from fastapi import APIRouter
from database import behavior_collection

router = APIRouter()

@router.get("/behavior")
def get_behavior():

    logs = list(
        behavior_collection.find({}, {"_id": 0})
    )

    return {
        "count": len(logs),
        "data": logs
    }