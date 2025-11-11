# flake8: noqa
"""
📦 IT Trend Hub v2 — 사용자 중심 DB 구조 (관심사 및 메인 섹션 선택 통합)
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text,
    JSON, Float, ForeignKey
)
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# ---------------------------------------------------------
# ⚙️ DB 연결 설정 (MariaDB / SQLite 자동 대응)
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
# 👤 사용자 중심 테이블
# ---------------------------------------------------------
class UserProfile(Base):
    """사용자 프로필 및 관심사"""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    # 🧭 메인 섹션 선택
    # (Career / Dev / Insight 중 하나 — 첫 로그인 시 선택)
    main_focus = Column(String(50), default="career")

    # 💼 관심사 관련 필드
    role_type = Column(String(50))               # ex. Frontend / Backend / AI / Fullstack
    career_stage = Column(String(50))            # ex. Student / JobSeeker / Professional
    tech_stack = Column(JSON, default=[])        # ex. ["React", "Python"]
    interest_topics = Column(JSON, default=[])   # ex. ["Frontend", "AI Ethics", "Cloud Trends"]
    preferred_sources = Column(JSON, default=["News", "JobKorea", "GitHub"])

    # 🧩 활동 상태
    last_login = Column(DateTime, default=datetime.utcnow)
    activity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 🔗 관계 설정
    histories = relationship("UserHistory", backref="user", cascade="all, delete")
    recommendations = relationship("UserRecommendation", backref="user", cascade="all, delete")


class UserHistory(Base):
    """사용자 행동 로그 (피드, 검색, 클릭 등 기록)"""
    __tablename__ = "user_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    action_type = Column(String(50), nullable=False)  # e.g., "view", "click", "search"
    target_table = Column(String(50))                 # e.g., "news_feed", "career_jobs"
    target_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)


class UserRecommendation(Base):
    """LLM 기반 개인화 추천 캐시"""
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_type = Column(String(50))       # ex. "News", "GitHub", "Career"
    data_id = Column(Integer)
    score = Column(Float, default=0.0)
    reason = Column(Text)                  # 추천 이유 (LLM 요약문)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# 📰 피드 기반 데이터 테이블
# ---------------------------------------------------------
class NewsFeed(Base):
    """뉴스 데이터"""
    __tablename__ = "news_feed"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    source = Column(String(100))
    url = Column(String(500), nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class CareerJob(Base):
    """채용 정보 (JobKorea 등 크롤링 데이터)"""
    __tablename__ = "career_jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    company = Column(String(255))
    location = Column(String(255))
    job_type = Column(String(100))
    link = Column(String(500))
    posted_date = Column(DateTime, default=datetime.utcnow)


class TechTrend(Base):
    """기술 트렌드 요약 (OpenAI API 결과 캐시)"""
    __tablename__ = "tech_trends"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255))
    summary = Column(Text)
    trend_score = Column(Integer, default=0)
    source = Column(String(100))
    fetched_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# ✅ DB 초기화 함수
# ---------------------------------------------------------
def init_db():
    """테이블 생성 및 초기화"""
    print("📦 Creating tables in database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")
