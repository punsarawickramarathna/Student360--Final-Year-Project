from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    student_id: str
    name: str
    intake: str
    password: str
    role: str


class LoginModel(BaseModel):
    student_id: str
    password: str


class AppealModel(BaseModel):
    student_id: str
    message: str
    type: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    group: Optional[str] = None
    batch: Optional[str] = None
    degree: Optional[str] = None
    intake: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class ChangePasswordModel(BaseModel):
    current_password: str
    new_password: str