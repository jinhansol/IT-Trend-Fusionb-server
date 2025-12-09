# backend/scheduler.py
# flake8: noqa

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
import asyncio
import threading

# ✅ 변경: 통합된 서비스에서 함수 가져오기
from services.home_service import run_news_pipeline  # News + Trend 통합됨
# from services.career_service import run_career_pipeline
from services.dev_service import save_posts
from services.dev_scraper import crawl_okky, crawl_devto # ✅ 함수명 변경 반영

from database.mariadb import SessionLocal

KST = timezone("Asia/Seoul")
scheduler = BackgroundScheduler(timezone=KST)


# -------------------------------------------------------------
# 🔄 뉴스 자동 업데이트
# -------------------------------------------------------------
def auto_update_news():
    print("🕒 [스케줄러] 뉴스 자동 업데이트 실행")
    try:
        run_news_pipeline()
    except Exception as e:
        print("❌ 뉴스 업데이트 오류:", e)


# -------------------------------------------------------------
# 🔄 Career 자동 업데이트
# -------------------------------------------------------------
# def auto_update_career():
#     print("🕒 [스케줄러] Career 자동 업데이트 실행")
#     try:
#         run_career_pipeline()
#     except Exception as e:
#         print("❌ Career 업데이트 오류:", e)


# -------------------------------------------------------------
# 🔄 Dev 자동 업데이트 (OKKY + Dev.to)
# -------------------------------------------------------------
def auto_update_dev():
    print("🕒 [스케줄러] Dev(OKKY/Dev.to) 자동 업데이트 실행")
    db = SessionLocal()
    try:
        # ✅ 함수명 변경 (fetch_... -> crawl_...)
        okky_raw = crawl_okky(limit=50)
        devto_raw = crawl_devto(limit=50)

        inserted1, updated1 = save_posts(db, okky_raw)
        inserted2, updated2 = save_posts(db, devto_raw)

        print("📌 Dev 업데이트 결과:")
        print(f"  • OKKY   → inserted={inserted1}, updated={updated1}")
        print(f"  • Dev.to → inserted={inserted2}, updated={updated2}")

    except Exception as e:
        print("❌ Dev 업데이트 오류:", e)
    finally:
        db.close()


# -------------------------------------------------------------
# 🚀 스케줄러 시작
# -------------------------------------------------------------
def start_scheduler():
    if scheduler.get_jobs():
        print("⚠ 스케줄러 이미 실행 중 → 중복 방지")
        return

    # 📰 뉴스: 3시간 간격
    scheduler.add_job(
        auto_update_news,
        CronTrigger(hour="0,3,6,9,12,15,18,21", minute=0),
        id="news-cron",
    )

    # # 💼 Career: 4시간 간격
    # scheduler.add_job(
    #     auto_update_career,
    #     CronTrigger(hour="0,4,8,12,16,20", minute=10),
    #     id="career-cron",
    # )

    # 💬 DevFeed: 2시간 간격
    scheduler.add_job(
        auto_update_dev,
        CronTrigger(hour="1,3,5,7,9,11,13,15,17,19,21,23", minute=5),
        id="dev-cron",
    )

    scheduler.start()
    print("🕐 스케줄러 실행됨 (뉴스 + Career + DevFeed)")

    # 🔥 서버 부팅 직후 즉시 실행 (테스트용)
    # (너무 많으면 서버 켜질 때 느리니까 필요하면 주석 처리)
    print("🚀 서버 시작 → 뉴스 즉시 실행")
    threading.Thread(target=auto_update_news, daemon=True).start()

    # print("🚀 서버 시작 → Career 즉시 실행")
    # threading.Thread(target=auto_update_career, daemon=True).start()

    print("🚀 서버 시작 → DevFeed 즉시 실행")
    threading.Thread(target=auto_update_dev, daemon=True).start()