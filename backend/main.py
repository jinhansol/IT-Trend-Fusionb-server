"""🚀 IT Trend Hub v2 메인 엔트리포인트 — 사용자 인증 + DevDashboard 통합 버전"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ⚙️ 내부 모듈 import (항상 최상단 유지)
from database.models import init_db
from routers import (
    home_router,
    career_router,
    github_router,
    news_router,
    trend_router,
    dev_router,
    auth_router,   # ✅ 새로 추가된 인증 라우터
    protected_router,
    interest_router,
)

# ---------------------------------------------------------
# 1️⃣ 환경 변수 로드 (.env)
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

print(
    "🔍 ENV LOAD CHECK:",
    f"OPENAI={bool(OPENAI_API_KEY)}, NAVER={bool(NAVER_CLIENT_ID)}, GITHUB={bool(GITHUB_TOKEN)}",
)

if not all([OPENAI_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET]):
    print("⚠️ 일부 환경 변수 누락 — .env 파일을 확인하세요.")

# ---------------------------------------------------------
# 2️⃣ FastAPI 앱 초기화
# ---------------------------------------------------------
app = FastAPI(title="IT Trend Hub v2 🚀")

# ---------------------------------------------------------
# 3️⃣ CORS 설정 (React 개발 서버 허용)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 4️⃣ DB 초기화 및 라우터 등록
# ---------------------------------------------------------
init_db()

# ✨ 인증 라우터 (회원가입 / 로그인)
app.include_router(auth_router.router, prefix="/api/auth")

# ✨ 기존 서비스 라우터
app.include_router(home_router.router, prefix="/api/home")
app.include_router(career_router.router, prefix="/api/career")
app.include_router(github_router.router, prefix="/api/github")
app.include_router(news_router.router, prefix="/api/news")
app.include_router(trend_router.router, prefix="/api/trend")
app.include_router(dev_router.router)
app.include_router(auth_router.router,)
app.include_router(protected_router.router)
app.include_router(interest_router.router)

# ---------------------------------------------------------
# 5️⃣ 기본 루트 엔드포인트
# ---------------------------------------------------------
@app.get("/")
def root():
    """서버 정상 작동 확인용"""
    return {"message": "✅ IT Trend Hub v2 Backend Running with Auth + DevDashboard!"}
