import os
import shutil

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks
)

from datetime import datetime

from train_faces import (
    retrain_registered_students
)

from database import (
    db,
    users_collection,
    students_collection
)

from auth import hash_password


router = APIRouter()


# ============================================================
# LECTURERS
# ============================================================

lecturers_collection = db[
    "lecturers"
]


# ============================================================
# UPLOAD DIRECTORY
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

UPLOAD_DIR = os.path.join(
    BASE_DIR,
    "uploads",
    "videos"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ============================================================
# STUDENT REGISTRATION
# ============================================================

@router.post(
    "/api/admin/register-student"
)
async def register_student(

    background_tasks: BackgroundTasks,

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

    student_id = (
        student_id
        .strip()
        .upper()
    )

    name = name.strip()

    email = email.strip()

    department = department.strip()

    intake = intake.strip()

    academic_year = (
        academic_year.strip()
    )

    semester = semester.strip()

    group = group.strip()

    password = password.strip()

    # ========================================================
    # VALIDATION
    # ========================================================

    if not student_id:

        raise HTTPException(
            status_code=400,
            detail="Student ID is required."
        )

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Student name is required."
        )

    if not email:

        raise HTTPException(
            status_code=400,
            detail="Student email is required."
        )

    if not password:

        raise HTTPException(
            status_code=400,
            detail="Student password is required."
        )

    # ========================================================
    # DUPLICATE STUDENT
    # ========================================================

    existing_student = (
        students_collection.find_one(
            {
                "student_id": student_id
            }
        )
    )

    if existing_student:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Student ID {student_id} "
                "already exists."
            )
        )

    # ========================================================
    # DUPLICATE USER
    # ========================================================

    existing_user = (
        users_collection.find_one(
            {
                "student_id": student_id
            }
        )
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail=(
                f"User account for {student_id} "
                "already exists."
            )
        )

    # ========================================================
    # VIDEO VALIDATION
    # ========================================================

    if video is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "Face training video is required."
            )
        )

    if not video.filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid video file."
        )

    allowed_extensions = (
        ".mp4",
        ".mov",
        ".avi",
        ".mkv"
    )

    file_ext = os.path.splitext(
        video.filename
    )[1].lower()

    if file_ext not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only MP4, MOV, AVI or MKV "
                "video files are allowed."
            )
        )

    # ========================================================
    # SAVE VIDEO
    # ========================================================

    video_filename = (
        f"{student_id}{file_ext}"
    )

    video_path = os.path.join(
        UPLOAD_DIR,
        video_filename
    )

    try:

        with open(
            video_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                video.file,
                buffer
            )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not save training video: {e}"
            )
        )

    video_path = os.path.abspath(
        video_path
    )

    print(
        "\n=========================================="
    )

    print(
        "NEW STUDENT REGISTERED"
    )

    print(
        "Student ID:",
        student_id
    )

    print(
        "Training video:",
        video_path
    )

    print(
        "=========================================="
    )

    # ========================================================
    # CREATE STUDENT RECORD
    # ========================================================

    student_data = {

        "student_id": student_id,

        "name": name,

        "email": email,

        "department": department,

        "intake": intake,

        "academic_year": academic_year,

        "semester": semester,

        "group": group,

        "role": "student",

        "video_path": video_path,

        # Training state
        "is_model_trained": False,

        "face_training_status": "pending",

        "face_training_error": "",

        "face_model_updated_at": None,

        "registered_date":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    }

    try:

        student_result = (
            students_collection.insert_one(
                student_data
            )
        )

        # ====================================================
        # CREATE LOGIN ACCOUNT
        # ====================================================

        users_collection.insert_one(
            {
                "student_id":
                    student_id,

                "user_id":
                    student_id,

                "email":
                    email,

                "password":
                    hash_password(
                        password
                    ),

                "role":
                    "student",

                "name":
                    name,

                "intake":
                    intake,

                "department":
                    department,

                "academic_year":
                    academic_year,

                "year":
                    academic_year,

                "semester":
                    semester,

                "group":
                    group,

                "account_status":
                    "active"
            }
        )

    except Exception as e:

        # Remove uploaded video if DB creation failed.
        try:

            if os.path.exists(
                video_path
            ):

                os.remove(
                    video_path
                )

        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                f"Student registration failed: {e}"
            )
        )

    # ========================================================
    # AUTOMATIC FACE TRAINING
    # ========================================================

    background_tasks.add_task(
        retrain_registered_students,
        [student_id]
    )

    print(
        f"🚀 Automatic face training "
        f"queued for {student_id}"
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {

        "status": "success",

        "message": (
            f"Student {name} registered successfully. "
            "Face recognition training has started "
            "automatically."
        ),

        "student_id": student_id,

        "face_training_status":
            "pending",

        "training_started":
            True
    }


# ============================================================
# LECTURER REGISTRATION
# ============================================================

@router.post(
    "/api/admin/register-lecturer"
)
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

        lec_id = lec_id.strip()

        name = name.strip()

        email = email.strip()

        faculty = faculty.strip()

        gender = gender.strip()

        employment_type = (
            employment_type.strip()
        )

        password = password.strip()

        if lecturers_collection.find_one(
            {
                "lec_id": lec_id
            }
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Lecturer ID already exists!"
                )
            )

        lecturer_data = {

            "lec_id":
                lec_id,

            "name":
                name,

            "email":
                email,

            "faculty":
                faculty,

            "gender":
                gender,

            "employment_type":
                employment_type,

            "subjects": [
                s.strip()
                for s in subjects.split(",")
                if s.strip()
            ],

            "role":
                "lecturer",

            "registered_date":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        lecturers_collection.insert_one(
            lecturer_data
        )

        users_collection.insert_one(
            {

                "user_id":
                    lec_id,

                "student_id":
                    lec_id,

                "email":
                    email,

                "password":
                    hash_password(
                        password
                    ),

                "role":
                    "lecturer",

                "name":
                    name
            }
        )

        return {

            "status":
                "success",

            "message":
                f"Lecturer {name} "
                "registered successfully!"
        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )