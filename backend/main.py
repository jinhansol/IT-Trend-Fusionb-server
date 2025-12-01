# backend/main.py
# flake8: noqa

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# DB 초기화
from database.models import init_db

# 🔥 Routers (리팩토링 완료된 통합 라우터들)
from routers import (
    home_router,      # (Home + News + Trend 통합)
    career_router,    # (Career + Learning + JobKorea/Saramin 통합)
    dev_router,       # (Dev + OKKY/Dev.to 통합)
    user_router,      # (Auth + Interest + User 통합)
    protected_router, # (JWT 테스트용 유지)
)

# 스케줄러 & 뉴스 파이프라인
from scheduler import start_scheduler
# ✅ 변경: news_service가 home_service로 통합됨
from services.home_service import run_news_pipeline


# ---------------------------------------------------------
# 🔧 환경 변수 로드
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)
# print("🔍 DEBUG GITHUB_TOKEN:", os.getenv("GITHUB_TOKEN")) # 디버그용 로그는 주석 처리 권장


# ---------------------------------------------------------
# 🚀 FastAPI 초기화
# ---------------------------------------------------------
app = FastAPI(title="IT Trend Hub v3 🚀")


# ---------------------------------------------------------
# 🌐 CORS 설정
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 배포 시에는 구체적인 도메인으로 변경 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------
# 💾 DB 초기화 + Router 등록
# ---------------------------------------------------------
init_db()

# 1️⃣ User & Auth (Prefix: /api)
# 내부 라우터에 /auth, /interests 등의 경로가 정의되어 있으므로 /api만 붙임
# 최종 경로 예시: /api/auth/login, /api/interests/save
app.include_router(user_router.router, prefix="/api")

# 2️⃣ Domain Routers (각 라우터 내부에 prefix=/api/... 설정됨)
app.include_router(home_router.router)    # /api/home
app.include_router(career_router.router)  # /api/career
app.include_router(dev_router.router)     # /api/dev

# 3️⃣ Protected (Test용)
app.include_router(protected_router.router)


# ---------------------------------------------------------
# 🕒 스케줄러 (뉴스 파이프라인 전용)
# ---------------------------------------------------------
RUN_MAIN_FLAG = os.environ.get("RUN_MAIN", "false")

@app.on_event("startup")
def startup_event():
    """
    uvicorn --reload 실행 시 두 번 실행되는 문제 회피용
    """
    if RUN_MAIN_FLAG == "true":
        print("⚠️ Reload 프로세스 → 스케줄러 실행 안 함")
        return

    print("🟢 Main 프로세스 → 스케줄러 실행")
    start_scheduler()


# ---------------------------------------------------------
# 🧪 Root 엔드포인트
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"message": "IT Trend Hub v3 Backend Running 🚀"}


# ---------------------------------------------------------
# ⭐ cron 직접 호출용 엔드포인트 (뉴스 파이프라인 테스트용)
# ---------------------------------------------------------
@app.get("/cron/news")
def cron_news():
    run_news_pipeline()
    return {"message": "News Pipeline executed successfully"}