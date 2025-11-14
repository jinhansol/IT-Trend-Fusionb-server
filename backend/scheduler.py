# backend/scheduler.py
# flake8: noqa

from apscheduler.schedulers.background import BackgroundScheduler
from services.news_service import run_news_pipeline
from services.trend_service import get_trend_recommendations
import asyncio


scheduler = BackgroundScheduler()


# -----------------------------
# 뉴스 자동 업데이트 (3시간)
# -----------------------------
def auto_update_news():
    print("🕒 [스케줄러] 뉴스 자동 업데이트 실행")
    run_news_pipeline()


# -----------------------------
# 트렌드 자동 업데이트 (12시간)
# -----------------------------
async def auto_update_trend():
    print("🕒 [스케줄러] 트렌드 자동 업데이트 실행")
    await get_trend_recommendations()


# -----------------------------
# 스케줄러 시작
# -----------------------------
def start_scheduler():
    if scheduler.get_jobs():
        print("⚠️ 스케줄러 이미 실행 중 → 중복 실행 방지")
        return

    scheduler.add_job(auto_update_news, "interval", hours=3, id="news-job")
    scheduler.add_job(lambda: asyncio.run(auto_update_trend()), "interval", hours=12, id="trend-job")

    scheduler.start()
    print("🕐 자동화 스케줄러 실행됨 (뉴스 3h / 트렌드 12h)")

