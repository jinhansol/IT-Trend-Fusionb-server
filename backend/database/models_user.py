# backend/database/models_user.py (새로 추가 권장)
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.mariadb import Base

# 🧍 사용자 프로필
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role_type = Column(String(50))                  # ex. 'Frontend', 'Backend', 'AI'
    tech_stack = Column(JSON, default=[])           # ex. ["React", "Python", "AWS"]
    career_stage = Column(String(50))               # ex. 'Student', 'JobSeeker', 'Professional'
    interest_topics = Column(JSON, default=[])      # ex. ["AI", "Cloud", "Data"]
    preferred_sources = Column(JSON, default=["News", "JobKorea", "GitHub"])
    last_login = Column(DateTime, default=datetime.utcnow)
    activity_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    interests = relationship("UserInterest", backref="user", cascade="all, delete")
    histories = relationship("UserHistory", backref="user", cascade="all, delete")
    recommendations = relationship("UserRecommendation", backref="user", cascade="all, delete")


# 🧠 사용자 관심 키워드
class UserInterest(Base):
    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    keyword = Column(String(255), nullable=False)
    category = Column(String(100), default="general")  # ex. 'career', 'learn', 'trend'
    created_at = Column(DateTime, default=datetime.utcnow)


# 📜 사용자 활동 히스토리
class UserHistory(Base):
    __tablename__ = "user_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    action_type = Column(String(50), nullable=False)   # 'search', 'click', 'save', 'share'
    target_table = Column(String(50))                  # 'news_feed', 'career_jobs', etc.
    target_id = Column(Integer)                        # 해당 테이블의 데이터 ID
    timestamp = Column(DateTime, default=datetime.utcnow)


# 🧩 개인화 추천 캐시 테이블 (LLM or Matching 기반)
class UserRecommendation(Base):
    __tablename__ = "user_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"))
    source_type = Column(String(50))                  # 'news', 'career', 'tech'
    data_id = Column(Integer)                         # 추천된 데이터의 ID
    score = Column(Float, default=0.0)                # 매칭 점수
    reason = Column(Text)                             # 추천 근거 (LLM 요약문 등)
    created_at = Column(DateTime, default=datetime.utcnow)
