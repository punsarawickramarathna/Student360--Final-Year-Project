# routes/profile.py

import os
import shutil
import uuid
import re
from bson import ObjectId

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

router = APIRouter(
    prefix="/profile",
    tags=["Profile"]
)

UPLOAD_DIR = "uploads/profile_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------------------------------
# Helper function: Format and normalize student profile data
# ---------------------------------

def format_user(user=None, student=None):
    user = user or {}
    student = student or {}

    academic_details = (
        user.get("academic_details")
        or student.get("academic_details")
        or {}
    )

    student_id = (
        user.get("student_id")
        or user.get("user_id")
        or student.get("student_id")
        or student.get("user_id")
        or ""
    )

    name = user.get("name") or student.get("name") or ""
    intake = (
        user.get("intake")
        or student.get("intake")
        or academic_details.get("intake")
        or ""
    )
    role = user.get("role") or student.get("role") or "student"
    department = (
        user.get("department")
        or student.get("department")
        or academic_details.get("department")
        or ""
    )

    year = (
        user.get("academic_year")
        or user.get("year")
        or student.get("academic_year")
        or student.get("year")
        or academic_details.get("academic_year")
        or academic_details.get("year")
        or ""
    )

    semester = (
        user.get("semester")
        or student.get("semester")
        or user.get("sem")
        or student.get("sem")
        or user.get("current_semester")
        or student.get("current_semester")
        or academic_details.get("semester")
        or academic_details.get("sem")
        or ""
    )

    group = (
        user.get("group")
        or student.get("group")
        or user.get("student_group")
        or student.get("student_group")
        or user.get("batch_group")
        or student.get("batch_group")
        or user.get("batch")
        or student.get("batch")
        or academic_details.get("group")
        or ""
    )

    degree = (
        user.get("degree")
        or student.get("degree")
        or user.get("program")
        or student.get("program")
        or academic_details.get("degree")
        or (f"BSc (Hons) in {department}" if department else "BSc (Hons) in Information Technology")
    )

    batch = (
        user.get("batch")
        or student.get("batch")
        or academic_details.get("batch")
        or (f"Intake {intake}" if intake else "")
    )

    email = user.get("email") or student.get("email") or ""
    phone = user.get("phone") or student.get("phone") or ""
    address = user.get("address") or student.get("address") or ""
    photo = user.get("photo") or student.get("photo") or ""
    account_status = user.get("account_status") or student.get("account_status") or "active"
    must_change_password = user.get("must_change_password", False)

    return {
        "student_id": str(student_id),
        "user_id": str(student_id),
        "name": str(name),
        "intake": str(intake),
        "role": str(role),
        "department": str(department),
        "year": str(year),
        "academic_year": str(year),
        "semester": str(semester),
        "sem": str(semester),
        "current_semester": str(semester),
        "group": str(group),
        "student_group": str(group),
        "batch_group": str(group),
        "batch": str(batch),
        "degree": str(degree),
        "email": str(email),
        "phone": str(phone),
        "address": str(address),
        "photo": str(photo),
        "account_status": str(account_status),
        "must_change_password": bool(must_change_password),
        "academic_details": {
            "academic_year": str(year),
            "year": str(year),
            "semester": str(semester),
            "sem": str(semester),
            "group": str(group),
            "intake": str(intake),
            "department": str(department),
            "batch": str(batch),
            "degree": str(degree),
        }
    }


