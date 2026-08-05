# routes/profile.py

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends
)

from database import users_collection
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
# MongoDB user -> frontend JSON
# ---------------------------------

def format_user(user):
    return {
        "student_id": user.get(
            "student_id",
            ""
        ),
        "name": user.get(
            "name",
            ""
        ),
        "intake": user.get(
            "intake",
            ""
        ),
        "role": user.get(
            "role",
            ""
        ),
        "department": user.get(
            "department",
            ""
        ),
        "year": user.get(
            "year",
            ""
        ),
        "email": user.get(
            "email",
            ""
        ),
        "phone": user.get(
            "phone",
            ""
        ),
        "address": user.get(
            "address",
            ""
        ),
        "photo": user.get(
            "photo",
            ""
        ),
        "account_status": user.get(
            "account_status",
            "active"
        ),
        "must_change_password": user.get(
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

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    return {
        "user": format_user(user)
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

    users_collection.update_one(
        {
            "student_id": student_id
        },
        {
            "$set": update_data
        }
    )

    updated_user = users_collection.find_one({
        "student_id": student_id
    })

    return {
        "message": "Profile updated successfully",
        "user": format_user(
            updated_user
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