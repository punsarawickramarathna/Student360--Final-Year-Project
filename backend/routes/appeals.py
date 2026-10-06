from fastapi import APIRouter, HTTPException
from database import appeals_collection, students_collection, users_collection
from datetime import datetime
from bson import ObjectId

router = APIRouter()


def get_student_name_by_id(student_id: str) -> str:
    if not student_id:
        return ""
    # 1. Check students_collection
    student = students_collection.find_one({"student_id": student_id})
    if student:
        name = student.get("name") or student.get("student_name")
        if name and str(name).strip().lower() != "student":
            return str(name).strip()

    # 2. Check users_collection (match student_id or user_id)
    user = users_collection.find_one({
        "$or": [{"student_id": student_id}, {"user_id": student_id}]
    })
    if user:
        name = user.get("name") or user.get("student_name")
        if name and str(name).strip().lower() != "student":
            return str(name).strip()

    return ""


# 1. Student / Admin Appeals Fetch (GET)
@router.get("")
@router.get("/")
def get_all_appeals():
    try:
        appeals = list(appeals_collection.find({}))
        for a in appeals:
            a["_id"] = str(a["_id"])
            student_id = a.get("student_id", "")
            current_name = a.get("name") or a.get("student_name")

            # If name is missing or the literal string "student", populate from MongoDB
            if not current_name or str(current_name).strip().lower() == "student":
                populated_name = get_student_name_by_id(student_id)
                if populated_name:
                    a["name"] = populated_name
                    a["student_name"] = populated_name
                else:
                    a["name"] = current_name or student_id or "Student"
                    a["student_name"] = a["name"]
            else:
                a["name"] = str(current_name).strip()
                a["student_name"] = str(current_name).strip()

        return appeals
    except Exception as e:
        return []


# 2. Student Appeal Submit (POST)
@router.post("")
@router.post("/")
def create_appeal(data: dict):
    try:
        data["created_at"] = datetime.utcnow().isoformat()
        data["status"] = data.get("status", "Pending")

        student_id = data.get("student_id", "")
        current_name = data.get("name") or data.get("student_name")
        if not current_name or str(current_name).strip().lower() == "student":
            populated_name = get_student_name_by_id(student_id)
            if populated_name:
                data["name"] = populated_name
                data["student_name"] = populated_name

        res = appeals_collection.insert_one(data)
        return {"message": "Appeal submitted", "id": str(res.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Admin Decision Update (PUT)
@router.put("/{appeal_id}")
def update_appeal_status(appeal_id: str, data: dict):
    try:
        appeals_collection.update_one(
            {"_id": ObjectId(appeal_id)},
            {"$set": {
                "status": data.get("status", "Approved"),
                "admin_response": data.get("admin_response", ""),
                "reviewed_by": data.get("reviewed_by", "Admin"),
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        return {"message": "Success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))