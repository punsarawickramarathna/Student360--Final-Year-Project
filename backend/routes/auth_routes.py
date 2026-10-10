from fastapi import APIRouter, HTTPException
from database import users_collection, students_collection
from auth import hash_password, verify_password, create_access_token
from models import UserCreate, LoginModel

router = APIRouter()


@router.post("/register")
def register(user: UserCreate):
    existing = users_collection.find_one({
        "$or": [
            {"student_id": user.student_id},
            {"user_id": user.student_id}
        ]
    })

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    users_collection.insert_one({
        "student_id": user.student_id,
        "user_id": user.student_id,  # Both keys saved for safety
        "name": user.name,
        "intake": user.intake,
        "password": hash_password(user.password),
        "role": user.role,
        "department": "",
        "year": "",
        "email": "",
        "phone": "",
        "address": "",
        "photo": "",
        "account_status": "active",
        "must_change_password": True
    })

    return {"message": "User created successfully"}


@router.post("/login")
def login(data: LoginModel):
    # Search by EITHER student_id OR user_id
    user = users_collection.find_one({
        "$or": [
            {"student_id": data.student_id},
            {"user_id": data.student_id}
        ]
    })

    if not user:
        raise HTTPException(status_code=401, detail="Invalid ID")

    # Password validation (Support for both hashed password & plain password if created directly by Admin)
    db_password = user.get("password", "")
    valid = False

    try:
        valid = verify_password(data.password, db_password)
    except Exception:
        valid = (data.password == db_password)

    if not valid and data.password != db_password:
        raise HTTPException(status_code=401, detail="Invalid Password")

    user_id_val = user.get("student_id") or user.get("user_id")

    # If student, lookup students_collection to ensure cohort details are populated
    student_doc = {}
    if user.get("role") == "student":
        student_doc = students_collection.find_one({
            "$or": [
                {"student_id": user_id_val},
                {"user_id": user_id_val}
            ]
        }) or {}

    academic_year = str(user.get("academic_year") or user.get("year") or student_doc.get("academic_year") or student_doc.get("year") or "")
    semester = str(user.get("semester") or student_doc.get("semester") or user.get("sem") or student_doc.get("sem") or "")
    group = str(user.get("group") or student_doc.get("group") or user.get("student_group") or student_doc.get("student_group") or "")
    department = str(user.get("department") or student_doc.get("department") or "")
    intake = str(user.get("intake") or student_doc.get("intake") or "")

    token = create_access_token({
        "student_id": user_id_val,
        "role": user.get("role", "student")
    })

    return {
        "token": token,
        "user": {
            "student_id": user_id_val,
            "user_id": user_id_val,
            "name": user.get("name", ""),
            "intake": intake,
            "role": user.get("role", "student"),
            "department": department,
            "year": academic_year,
            "academic_year": academic_year,
            "semester": semester,
            "sem": semester,
            "group": group,
            "student_group": group,
            "batch": f"Intake {intake}" if intake else "",
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "address": user.get("address", ""),
            "photo": user.get("photo", ""),
            "account_status": user.get("account_status", "active"),
            "must_change_password": user.get("must_change_password", False)
        }
    }