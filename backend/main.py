# backend/main.py
# flake8: noqa

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database.models import init_db
from routers import (
    home_router,
    career_router,
    github_router,
    news_router,
    trend_router,
    dev_router,
    auth_router,
    protected_router,
    interest_router,
)
from scheduler import start_scheduler

# --------------------------------------
# 🔧 환경 변수 로드
# --------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

# --------------------------------------
# 🚀 FastAPI 초기화
# --------------------------------------
app = FastAPI(title="IT Trend Hub v2 🚀")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------
# 💾 DB 초기화 + 라우터 등록
# --------------------------------------
init_db()

app.include_router(home_router.router)
app.include_router(news_router.router)
app.include_router(career_router.router)
app.include_router(github_router.router)
app.include_router(trend_router.router)
app.include_router(dev_router.router)
app.include_router(auth_router.router, prefix="/api/auth")
app.include_router(protected_router.router)
app.include_router(interest_router.router)


# ==========================================================
# 🕒 스케줄러 중복 실행 방지 로직
# ==========================================================

# uvicorn --reload 환경에서는 RUN_MAIN="true"로 설정됨
RUN_MAIN_FLAG = os.environ.get("RUN_MAIN", "false")

@app.on_event("startup")
def startup_event():
    """
    ⭐ reload 워커에서는 스케줄러가 실행되지 않도록 보호함
    ⭐ 스케줄러가 이미 실행된 경우 중복 job 등록도 차단됨 (scheduler.py에서 처리)
    """
    if RUN_MAIN_FLAG == "true":
        print("⚠️ Reload 프로세스 → 스케줄러 실행 안 함")
        return

    print("🟢 Main 프로세스 → 스케줄러 실행")
    start_scheduler()


@app.get("/")
def root():
    return {"message": "IT Trend Hub v2 Backend Running 🚀"}
