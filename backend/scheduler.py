# backend/scheduler.py
# flake8: noqa

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import asyncio
import threading

from services.news_service import run_news_pipeline
from services.trend_service import update_global_trends  # ✅ 여기!

KST = timezone("Asia/Seoul")
scheduler = BackgroundScheduler(timezone=KST)


def auto_update_news():
    print("🕒 [스케줄러] 뉴스 자동 업데이트 실행")
    run_news_pipeline()


def run_global_trend():
    asyncio.run(update_global_trends())


def start_scheduler():
    if scheduler.get_jobs():
        print("⚠ 스케줄러 이미 실행 중 → 중복 방지")
        return

    # 뉴스: 0,3,6,9,12,15,18,21
    scheduler.add_job(
        auto_update_news,
        CronTrigger(hour="0,3,6,9,12,15,18,21", minute=0),
        id="news-cron",
    )

    # 전역 트렌드: 매일 00시, 12시
    scheduler.add_job(
        run_global_trend,
        CronTrigger(hour="0,12", minute=0),
        id="global-trend-cron",
    )

    scheduler.start()
    print("🕐 스케줄러 실행됨 (뉴스 + 전역 트렌드)")

    print("🚀 서버 시작 → 뉴스 즉시 실행")
    auto_update_news()

    print("🚀 서버 시작 → 전역 트렌드 즉시 실행")
    threading.Thread(
        target=lambda: asyncio.run(update_global_trends()),
        daemon=True,
    ).start()
