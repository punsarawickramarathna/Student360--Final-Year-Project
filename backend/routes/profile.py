# routes/profile.py

# pyrefly: ignore [missing-import]
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from database import users_collection, students_collection
from auth import (
    get_current_user,
    verify_password,
    hash_password
)

from models import (
    ProfileUpdate,
    ChangePasswordModel
)

import os
import shutil
import uuid


router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)


UPLOAD_DIR = "uploads/profile_images"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ---------------------------------
# Helper function
# MongoDB user/student -> frontend JSON
# ---------------------------------

def format_user(user, student=None):
    if not user and not student:
        return {}

    user_data = user or {}
    student_id = user_data.get("student_id") or (student.get("student_id") if student else "")

    if student is None and student_id:
        student = students_collection.find_one({
            "student_id": student_id
        })

    student_data = student or {}

    academic_year = (
        student_data.get("academic_year")
        or student_data.get("year")
        or user_data.get("academic_year")
        or user_data.get("year")
        or ""
    )

    semester = (
        student_data.get("semester")
        or user_data.get("semester")
        or ""
    )

    group = (
        student_data.get("group")
        or user_data.get("group")
        or ""
    )

    department = (
        user_data.get("department")
        or student_data.get("department")
        or ""
    )

    intake = (
        user_data.get("intake")
        or student_data.get("intake")
        or ""
    )

    name = (
        user_data.get("name")
        or student_data.get("name")
        or ""
    )

    email = (
        user_data.get("email")
        or student_data.get("email")
        or ""
    )

    role = (
        user_data.get("role")
        or student_data.get("role")
        or "student"
    )

    return {
        "student_id": student_id,
        "name": name,
        "intake": intake,
        "role": role,
        "department": department,
        "year": academic_year,
        "academic_year": academic_year,
        "semester": semester,
        "group": group,
        "email": email,
        "phone": user_data.get(
            "phone",
            student_data.get("phone", "")
        ),
        "address": user_data.get(
            "address",
            student_data.get("address", "")
        ),
        "photo": user_data.get(
            "photo",
            student_data.get("photo", "")
        ),
        "account_status": user_data.get(
            "account_status",
            student_data.get("account_status", "active")
        ),
        "must_change_password": user_data.get(
            "must_change_password",
            False
        )
    }


# ---------------------------------
# GET logged-in student profile
# ---------------------------------

@router.get("/me")
def get_my_profile(
    current_user=Depends(
        get_current_user
    )
):
    student_id = current_user[
        "student_id"
    ]

    user = users_collection.find_one({
        "student_id": student_id
    })

    student = students_collection.find_one({
        "student_id": student_id
    })

    if not user and not student:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    base_user = user or student or {}

    return {
        "user": format_user(base_user, student)
    }


# ---------------------------------
# UPDATE logged-in student profile
# ---------------------------------

