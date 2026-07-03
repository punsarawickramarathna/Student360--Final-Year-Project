from pydantic import BaseModel

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