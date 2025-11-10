# flake8: noqa
from apscheduler.schedulers.background import BackgroundScheduler
from services.news_service import save_news_to_db
from services.trend_service import get_trend_recommendations
import asyncio

scheduler = BackgroundScheduler()

@scheduler.scheduled_job("interval", hours=3)
def auto_update_news():
    print("🕒 [스케줄러] 뉴스 자동 업데이트 실행")
    save_news_to_db()

@scheduler.scheduled_job("interval", hours=12)
def auto_update_trend():
    print("🕒 [스케줄러] 트렌드 자동 업데이트 실행")
    asyncio.run(get_trend_recommendations())

def start_scheduler():
    scheduler.start()
    print("🕐 자동화 스케줄러 실행됨 (뉴스 3h / 트렌드 12h)")
