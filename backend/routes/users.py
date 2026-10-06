from fastapi import APIRouter, HTTPException
from database import users_collection, db
from bson import ObjectId

router = APIRouter()

@router.put("/update-profile/{student_id}")
def update_profile(student_id: str, data: dict):
    result = users_collection.update_one(
        {"student_id": student_id},
        {"$set": {
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "department": data.get("department"),
            "year": data.get("year"),
            "intake": data.get("intake"),
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Profile updated successfully"}

@router.get("/all")
async def get_all_users():
    try:
        # Fetch students from students collection
        students = list(db.students.find({}, {
            "_id": 1, "student_id": 1, "name": 1, "student_name": 1, "email": 1,
            "department": 1, "intake": 1, "is_model_trained": 1
        }))
        seen_ids = set()
        for s in students:
            s["_id"] = str(s["_id"])
            s["role"] = "student"
            sid = s.get("student_id")
            if sid:
                seen_ids.add(sid)

            # Populate name from users collection if missing or literal "student"
            current_name = s.get("name") or s.get("student_name")
            if not current_name or str(current_name).strip().lower() == "student":
                if sid:
                    u = db.users.find_one({"$or": [{"student_id": sid}, {"user_id": sid}]})
                    if u and u.get("name") and str(u.get("name")).strip().lower() != "student":
                        s["name"] = str(u["name"]).strip()
                        s["student_name"] = str(u["name"]).strip()
            else:
                s["name"] = str(current_name).strip()
                s["student_name"] = str(current_name).strip()

        # Merge student accounts in users collection if not already in students
        user_students = list(db.users.find({"role": "student"}, {
            "_id": 1, "student_id": 1, "user_id": 1, "name": 1, "student_name": 1,
            "email": 1, "department": 1, "intake": 1
        }))
        for u in user_students:
            uid = u.get("student_id") or u.get("user_id")
            if uid and uid not in seen_ids:
                seen_ids.add(uid)
                u_name = u.get("name") or u.get("student_name") or ""
                students.append({
                    "_id": str(u["_id"]),
                    "student_id": uid,
                    "name": str(u_name).strip() if u_name else uid,
                    "student_name": str(u_name).strip() if u_name else uid,
                    "email": u.get("email", ""),
                    "department": u.get("department", ""),
                    "intake": u.get("intake", ""),
                    "is_model_trained": False,
                    "role": "student"
                })

        # Fetch lecturers
        lecturers = list(db.users.find({"role": "lecturer"}, {"_id": 1, "name": 1, "email": 1, "department": 1}))
        for l in lecturers:
            l["_id"] = str(l["_id"])
            l["role"] = "lecturer"

        return {"students": students, "lecturers": lecturers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_type}/{user_id}")
async def delete_user(user_type: str, user_id: str):
    try:
        collection = db.students if user_type == "student" else db.users
        result = collection.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "success", "message": f"{user_type} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))