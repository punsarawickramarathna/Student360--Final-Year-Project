import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import db, users_collection, students_collection
from auth import hash_password  # <-- Password hash කිරීම සඳහා import කරන ලදී
from datetime import datetime

router = APIRouter()

# Collections definition
lecturers_collection = db["lecturers"]

UPLOAD_DIR = "uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==========================================
# 1. STUDENT REGISTRATION API
# ==========================================
@router.post("/api/admin/register-student")
async def register_student(
    student_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    intake: str = Form(...),
    academic_year: str = Form("1"),
    semester: str = Form("1"),
    group: str = Form("A"),
    password: str = Form(...),
    video: UploadFile = File(...)
):
    try:
        if students_collection.find_one({"student_id": student_id}):
            raise HTTPException(status_code=400, detail="Student ID already exists!")

        if not video.filename.endswith(('.mp4', '.MP4', '.mov', '.avi')):
            raise HTTPException(status_code=400, detail="Only MP4 or MOV video files are allowed!")

        file_ext = os.path.splitext(video.filename)[1]
        video_path = os.path.join(UPLOAD_DIR, f"{student_id}{file_ext}")

        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        student_data = {
            "student_id": student_id.strip(),
            "name": name.strip(),
            "email": email.strip(),
            "department": department.strip(),
            "intake": intake.strip(),
            "academic_year": academic_year.strip(),
            "semester": semester.strip(),
            "group": group.strip(),
            "role": "student",
            "video_path": video_path,
            "is_model_trained": False,
            "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        students_collection.insert_one(student_data)
        
        # users_collection එකට hashed password එක සහ student_id/user_id දෙකම ඇතුළත් කිරීම
        users_collection.insert_one({
            "student_id": student_id.strip(),
            "user_id": student_id.strip(),
            "email": email.strip(),
            "password": hash_password(password.strip()),  # Hashed Password
            "role": "student",
            "name": name.strip(),
            "intake": intake.strip(),
            "department": department.strip(),
            "account_status": "active"
        })

        return {"status": "success", "message": f"Student {name} registered & AI training video uploaded successfully!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 2. LECTURER REGISTRATION API
# ==========================================
@router.post("/api/admin/register-lecturer")
async def register_lecturer(
    lec_id: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    faculty: str = Form(...),
    gender: str = Form(...),
    employment_type: str = Form(...),
    subjects: str = Form(...),
    password: str = Form(...)
):
    try:
        if lecturers_collection.find_one({"lec_id": lec_id}):
            raise HTTPException(status_code=400, detail="Lecturer ID already exists!")

        lecturer_data = {
            "lec_id": lec_id.strip(),
            "name": name.strip(),
            "email": email.strip(),
            "faculty": faculty.strip(),
            "gender": gender.strip(),
            "employment_type": employment_type.strip(),
            "subjects": [s.strip() for s in subjects.split(",") if s.strip()],
            "role": "lecturer",
            "registered_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        lecturers_collection.insert_one(lecturer_data)

        users_collection.insert_one({
            "user_id": lec_id.strip(),
            "student_id": lec_id.strip(),
            "email": email.strip(),
            "password": hash_password(password.strip()),  # Hashed Password
            "role": "lecturer",
            "name": name.strip()
        })

        return {"status": "success", "message": f"Lecturer {name} registered successfully!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))