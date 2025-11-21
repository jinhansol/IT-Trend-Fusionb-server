# backend/main.py
# flake8: noqa

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# DB 초기화
from database.models import init_db

# 🔥 Routers
from routers import (
    home_router,
    career_router,
    news_router,
    dev_router,            # GitHub + Velog 통합 DevDashboard v3
    trend_router,          # ⭐ Home AI Insight / Trend 요약
    auth_router,
    protected_router,
    interest_router,
)

# 스케줄러 & 뉴스 파이프라인
from scheduler import start_scheduler
from services.news_service import run_news_pipeline


# ---------------------------------------------------------
# 🔧 환경 변수 로드
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)
print("🔍 DEBUG GITHUB_TOKEN:", os.getenv("GITHUB_TOKEN"))


# ---------------------------------------------------------
# 🚀 FastAPI 초기화
# ---------------------------------------------------------
app = FastAPI(title="IT Trend Hub v3 🚀")


# ---------------------------------------------------------
# 🌐 CORS 설정
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


# ---------------------------------------------------------
# 💾 DB 초기화 + Router 등록
# ---------------------------------------------------------
init_db()

# ⬇️ Public 영역
# Public
app.include_router(home_router.router)
app.include_router(news_router.router)
app.include_router(career_router.router)
app.include_router(dev_router.router)
app.include_router(trend_router.router)

# Auth 전용 API
app.include_router(auth_router.router, prefix="/api/auth")

# Protected / Interest → prefix 설정된 후에 등록
app.include_router(protected_router.router)
app.include_router(interest_router.router)



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
# ⭐ cron 직접 호출용 엔드포인트 (뉴스 파이프라인)
# ---------------------------------------------------------
@app.get("/cron/news")
def cron_news():
    run_news_pipeline()
    return {"message": "News Pipeline executed successfully"}
