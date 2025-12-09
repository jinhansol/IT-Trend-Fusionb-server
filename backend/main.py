# backend/main.py
# flake8: noqa

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# DB 초기화
from database.models import init_db

# Routers
from routers import (
    home_router,       # /api/home
    dev_router,        # /api/dev
    user_router,       # /api/auth, /api/user
    protected_router,  # /api/protected
    roadmap_router,    # /api/roadmap
    ai_router,         # /api/ai
    quest_router,      # /api/quest
    # career_router,     # ⭐ 다시 활성화
    quiz_router,
)

# Scheduler (news)
from scheduler import start_scheduler


# --------------------------------------------------------------
# 🔧 Load Environment
# --------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)


# --------------------------------------------------------------
# 🚀 FastAPI Initialization
# --------------------------------------------------------------
app = FastAPI(
    title="DevHub API v4 (Gamified + Career Enabled) 🚀",
    version="4.0.1",
)


# --------------------------------------------------------------
# 🌐 CORS
# --------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


# --------------------------------------------------------------
# 💾 Init DB + Register Routers
# --------------------------------------------------------------
init_db()

# 1️⃣ User
app.include_router(user_router.router, prefix="/api")

# 2️⃣ Home (News + Trend)
app.include_router(home_router.router)

# 3️⃣ Dev Community
app.include_router(dev_router.router)

# ⭐ 4️⃣ Career (Reactivate)
# 챗GPT가 로직 수정할 필요 없이 당장 동작 가능 상태로 유지
# app.include_router(career_router.router, prefix="/api/career")

# 5️⃣ Roadmap
app.include_router(roadmap_router.router)

# 6️⃣ Today Quests
app.include_router(quest_router.router)

# 7️⃣ AI
app.include_router(ai_router.router, prefix="/api/ai")

# 8️⃣ Protected
app.include_router(protected_router.router, prefix="/api")

app.include_router(quiz_router.router, prefix="/api/quiz", tags=["Quiz"])


# --------------------------------------------------------------
# 🕒 Scheduler
# --------------------------------------------------------------
RUN_MAIN_FLAG = os.environ.get("RUN_MAIN", "false")

@app.on_event("startup")
def startup_event():
    if RUN_MAIN_FLAG == "true":
        print("⚠️ Reload Process → Scheduler Skipped")
        return

    print("🟢 Starting Scheduler...")
    start_scheduler()


# --------------------------------------------------------------
# Root and Health Check
# --------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "DevHub v4 Backend Running (Gamified + Career) 🚀"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
