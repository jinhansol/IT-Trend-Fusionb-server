# schemas/user_schema.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List

# ✅ [수정 1] 회원가입 시 프론트엔드가 보내는 main_focus를 받을 수 있게 추가
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    main_focus: str 


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ✅ [수정 2] 응답 시 유저의 관심사 정보를 포함해서 보내주도록 필드 추가
class User(BaseModel):
    id: int
    username: str
    email: str
    main_focus: Optional[str] = None
    tech_stack: Optional[List[str]] = []      # 기술 스택 (배열)
    interest_topics: Optional[List[str]] = [] # 관심 주제 (배열)

    class Config:
        orm_mode = True # Pydantic v2에서는 from_attributes = True 권장되나, v1 호환성을 위해 유지


class AuthResponse(BaseModel):
    message: str
    user: User
    access_token: str
    token_type: str = "bearer"