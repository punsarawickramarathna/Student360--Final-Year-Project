from fastapi import APIRouter
from database import students_collection

router = APIRouter()

@router.get("/students")
def get_students():

    students = list(
        students_collection.find({}, {"_id": 0})
    )

    return {
        "count": len(students),
        "data": students
    }