@router.put("/me")
def update_my_profile(
    profile: ProfileUpdate,
    current_user=Depends(
        get_current_user
    )
):
    student_id = current_user[
        "student_id"
    ]

    user = users_collection.find_one({
        "student_id": student_id
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    update_data = profile.model_dump(
        exclude_unset=True,
        exclude_none=True
    )

    # Student cannot change protected fields
    protected_fields = [
        "student_id",
        "intake",
        "role",
        "department",
        "email",
        "password",
        "photo",
        "account_status",
        "must_change_password"
    ]

    for field in protected_fields:
        update_data.pop(
            field,
            None
        )

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No profile data provided"
        )

    # 1. users collection එක update කිරීම
    users_collection.update_one(
        {
            "student_id": student_id
        },
        {
            "$set": update_data
        }
    )

    # 2. students collection එකත් sync කිරීම
    if user.get("role") == "student":
        student_sync_data = {}
        if "name" in update_data:
            student_sync_data["name"] = update_data["name"]
        if "year" in update_data:
            student_sync_data["academic_year"] = update_data["year"]
            student_sync_data["year"] = update_data["year"]
        elif "academic_year" in update_data:
            student_sync_data["academic_year"] = update_data["academic_year"]
            student_sync_data["year"] = update_data["academic_year"]
        if "semester" in update_data:
            student_sync_data["semester"] = update_data["semester"]
        if "group" in update_data:
            student_sync_data["group"] = update_data["group"]

        if student_sync_data:
            students_collection.update_one(
                {
                    "student_id": student_id
                },
                {
                    "$set": student_sync_data
                }
            )

    updated_user = users_collection.find_one({
        "student_id": student_id
    })
    updated_student = students_collection.find_one({
        "student_id": student_id
    })

    return {
        "message": "Profile updated successfully",
        "user": format_user(
            updated_user,
            updated_student
        )
    }


# ---------------------------------
# UPLOAD profile image
# ---------------------------------

@router.post("/photo")
def upload_profile_image(
    file: UploadFile = File(...),
    current_user=Depends(
        get_current_user
    )
):
    student_id = current_user[
        "student_id"
    ]

    user = users_collection.find_one({
        "student_id": student_id
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    allowed_types = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only JPG, PNG and WEBP "
                "images are allowed"
            )
        )

    extension = os.path.splitext(
        file.filename or ""
    )[1].lower()

    allowed_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    ]

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Invalid image extension"
        )

    unique_filename = (
        f"{student_id}_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        unique_filename
    )

    try:
        with open(
            file_path,
            "wb"
        ) as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Profile image upload failed"
        ) from error

    photo_url = (
        f"/uploads/profile_images/"
        f"{unique_filename}"
    )

    old_photo = user.get(
        "photo",
        ""
    )

    users_collection.update_one(
        {
            "student_id": student_id
        },
        {
            "$set": {
                "photo": photo_url
            }
        }
    )

    # Delete previous local image
    if old_photo and old_photo.startswith(
        "/uploads/profile_images/"
    ):
        old_file_name = old_photo.split(
            "/"
        )[-1]

        old_file_path = os.path.join(
            UPLOAD_DIR,
            old_file_name
        )

        if os.path.exists(
            old_file_path
        ):
            try:
                os.remove(
                    old_file_path
                )
            except OSError:
                pass

    return {
        "message": (
            "Profile image uploaded "
            "successfully"
        ),
        "photo": photo_url
    }


# ---------------------------------
# DELETE profile image
# ---------------------------------

@router.delete("/photo")
def delete_profile_image(
    current_user=Depends(
        get_current_user
    )
):
    student_id = current_user[
        "student_id"
    ]

    user = users_collection.find_one({
        "student_id": student_id
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    old_photo = user.get(
        "photo",
        ""
    )

    if old_photo and old_photo.startswith(
        "/uploads/profile_images/"
    ):
        old_file_name = old_photo.split(
            "/"
        )[-1]

        old_file_path = os.path.join(
            UPLOAD_DIR,
            old_file_name
        )

        if os.path.exists(
            old_file_path
        ):
            try:
                os.remove(
                    old_file_path
                )
            except OSError:
                pass

    users_collection.update_one(
        {
            "student_id": student_id
        },
        {
            "$set": {
                "photo": ""
            }
        }
    )

    return {
        "message": (
            "Profile image removed "
            "successfully"
        )
    }


# ---------------------------------
# CHANGE logged-in user's password
# ---------------------------------

@router.put("/change-password")
def change_password(
    password_data: ChangePasswordModel,
    current_user=Depends(get_current_user)
):
    student_id = current_user["student_id"]

    user = users_collection.find_one({
        "student_id": student_id
    })

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User account not found"
        )

    stored_password = user.get("password")

    if not stored_password:
        raise HTTPException(
            status_code=400,
            detail="Password is not configured"
        )

    try:
        current_password_valid = verify_password(
            password_data.current_password,
            stored_password
        )
    except Exception:
        current_password_valid = False

    if not current_password_valid:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    new_password = password_data.new_password

    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must contain at least 8 characters"
        )

    if not any(character.isupper() for character in new_password):
        raise HTTPException(
            status_code=400,
            detail="New password must contain an uppercase letter"
        )

    if not any(character.islower() for character in new_password):
        raise HTTPException(
            status_code=400,
            detail="New password must contain a lowercase letter"
        )

    if not any(character.isdigit() for character in new_password):
        raise HTTPException(
            status_code=400,
            detail="New password must contain a number"
        )

    if password_data.current_password == new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )

    new_hashed_password = hash_password(
        new_password
    )

    result = users_collection.update_one(
        {
            "student_id": student_id
        },
        {
            "$set": {
                "password": new_hashed_password,
                "must_change_password": False
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=500,
            detail="Password could not be updated"
        )

    return {
        "message": "Password changed successfully"
    }