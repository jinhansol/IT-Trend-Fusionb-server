from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from database.mariadb import SessionLocal
from database.models import UserProfile

# ---------------------------------------------------------
# ⚙️ JWT 기본 설정
# ---------------------------------------------------------
SECRET_KEY = "YOUR_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------------------------------------------------------
# 🔐 비밀번호 관련
# ---------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------
# 🔐 JWT 만들기
# ---------------------------------------------------------
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------
# 🔐 필수 로그인 버전 (401 발생)
# ---------------------------------------------------------
def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    필수 로그인 요구 API에서만 사용.
    Authorization 헤더가 없거나 토큰이 잘못되면 즉시 401 발생.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="⚠️ 유효하지 않거나 만료된 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    user = db.query(UserProfile).filter(UserProfile.email == email).first()
    db.close()

    if not user:
        raise credentials_exception

    return user


# ---------------------------------------------------------
# 🔓 Optional 로그인 (fallback)
# ---------------------------------------------------------
def get_current_user_optional(request: Request):
    """
    - Authorization 헤더 없음     → None
    - Bearer 포맷 아님            → None
    - Token 비어있음              → None
    - Token 만료/손상            → None
    - User 없으면                → None
    """

    # 1) Authorization 헤더 없으면 public
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    # 2) Bearer 포맷 검사
    if not auth_header.startswith("Bearer "):
        return None

    # 3) Token 추출
    token = auth_header.split(" ")[1].strip()
    if not token:
        return None

    # 4) JWT decode 시도
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        # ✔️ decode 실패 → 만료 / invalid → None 반환
        return None

    # 5) DB 조회
    db = SessionLocal()
    user = db.query(UserProfile).filter(UserProfile.email == email).first()
    db.close()

    if not user:
        return None

    return user
