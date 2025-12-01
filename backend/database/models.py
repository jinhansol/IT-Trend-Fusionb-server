# database/models.py
# flake8: noqa
"""
📦 IT Trend Hub v4 — DB 모델 (OKKY / Tistory / Dev.to 기반)
기존 v3 모델에 DevPost / DevUserPreference 추가 + view_count 필드 확정
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
    from database.mariadb import Base, engine
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "fallback_user_data.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ===================================================================
# 👤 사용자 프로필 (기존)
# ===================================================================
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    main_focus = Column(String(50), default="career")
    role_type = Column(String(50))
    career_stage = Column(String(50))
    tech_stack = Column(JSON, default=[])
    interest_topics = Column(JSON, default=[])
    preferred_sources = Column(JSON, default=["News", "JobKorea", "GitHub", "Velog"])

    last_login = Column(DateTime, default=datetime.utcnow)
    activity_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interests = relationship("UserInterest", backref="user", cascade="all, delete-orphan")
    histories = relationship("UserHistory", backref="user", cascade="all, delete-orphan")
    recommendations = relationship("UserRecommendation", backref="user", cascade="all, delete-orphan")


# ===================================================================
# ⭐ 사용자 관심 키워드 (기존)
# ===================================================================
class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    keyword = Column(String(255), nullable=False)
    category = Column(String(50), default="general")

    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 🧩 활동 기록 (기존)
# ===================================================================
class UserHistory(Base):
    __tablename__ = "user_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))

    action_type = Column(String(50))
    target_table = Column(String(50))
    target_id = Column(Integer)

    timestamp = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 💡 LLM 기반 추천 캐시 (기존)
# ===================================================================
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_type = Column(String(50))
    data_id = Column(Integer)
    score = Column(Float, default=0.0)
    reason = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)


# ===================================================================
# 📰 뉴스 데이터 (기존)
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
# 💼 채용 공고 데이터 (기존)
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
# 🆕 DevDashboard v4 — 통합 개발 게시글 테이블
# ===================================================================
class DevPost(Base):
    __tablename__ = "dev_posts"

    id = Column(Integer, primary_key=True, index=True)

    # 출처: okky / tistory / devto
    source = Column(String(50), index=True)

    # 소스별 고유 식별자 (okky-id, tistory slug, devto id 등)
    source_id = Column(String(255), index=True)

    # 공통 필드
    title = Column(String(255))
    url = Column(String(500))
    author = Column(String(255), nullable=True)

    summary = Column(Text, nullable=True)
    tags = Column(JSON, default=[])

    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # 🆕 추가: 조회수 (OKKY에서 지원)
    view_count = Column(Integer, default=0)

    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    # -------------------------------------------------------------
    # 🆕 추가되는 핵심 컬럼 4개
    # -------------------------------------------------------------
    topic_primary = Column(String(50), nullable=True)   # 키워드 기반 자동 분류
    issue_primary = Column(String(50), nullable=True)

    topic_ai = Column(String(50), nullable=True)        # AI 기반 의미 분류
    issue_ai = Column(String(50), nullable=True)



# ===================================================================
# 🆕 DevDashboard v4 — 사용자 선호도
# ===================================================================
class DevUserPreference(Base):
    __tablename__ = "dev_user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))

    favorite_tags = Column(JSON, default=[])
    favorite_sources = Column(JSON, default=["okky", "tistory", "devto"])

    preference_score = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ===================================================================
# 🚀 DB 초기화 함수
# ===================================================================
def init_db():
    print("📦 Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created!")
