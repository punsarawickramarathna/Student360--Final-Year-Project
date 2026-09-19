from fastapi import APIRouter, HTTPException
from database import users_collection
from auth import hash_password, verify_password, create_access_token
from models import UserCreate, LoginModel

router = APIRouter()


@router.post("/register")
def register(user: UserCreate):

    

    existing = users_collection.find_one({
        "student_id": user.student_id
    })

    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    users_collection.insert_one({
    "student_id": user.student_id,
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

    user = users_collection.find_one({
        "student_id": data.student_id
    })

    if not user:
        raise HTTPException(status_code=401, detail="Invalid ID")
   

    valid = verify_password(
        data.password,
        user["password"]
    )

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid Password")

    token = create_access_token({
        "student_id": user["student_id"],
        "role": user["role"]
    })

    return {

        "token": token,

        "user": {
    "student_id": user["student_id"],
    "name": user["name"],
    "intake": user.get("intake", ""),
    "role": user["role"],

    "department": user.get("department", ""),
    "year": user.get("year", ""),
    "email": user.get("email", ""),
    "phone": user.get("phone", ""),
    "address": user.get("address", ""),
    "photo": user.get("photo", ""),

    "account_status": user.get("account_status", "active"),
    "must_change_password": user.get("must_change_password", False)
}

    }