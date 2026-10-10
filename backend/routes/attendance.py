import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from fastapi import APIRouter, Depends, Query, HTTPException
from database import (
    attendance_collection,
    sessions_collection,
    users_collection,
    students_collection,
)
from auth import get_current_user

router = APIRouter()


def fetch_student_attendance_data(raw_student_id: str) -> Dict[str, Any]:
    cleaned_id = str(raw_student_id or "").strip()
    total_sessions = sessions_collection.count_documents({})

    if not cleaned_id or cleaned_id.lower() in ["undefined", "null"]:
        return {
            "status": "success",
            "student_id": cleaned_id,
            "total_sessions": total_sessions,
            "present_count": 0,
            "percentage": 0.0,
            "history": [],
            "data": [],
            "count": 0,
        }

    # Collect candidate IDs (e.g. student_id, user_id, Mongo _id)
    candidate_ids = {cleaned_id}

    # Check users collection for alternate IDs
    user_query = {
        "$or": [
            {"student_id": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
            {"user_id": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
            {"email": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
        ]
    }
    if ObjectId.is_valid(cleaned_id):
        user_query["$or"].append({"_id": ObjectId(cleaned_id)})

    user = users_collection.find_one(user_query)
    if user:
        if user.get("student_id"):
            candidate_ids.add(str(user["student_id"]).strip())
        if user.get("user_id"):
            candidate_ids.add(str(user["user_id"]).strip())
        candidate_ids.add(str(user["_id"]))

    # Check students collection for alternate IDs
    student_query = {
        "$or": [
            {"student_id": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
            {"email": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
        ]
    }
    if ObjectId.is_valid(cleaned_id):
        student_query["$or"].append({"_id": ObjectId(cleaned_id)})

    student_doc = students_collection.find_one(student_query)
    if student_doc:
        if student_doc.get("student_id"):
            candidate_ids.add(str(student_doc["student_id"]).strip())
        candidate_ids.add(str(student_doc["_id"]))

    # Build $or query for attendance_collection
    query_conditions = []
    for cid in candidate_ids:
        escaped = re.escape(cid)
        query_conditions.append({"student_id": {"$regex": f"^{escaped}$", "$options": "i"}})
        query_conditions.append({"user_id": {"$regex": f"^{escaped}$", "$options": "i"}})
        query_conditions.append({"studentId": {"$regex": f"^{escaped}$", "$options": "i"}})
        if ObjectId.is_valid(cid):
            query_conditions.append({"_id": ObjectId(cid)})
            query_conditions.append({"student_id": ObjectId(cid)})

    # Query attendance collection
    attendance_records = list(attendance_collection.find({"$or": query_conditions}))

    # Also query sessions_collection if attendance is stored inside sessions as an array (present_students)
    session_conditions = []
    for cid in candidate_ids:
        escaped = re.escape(cid)
        regex_obj = {"$regex": f"^{escaped}$", "$options": "i"}
        session_conditions.extend([
            {"present_students": regex_obj},
            {"students": regex_obj},
            {"attendees": regex_obj},
            {"present_students": cid},
        ])

    session_matches = list(sessions_collection.find({"$or": session_conditions}))
    existing_session_ids = {str(r.get("session_id")) for r in attendance_records if r.get("session_id")}

    for sess in session_matches:
        sess_id = str(sess.get("session_id") or sess.get("_id"))
        if sess_id not in existing_session_ids:
            attendance_records.append({
                "student_id": cleaned_id,
                "session_id": sess_id,
                "date": str(sess.get("date") or datetime.utcnow().strftime("%Y-%m-%d")),
                "arrival_time": str(sess.get("started_at") or "N/A"),
                "status": "Present",
                "mode": sess.get("mode", "classroom"),
                "created_at": sess.get("started_at") or sess.get("ended_at") or datetime.utcnow(),
            })

    # Format and sanitize all records
    formatted_history = []
    for r in attendance_records:
        rec = dict(r)
        if "_id" in rec:
            rec["_id"] = str(rec["_id"])
        created_at = rec.get("created_at")
        if isinstance(created_at, datetime):
            rec["created_at"] = created_at.isoformat()
        date_val = rec.get("date")
        if isinstance(date_val, datetime):
            rec["date"] = date_val.strftime("%Y-%m-%d")
        elif not date_val and created_at:
            rec["date"] = str(created_at)[:10]

        if not rec.get("status"):
            rec["status"] = "Present"

        formatted_history.append(rec)

    # Sort history descending by date / created_at
    def sort_key(item):
        return str(item.get("date") or item.get("created_at") or "")

    formatted_history.sort(key=sort_key, reverse=True)

    present_count = len(formatted_history)
    effective_total_sessions = max(total_sessions, present_count)
    percentage = (
        round((present_count / effective_total_sessions) * 100, 2)
        if effective_total_sessions > 0
        else 0.0
    )

    return {
        "status": "success",
        "student_id": cleaned_id,
        "total_sessions": effective_total_sessions,
        "present_count": present_count,
        "percentage": percentage,
        "history": formatted_history,
        "data": formatted_history,
        "count": present_count,
    }


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/attendance/student/{student_id}")
@router.get("/api/attendance/student/{student_id}")
def get_student_attendance(student_id: str):
    """
    Get full attendance statistics and records for a specific student.
    Matches by student_id string, user_id, or ObjectId.
    """
    return fetch_student_attendance_data(student_id)


@router.get("/student/attendance")
@router.get("/api/student/attendance")
def get_current_student_attendance(
    current_user: dict = Depends(get_current_user),
):
    """
    Get attendance statistics and records for the currently authenticated student
    via JWT bearer token.
    """
    student_id = current_user.get("student_id") or current_user.get("user_id")
    return fetch_student_attendance_data(student_id)


@router.get("/attendance")
@router.get("/api/attendance")
def get_attendance(
    student_id: Optional[str] = Query(None),
):
    """
    Get attendance records. If student_id query param is supplied, returns
    statistics and history for that student. Otherwise returns all records.
    """
    if student_id and student_id.strip() and student_id.lower() not in ["undefined", "null"]:
        return fetch_student_attendance_data(student_id)

    records = list(attendance_collection.find({}))
    formatted = []
    for r in records:
        rec = dict(r)
        if "_id" in rec:
            rec["_id"] = str(rec["_id"])
        if isinstance(rec.get("created_at"), datetime):
            rec["created_at"] = rec["created_at"].isoformat()
        if isinstance(rec.get("date"), datetime):
            rec["date"] = rec["date"].strftime("%Y-%m-%d")
        if not rec.get("status"):
            rec["status"] = "Present"
        formatted.append(rec)

    return {
        "status": "success",
        "count": len(formatted),
        "data": formatted,
        "history": formatted,
    }