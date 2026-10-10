from fastapi import APIRouter, HTTPException
from database import users_collection, db
from bson import ObjectId

router = APIRouter()

@router.put("/update-profile/{student_id}")
def update_profile(student_id: str, data: dict):
    update_dict = {
        "name": data.get("name"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "department": data.get("department"),
        "year": data.get("year") or data.get("academic_year"),
        "academic_year": data.get("academic_year") or data.get("year"),
        "semester": data.get("semester") or data.get("sem"),
        "group": data.get("group"),
        "intake": data.get("intake"),
    }
    update_dict = {k: v for k, v in update_dict.items() if v is not None}

    result = users_collection.update_one(
        {"$or": [{"student_id": student_id}, {"user_id": student_id}]},
        {"$set": update_dict}
    )
    db.students.update_one(
        {"$or": [{"student_id": student_id}, {"user_id": student_id}]},
        {"$set": update_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Profile updated successfully"}

@router.put("/{user_type}/{user_id}")
async def update_user(user_type: str, user_id: str, data: dict):
    try:
        collection = db.students if user_type == "student" else db.users
        
        update_dict = {
            "name": data.get("name"),
            "email": data.get("email"),
            "department": data.get("department"),
            "intake": data.get("intake"),
            "student_id": data.get("student_id"),
        }
        if data.get("semester") is not None or data.get("sem") is not None:
            update_dict["semester"] = data.get("semester") or data.get("sem")
        if data.get("group") is not None:
            update_dict["group"] = data.get("group")
        if data.get("academic_year") is not None or data.get("year") is not None:
            update_dict["academic_year"] = data.get("academic_year") or data.get("year")
            update_dict["year"] = data.get("year") or data.get("academic_year")

        update_dict = {k: v for k, v in update_dict.items() if v is not None}

        result = collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"status": "success", "message": f"{user_type} updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_users():
    try:
        # Fetch students
        students = list(db.students.find({}, {"_id": 1, "student_id": 1, "name": 1, "email": 1, "department": 1, "intake": 1, "is_model_trained": 1}))
        for s in students:
            s["_id"] = str(s["_id"])
            s["role"] = "student"

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