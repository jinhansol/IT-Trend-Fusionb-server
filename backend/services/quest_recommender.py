# backend/services/quest_recommender.py
# flake8: noqa

from datetime import datetime, date
from sqlalchemy.orm import Session

from database.models import (
    LearningQuest,
    LearningResource,
    UserProfile,
    UserNodeProgress,
    SkillNode,
    NodeStatus,
)

from services.roadmap_service import get_next_unlocked_node


DAILY_RECOMMEND_COUNT = 5


# -----------------------------------------------------------
# 날짜 포맷
# -----------------------------------------------------------
def today_str():
    return date.today().isoformat()


# -----------------------------------------------------------
# 🔥 유저 tech_stack 기반 점수 계산
# -----------------------------------------------------------
def calculate_interest_score(quest: LearningQuest, user: UserProfile):
    if not user or not user.tech_stack:
        return 0

    score = 0
    qtext = f"{quest.title} {quest.description} {quest.category}".lower()

    for tech in user.tech_stack:
        if tech.lower() in qtext:
            score += 2  # tech는 강한 선호도

    return score


# -----------------------------------------------------------
# 🔥 Node 기반 학습 우선순위 점수
# -----------------------------------------------------------
def node_related_score(quest: LearningQuest, node: SkillNode):
    if not node:
        return 0

    text = f"{quest.title} {quest.description} {quest.category}".lower()

    score = 0

    # Node label 기반
    if node.label and node.label.lower() in text:
        score += 5

    # Node 검색 키워드 기반
    if node.search_keywords:
        for kw in node.search_keywords:
            if kw.lower() in text:
                score += 3

    return score


# -----------------------------------------------------------
# 🔥 LearningResource 기반 자동 생성(보조)
# -----------------------------------------------------------
def auto_generate_from_resources(db: Session, node: SkillNode):
    if not node:
        return []

    keywords = []
    if node.label:
        keywords.append(node.label.lower())
    if node.search_keywords:
        keywords.extend([kw.lower() for kw in node.search_keywords])

    resources = db.query(LearningResource).all()
    matched = []

    for r in resources:
        text = f"{r.title} {r.description} {r.category}".lower()

        if any(kw in text for kw in keywords):
            # 기존 퀘스트 있으면 재활용
            exist_q = db.query(LearningQuest).filter_by(url=r.url).first()
            if exist_q:
                matched.append(exist_q)
                continue

            q = LearningQuest(
                title=r.title,
                description=r.description,
                url=r.url,
                category=r.category,
                xp=50,
                difficulty="easy",
            )
            db.add(q)
            matched.append(q)

    db.commit()
    return matched[:5]


# -----------------------------------------------------------
# 🔥 오늘 추천 생성
# -----------------------------------------------------------
def recommend_today_quests(db: Session, user_id: int):

    today = today_str()

    # ---------------------------
    # 0) 유저 확인
    # ---------------------------
    user = db.query(UserProfile).filter_by(id=user_id).first()
    if not user:
        return []

    # ---------------------------
    # 1) 오늘 이미 추천된 것 있으면 그대로 사용
    # ---------------------------
    already = (
        db.query(LearningQuest)
        .filter(LearningQuest.last_recommended == today)
        .all()
    )
    if len(already) >= DAILY_RECOMMEND_COUNT:
        return already

    # ---------------------------
    # 2) 현재 유저가 진행 중인 Node 찾기
    # ---------------------------
    progress = (
        db.query(UserNodeProgress)
        .filter(
            UserNodeProgress.user_id == user_id,
            UserNodeProgress.status == NodeStatus.UNLOCKED,
        )
        .order_by(UserNodeProgress.id.asc())
        .first()
    )

    current_node = None

    if progress:
        current_node = db.query(SkillNode).filter_by(id=progress.node_db_id).first()
    else:
        current_node = db.query(SkillNode).order_by(SkillNode.id.asc()).first()

    # ---------------------------
    # 3) 완료되지 않은 퀘스트 모으기
    # ---------------------------
    candidates = (
        db.query(LearningQuest)
        .filter(LearningQuest.completed == False)
        .all()
    )

    scored_list = []

    for q in candidates:

        # Recency Score (오래 추천 안됐을수록 점수↑)
        if not q.last_recommended:
            recency_score = 5
        else:
            days = abs(
                (date.today() - datetime.strptime(q.last_recommended, "%Y-%m-%d").date()).days
            )
            recency_score = min(10, days)

        # tech_stack 기반 선호도
        interest_score = calculate_interest_score(q, user)

        # Node 기반 학습 단계 점수
        node_score = node_related_score(q, current_node)

        total = recency_score + interest_score + node_score

        scored_list.append((total, q))

    # ---------------------------
    # 4) Node 기반 자동 생성 보조 추천
    # ---------------------------
    auto_generated = auto_generate_from_resources(db, current_node)

    # auto generate는 높은 가중치 제공
    for q in auto_generated:
        scored_list.append((100, q))  # 최상위 권장

    # ---------------------------
    # 5) 점수 높은 순 정렬 후 상위 N개 선택
    # ---------------------------
    scored_list.sort(key=lambda x: x[0], reverse=True)
    selected = [q for _, q in scored_list[:DAILY_RECOMMEND_COUNT]]

    # ---------------------------
    # 6) 오늘 추천 날짜 기록
    # ---------------------------
    for q in selected:
        q.last_recommended = today

    db.commit()

    return selected


# -----------------------------------------------------------
# 🔥 퀘스트 완료 처리 (현재 구조 유지)
# -----------------------------------------------------------
def complete_quest(db: Session, quest_id: int):
    quest = db.query(LearningQuest).filter_by(id=quest_id).first()
    if not quest:
        return None

    quest.completed = True
    db.commit()
    return quest
