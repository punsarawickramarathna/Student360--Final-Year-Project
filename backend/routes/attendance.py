from fastapi import APIRouter
from database import attendance_collection

router = APIRouter()

@router.get("/attendance")
def get_attendance():

    records = list(
        attendance_collection.find({}, {"_id": 0})
    )

    return {
        "count": len(records),
        "data": records
    }