# flake8: noqa
"""
📦 IT Trend Hub v3 — 사용자 중심 DB 구조 정리본
- DevDashboard는 실데이터 기반이라 캐시 테이블 제외
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text,
    JSON, Float, ForeignKey
)
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# ---------------------------------------------------------
# ⚙️ DB 연결
# ---------------------------------------------------------
try:
    from database.mariadb import Base, engine
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "user_data.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------
# 👤 사용자 중심 프로필
# ---------------------------------------------------------
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    main_focus = Column(String(50), default="career")

    # 관심사 기반 Dev 개인화에 핵심적으로 사용됨
    role_type = Column(String(50))
    career_stage = Column(String(50))
    tech_stack = Column(JSON, default=[])      # DevDashboard 핵심
    interest_topics = Column(JSON, default=[])
    preferred_sources = Column(JSON, default=["News", "JobKorea", "GitHub", "Velog"])

    last_login = Column(DateTime, default=datetime.utcnow)
    activity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    histories = relationship("UserHistory", backref="user", cascade="all, delete")
    recommendations = relationship("UserRecommendation", backref="user", cascade="all, delete")


# ---------------------------------------------------------
# 🧩 활동 기록
# ---------------------------------------------------------
class UserHistory(Base):
    __tablename__ = "user_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))

    action_type = Column(String(50))        # view, click, search
    target_table = Column(String(50))       # news_feed, career_jobs, github, velog 등
    target_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# 💡 LLM 추천 캐시
# ---------------------------------------------------------
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_type = Column(String(50))       # News, GitHub, Velog, Career
    data_id = Column(Integer)
    score = Column(Float, default=0.0)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# 📰 뉴스
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 💼 채용
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 🚀 DB Init
# ---------------------------------------------------------
def init_db():
    print("📦 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created!")
