from fastapi import APIRouter, HTTPException
from database import users_collection

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