def resolve_student_profile(raw_student_id: str):
    cleaned_id = str(raw_student_id or "").strip()
    if not cleaned_id:
        return None

    # 1. Search in users_collection
    user_query = {
        "$or": [
            {"student_id": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
            {"user_id": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
            {"email": {"$regex": f"^{re.escape(cleaned_id)}$", "$options": "i"}},
        ]
    }
    if ObjectId.is_valid(cleaned_id):
        user_query["$or"].append({"_id": ObjectId(cleaned_id)})

    user = users_collection.find_one(user_query)

    # 2. Search in students_collection
    candidate_ids = {cleaned_id}
    if user:
        if user.get("student_id"):
            candidate_ids.add(str(user["student_id"]).strip())
        if user.get("user_id"):
            candidate_ids.add(str(user["user_id"]).strip())
        if user.get("email"):
            candidate_ids.add(str(user["email"]).strip())

    student_conditions = []
    for cid in candidate_ids:
        escaped = re.escape(cid)
        student_conditions.extend([
            {"student_id": {"$regex": f"^{escaped}$", "$options": "i"}},
            {"user_id": {"$regex": f"^{escaped}$", "$options": "i"}},
            {"email": {"$regex": f"^{escaped}$", "$options": "i"}},
        ])
        if ObjectId.is_valid(cid):
            student_conditions.append({"_id": ObjectId(cid)})

    student = students_collection.find_one({"$or": student_conditions})

    if not user and not student:
        return None

    if not user and student:
        user = dict(student)
    if not student and user:
        student = dict(user)

    formatted = format_user(user, student)
    print(f"DEBUG PROFILE FETCH FOR {raw_student_id}: semester={formatted.get('semester')}, group={formatted.get('group')}, year={formatted.get('academic_year')}")

    # Synchronize missing academic fields into users_collection
    if user and user.get("_id"):
        sync_fields = {}
        for key in ["semester", "group", "academic_year", "year", "department", "intake"]:
            if not user.get(key) and formatted.get(key):
                sync_fields[key] = formatted.get(key)
        if not user.get("student_id") and formatted.get("student_id"):
            sync_fields["student_id"] = formatted.get("student_id")
        if not user.get("user_id") and formatted.get("student_id"):
            sync_fields["user_id"] = formatted.get("student_id")
        if sync_fields:
            users_collection.update_one({"_id": user["_id"]}, {"$set": sync_fields})

    # Synchronize missing academic fields into students_collection
    if student and student.get("_id"):
        student_sync = {}
        for key in ["semester", "group", "academic_year", "year", "department", "intake"]:
            if not student.get(key) and formatted.get(key):
                student_sync[key] = formatted.get(key)
        if not student.get("student_id") and formatted.get("student_id"):
            student_sync["student_id"] = formatted.get("student_id")
        if student_sync:
            students_collection.update_one({"_id": student["_id"]}, {"$set": student_sync})

    return formatted


# ---------------------------------
# GET logged-in student profile
# ---------------------------------

@router.get("/me")
def get_my_profile(
    current_user=Depends(get_current_user)
):
    student_id = current_user.get("student_id") or current_user.get("user_id")

    profile_data = resolve_student_profile(student_id)
    if not profile_data:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    return {
        "status": "success",
        "user": profile_data,
        "student": profile_data,
        "data": profile_data
    }


# ---------------------------------
# GET student profile by student_id
# ---------------------------------

@router.get("/student/{student_id}")
@router.get("/{student_id}")
def get_student_profile_by_id(student_id: str):
    profile_data = resolve_student_profile(student_id)
    if not profile_data:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found"
        )

    return {
        "status": "success",
        "user": profile_data,
        "student": profile_data,
        "data": profile_data
    }


# ---------------------------------
# UPDATE logged-in student profile
# ---------------------------------

@router.put("/me")
def update_my_profile(
    profile: ProfileUpdate,
    current_user=Depends(get_current_user)
):
    student_id = current_user.get("student_id") or current_user.get("user_id")

    user_query = {
        "$or": [
            {"student_id": student_id},
            {"user_id": student_id}
        ]
    }
    user = users_collection.find_one(user_query)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    update_data = profile.model_dump(
        exclude_unset=True,
        exclude_none=True
    )

    # Student cannot change protected system credentials
    protected_fields = [
        "student_id",
        "role",
        "password",
        "photo",
        "account_status",
        "must_change_password"
    ]
    for field in protected_fields:
        update_data.pop(field, None)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No profile data provided"
        )

    # Normalize year and academic_year
    if "academic_year" in update_data and "year" not in update_data:
        update_data["year"] = update_data["academic_year"]
    elif "year" in update_data and "academic_year" not in update_data:
        update_data["academic_year"] = update_data["year"]

    # Update in users_collection
    users_collection.update_one(
        user_query,
        {"$set": update_data}
    )

    # Also update in students_collection so both collections remain fully synced
    students_collection.update_one(
        {"$or": [{"student_id": student_id}, {"user_id": student_id}]},
        {"$set": update_data}
    )

    updated_profile = resolve_student_profile(student_id)

    return {
        "message": "Profile updated successfully",
        "user": updated_profile,
        "student": updated_profile,
        "data": updated_profile
    }


