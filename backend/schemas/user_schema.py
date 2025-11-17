# schemas/user_schema.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        orm_mode = True


class AuthResponse(BaseModel):
    message: str
    user: User
    access_token: str
    token_type: str = "bearer"
