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
from services.news_service import run_news_pipeline   # ⭐ 추가됨


# ---------------------------------------------------------
# 🔧 환경 변수 로드
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

# ---------------------------------------------------------
# 🚀 FastAPI 초기화
# ---------------------------------------------------------
app = FastAPI(title="IT Trend Hub v2 🚀")

# ---------------------------------------------------------
# 🌐 CORS 설정
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 필요하면 도메인 지정 가능
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 💾 DB 초기화 + Router 등록
# ---------------------------------------------------------
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


# =========================================================
# 🕒 스케줄러 중복 실행 방지 (uvicorn reload 대응)
# =========================================================
RUN_MAIN_FLAG = os.environ.get("RUN_MAIN", "false")


# ---------------------------------------------------------
# 🚀 서버 기동 시 스케줄러 시작
# ---------------------------------------------------------
@app.on_event("startup")
def startup_event():
    if RUN_MAIN_FLAG == "true":
        print("⚠️ Reload 프로세스 → 스케줄러 실행 안 함")
        return

    print("🟢 Main 프로세스 → 스케줄러 실행")
    start_scheduler()


# ---------------------------------------------------------
# 🧪 루트 엔드포인트
# ---------------------------------------------------------
@app.get("/")
def root():
    return {"message": "IT Trend Hub v2 Backend Running 🚀"}


# ---------------------------------------------------------
# ⭐⭐ NEW: 크론 직접 호출용 엔드포인트 ⭐⭐
# ---------------------------------------------------------
@app.get("/cron/news")
def cron_news():
    """
    외부에서 직접 크롤러를 실행할 수 있는 엔드포인트.
    스케줄러가 내부적으로도 이걸 호출함.
    """
    run_news_pipeline()
    return {"message": "News Pipeline executed successfully"}
