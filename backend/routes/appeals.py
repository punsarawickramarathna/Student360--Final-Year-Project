from fastapi import APIRouter
from database import appeals_collection
from models import AppealModel
from datetime import datetime

router = APIRouter()

@router.post("/appeals")
def create_appeal(data: AppealModel):

    appeals_collection.insert_one({
        "student_id": data.student_id,
        "message": data.message,
        "type": data.type,
        "status": "Pending",
        "created_at": datetime.utcnow()
    })

    return {"message": "Appeal submitted"}

@router.get("/appeals")
def get_appeals():

    appeals = list(
        appeals_collection.find({}, {"_id": 0})
    )

    return {
        "count": len(appeals),
        "data": appeals
    }