# ---------------------------------
# UPLOAD profile image
# ---------------------------------

@router.post("/photo")
def upload_profile_image(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    student_id = current_user.get("student_id") or current_user.get("user_id")

    user_query = {
        "$or": [
            {"student_id": student_id},
            {"user_id": student_id}
        ]
    }
    user = users_collection.find_one(user_query)

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
            detail="Only JPG, PNG and WEBP images are allowed"
        )

    extension = os.path.splitext(file.filename or "")[1].lower()
    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Invalid image extension"
        )

    unique_filename = f"{student_id}_{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Profile image upload failed"
        ) from error

    photo_url = f"/uploads/profile_images/{unique_filename}"
    old_photo = user.get("photo", "")

    users_collection.update_one(
        user_query,
        {"$set": {"photo": photo_url}}
    )
    students_collection.update_one(
        {"$or": [{"student_id": student_id}, {"user_id": student_id}]},
        {"$set": {"photo": photo_url}}
    )

    # Delete previous local image file
    if old_photo and old_photo.startswith("/uploads/profile_images/"):
        old_file_name = old_photo.split("/")[-1]
        old_file_path = os.path.join(UPLOAD_DIR, old_file_name)
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except OSError:
                pass

    return {
        "message": "Profile image uploaded successfully",
        "photo": photo_url
    }


# ---------------------------------
# DELETE profile image
# ---------------------------------

@router.delete("/photo")
def delete_profile_image(
    current_user=Depends(get_current_user)
):
    student_id = current_user.get("student_id") or current_user.get("user_id")

    user_query = {
        "$or": [
            {"student_id": student_id},
            {"user_id": student_id}
        ]
    }
    user = users_collection.find_one(user_query)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    old_photo = user.get("photo", "")
    if old_photo and old_photo.startswith("/uploads/profile_images/"):
        old_file_name = old_photo.split("/")[-1]
        old_file_path = os.path.join(UPLOAD_DIR, old_file_name)
        if os.path.exists(old_file_path):
            try:
                os.remove(old_file_path)
            except OSError:
                pass

    users_collection.update_one(
        user_query,
        {"$set": {"photo": ""}}
    )
    students_collection.update_one(
        {"$or": [{"student_id": student_id}, {"user_id": student_id}]},
        {"$set": {"photo": ""}}
    )

    return {
        "message": "Profile image removed successfully"
    }


# ---------------------------------
# CHANGE logged-in user's password
# ---------------------------------

@router.put("/change-password")
def change_password(
    password_data: ChangePasswordModel,
    current_user=Depends(get_current_user)
):
    student_id = current_user.get("student_id") or current_user.get("user_id")

    user_query = {
        "$or": [
            {"student_id": student_id},
            {"user_id": student_id}
        ]
    }
    user = users_collection.find_one(user_query)

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

    new_hashed_password = hash_password(new_password)

    result = users_collection.update_one(
        user_query,
        {
            "$set": {
                "password": new_hashed_password,
                "must_change_password": False
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=500,
            detail="Password could not be updated"
        )

    return {
        "message": "Password changed successfully"
    }