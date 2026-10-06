from fastapi import APIRouter
from database import students_collection, users_collection

router = APIRouter()

@router.get("/students")
def get_students():
    students = list(
        students_collection.find({}, {"_id": 0})
    )

    for s in students:
        sid = s.get("student_id")
        current_name = s.get("name") or s.get("student_name")
        if not current_name or str(current_name).strip().lower() == "student":
            if sid:
                u = users_collection.find_one({
                    "$or": [{"student_id": sid}, {"user_id": sid}]
                })
                if u and u.get("name") and str(u.get("name")).strip().lower() != "student":
                    s["name"] = str(u["name"]).strip()
                    s["student_name"] = str(u["name"]).strip()
        else:
            s["name"] = str(current_name).strip()
            s["student_name"] = str(current_name).strip()

    return {
        "count": len(students),
        "data": students
    }