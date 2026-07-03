from fastapi import APIRouter

from database import students_collection
from database import attendance_collection
from database import behavior_collection
from database import appeals_collection

router = APIRouter()


@router.get("/dashboard")

def dashboard():

    students = students_collection.count_documents({})

    attendance = attendance_collection.count_documents({})

    behavior = behavior_collection.count_documents({})

    appeals = appeals_collection.count_documents({})

    return {

        "students": students,

        "attendance": attendance,

        "behavior": behavior,

        "appeals": appeals

    }