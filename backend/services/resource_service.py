# backend/services/roadmap_service.py
# flake8: noqa

from sqlalchemy.orm import Session
from datetime import datetime

from database.models import (
    SkillTrack,
    SkillNode,
    UserNodeProgress,
    NodeStatus,
    LearningQuest,
    UserQuestProgress
)


# ================================================================
# 📌 유저가 어떤 챕터(마지막 완료 노드)에 있는지 계산
# ================================================================
def get_user_current_chapter(db: Session, user_id: int | None):
    if not user_id:
        return None

    last_completed = (
        db.query(UserNodeProgress)
        .filter(UserNodeProgress.user_id == user_id)
        .filter(UserNodeProgress.status == NodeStatus.COMPLETED)
        .order_by(UserNodeProgress.completed_at.desc())
        .first()
    )

    if not last_completed:
        return None

    node = db.query(SkillNode).filter_by(id=last_completed.node_db_id).first()
    if not node:
        return None

    return node.label.lower()


# ================================================================
# 📌 chapter 기반 추천 카테고리 (퀘스트 필터에 사용)
# ================================================================
def get_related_categories(chapter: str | None):
    if not chapter:
        return ["html", "css", "js", "general"]

    mapping = {
        "html": ["html", "css"],
        "css": ["css", "html", "js"],
        "javascript": ["js", "html"],
        "react": ["react", "js"],
        "python": ["python", "db"],
        "mysql": ["db", "python"],
        "git": ["git", "tools"],
    }
    return mapping.get(chapter, ["general"])


# ================================================================
# 📌 로드맵 조회 (personal/public 자동 지원)
# ================================================================
def get_roadmap(db: Session, track_slug: str, user_id: int | None):

    track = db.query(SkillTrack).filter_by(slug=track_slug).first()
    if not track:
        return None

    nodes = db.query(SkillNode).filter_by(track_id=track.id).all()
    progress_map = {}

    # personal 모드일 때만 user progress 로드
    if user_id:
        user_progress = db.query(UserNodeProgress).filter_by(user_id=user_id).all()
        progress_map = {p.node_db_id: p.status for p in user_progress}

    # node_id(string) → db_id(int) 변환
    str_to_db = {node.node_id: node.id for node in nodes}

    result_nodes = []
    for node in nodes:

        # -------------------- PERSONAL 모드 --------------------
        if user_id:
            status = progress_map.get(node.id, NodeStatus.LOCKED)

            # prerequisites가 없으면 자동으로 UNLOCKED
            if not node.prerequisites:
                status = NodeStatus.UNLOCKED

            else:
                unlockable = True
                for parent in node.prerequisites:
                    parent_db = str_to_db.get(parent)
                    if not parent_db or progress_map.get(parent_db) != NodeStatus.COMPLETED:
                        unlockable = False
                if unlockable and status != NodeStatus.COMPLETED:
                    status = NodeStatus.UNLOCKED

        # -------------------- PUBLIC 모드 --------------------
        else:
            status = NodeStatus.UNLOCKED if node == nodes[0] else NodeStatus.LOCKED

        # -------------------- 노드에 연결된 퀘스트 상태 --------------------
        quest_status = None
        if node.main_quest_id:
            qp = db.query(UserQuestProgress).filter_by(
                user_id=user_id, quest_id=node.main_quest_id
            ).first()
            quest_status = qp.status if qp else "pending"

        result_nodes.append({
            "db_id": node.id,
            "node_id": node.node_id,
            "label": node.label,
            "description": node.description,
            "icon": node.icon_slug,
            "position": node.position,
            "status": status,
            "xp": node.xp_reward,
            "prerequisites": node.prerequisites,
            "resource_link": node.resource_link,
            "thumbnail": node.thumbnail,
            "main_quest_id": node.main_quest_id,
            "quest_status": quest_status,
        })

    return {
        "track_title": track.title,
        "track_desc": track.description,
        "nodes": result_nodes,
    }


# ================================================================
# 📌 노드 완료 처리 → 퀘스트도 함께 COMPLETED 처리
# ================================================================
def complete_node(db: Session, user_id: int, node_db_id: int):

    # Node Progress 업데이트
    progress = (
        db.query(UserNodeProgress)
        .filter_by(user_id=user_id, node_db_id=node_db_id)
        .first()
    )

    if not progress:
        progress = UserNodeProgress(
            user_id=user_id,
            node_db_id=node_db_id,
            status=NodeStatus.COMPLETED,
            completed_at=datetime.utcnow(),
        )
        db.add(progress)
    else:
        progress.status = NodeStatus.COMPLETED
        progress.completed_at = datetime.utcnow()

    db.commit()

    # 해당 노드 연결된 Quest도 자동 완료
    _complete_related_quest(db, user_id, node_db_id)

    # 다음 노드 자동 Unlock
    _unlock_next_nodes(db, user_id, node_db_id)

    return progress


# ================================================================
# 📌 Node → 연결된 Quest 자동 완료
# ================================================================
def _complete_related_quest(db: Session, user_id: int, node_db_id: int):

    node = db.query(SkillNode).filter_by(id=node_db_id).first()
    if not node or not node.main_quest_id:
        return

    # 기존 퀘스트 진행 기록 체크
    qp = (
        db.query(UserQuestProgress)
        .filter_by(user_id=user_id, quest_id=node.main_quest_id)
        .first()
    )

    if qp:
        qp.status = "completed"
        qp.completed_at = datetime.utcnow()
    else:
        db.add(
            UserQuestProgress(
                user_id=user_id,
                quest_id=node.main_quest_id,
                status="completed",
                completed_at=datetime.utcnow(),
            )
        )
    db.commit()


# ================================================================
# 📌 prerequisites 충족한 다음 노드 자동 해금
# ================================================================
def _unlock_next_nodes(db: Session, user_id: int, node_db_id: int):
    node = db.query(SkillNode).filter_by(id=node_db_id).first()
    if not node:
        return

    next_nodes = (
        db.query(SkillNode)
        .filter(SkillNode.prerequisites.contains([node.node_id]))
        .all()
    )

    for n in next_nodes:
        exists = (
            db.query(UserNodeProgress)
            .filter_by(user_id=user_id, node_db_id=n.id)
            .first()
        )
        if exists:
            continue

        db.add(
            UserNodeProgress(
                user_id=user_id,
                node_db_id=n.id,
                status=NodeStatus.UNLOCKED,
            )
        )

    db.commit()
