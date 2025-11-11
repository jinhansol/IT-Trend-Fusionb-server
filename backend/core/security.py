# backend/core/security.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database.mariadb import SessionLocal
from database.models import UserProfile

# ---------------------------------------------------------
# ⚙️ JWT 기본 설정
# ---------------------------------------------------------
SECRET_KEY = "YOUR_SECRET_KEY"  # 🚨 실제 배포 시 .env로 옮겨야 함
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ---------------------------------------------------------
# 🧩 비밀번호 암호화
# ---------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """입력된 비밀번호를 bcrypt 해시로 변환"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """입력된 비밀번호가 저장된 해시와 일치하는지 검증"""
    return pwd_context.verify(plain_password, hashed_password)

# ---------------------------------------------------------
# 🔐 JWT 토큰 관련 함수
# ---------------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    """JWT 디코드 (payload 반환 또는 None)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ---------------------------------------------------------
# 🧠 현재 로그인 사용자 검증 (3단계 핵심)
# ---------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    """JWT 토큰을 해석해 현재 로그인한 사용자 정보를 반환"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="⚠️ 유효하지 않거나 만료된 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    user = db.query(UserProfile).filter(UserProfile.email == email).first()
    db.close()
    if user is None:
        raise credentials_exception

    return user
