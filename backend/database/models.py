# database/models.py
# flake8: noqa
"""
📦 IT Trend Hub v3 — 완전한 DB 모델 정리본
- UserProfile
- UserInterest
- UserHistory
- UserRecommendation
- NewsFeed
- CareerJob
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text,
    JSON, Float, ForeignKey
)
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# -------------------------------------------------------------------
# ⚙️ DB 연결
# -------------------------------------------------------------------
try:
    # MariaDB Version
    from database.mariadb import Base, engine
except ImportError:
    # Fallback → SQLite (개발용)
    from sqlalchemy.ext.declarative import declarative_base
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "fallback_user_data.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ===================================================================
# 👤 사용자 프로필
# ===================================================================
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    # Personal Dev 모드에서 사용
    main_focus = Column(String(50), default="career")  # career / dev
    role_type = Column(String(50))                    # student, junior, senior...
    career_stage = Column(String(50))                 # 입문 / 취업준비 / 경력직 등
    tech_stack = Column(JSON, default=[])             # ⭐ Dev 핵심 personal 추천용
    interest_topics = Column(JSON, default=[])        # Velog / GitHub 키워드 기반 추천
    preferred_sources = Column(JSON, default=["News", "JobKorea", "GitHub", "Velog"])

    # 활동 정보
    last_login = Column(DateTime, default=datetime.utcnow)
    activity_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    interests = relationship("UserInterest", backref="user", cascade="all, delete-orphan")
    histories = relationship("UserHistory", backref="user", cascade="all, delete-orphan")
    recommendations = relationship("UserRecommendation", backref="user", cascade="all, delete-orphan")


# ===================================================================
# ⭐ 사용자 관심 키워드
# ===================================================================
class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    keyword = Column(String(255), nullable=False)
    category = Column(String(50), default="general")  # trend / dev / career / general

    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 🧩 활동 기록
# ===================================================================
class UserHistory(Base):
    __tablename__ = "user_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))

    action_type = Column(String(50))        # view, click, search
    target_table = Column(String(50))       # news_feed, career_jobs, github, velog 등
    target_id = Column(Integer)

    timestamp = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 💡 LLM 기반 추천 캐시
# ===================================================================
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_type = Column(String(50))         # News, GitHub, Velog, Career
    data_id = Column(Integer)                # 추천된 실제 컨텐츠의 id
    score = Column(Float, default=0.0)       # 중요도 점수
    reason = Column(Text)                    # 요약 및 추천 이유

    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 📰 뉴스 데이터
# ===================================================================
class NewsFeed(Base):
    __tablename__ = "news_feed"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    summary = Column(Text)
    content = Column(Text)
    category = Column(String(50))
    keywords = Column(JSON)
    source = Column(String(100))
    url = Column(String(500))
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 💼 채용 공고 데이터
# ===================================================================
class CareerJob(Base):
    __tablename__ = "career_jobs"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    job_type = Column(String(100))

    url = Column(String(500), unique=True)
    tags = Column(JSON)
    source = Column(String(100))

    posted_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 🚀 DB 초기화 함수
# ===================================================================
def init_db():
    print("📦 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created!")
