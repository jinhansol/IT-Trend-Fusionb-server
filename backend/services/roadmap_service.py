# backend/services/roadmap_service.py
# flake8: noqa

from sqlalchemy.orm import Session
from datetime import datetime
from database.models import (
    SkillTrack, SkillNode, UserNodeProgress, NodeStatus
)

# ================================================================
# 📌 1) 유저 현재 챕터
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
# 📌 2) chapter 기반 추천 카테고리
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
# 📌 3) 로드맵 조회 (public/personal 자동 지원)
# ================================================================
def get_roadmap(db: Session, track_slug: str, user_id: int | None):

    # 1) 트랙 조회
    track = db.query(SkillTrack).filter_by(slug=track_slug).first()
    if not track:
        return None

    # 2) 스킬 노드 전체
    nodes = db.query(SkillNode).filter_by(track_id=track.id).all()

    # 3) personal 모드 → 유저 진행 정보 조회
    progress_map = {}
    if user_id:
        user_progress = db.query(UserNodeProgress).filter_by(user_id=user_id).all()
        progress_map = {p.node_db_id: p.status for p in user_progress}

    node_str_to_db = {n.node_id: n.id for n in nodes}

    # 4) 응답 노드 리스트 구성
    result_nodes = []
    for node in nodes:
        
        # ------------------------------------------------------------
        # 🔥 [수정] 퀘스트 데이터 구성 및 완료 여부 강제 초기화 로직
        # ------------------------------------------------------------
        quests_data = []
        
        # user_id가 없으면(Public 모드) 퀘스트 전체 완료 여부도 False로 시작
        all_quests_completed = True if (node.quests and user_id) else False 

        for q in node.quests:
            # ⭐ [핵심 수정] user_id가 없으면 무조건 미완료(False) 처리
            # 이렇게 해야 새로고침 시(user_id=None일 때) 퀘스트가 초기화되어 보입니다.
            is_completed = q.completed if user_id else False

            quests_data.append({
                "quest_id": q.id,
                "node_db_id": node.id,
                "title": q.title,
                "description": q.description,
                "xp": q.xp,
                "category": q.category,
                "url": q.url, 
                "resource_link": q.url,
                "completed": is_completed  # 수정된 상태값 사용
            })
            
            # 하나라도 안 깬 게 있으면(혹은 강제 False면) 전체 완료 X
            if not is_completed:
                all_quests_completed = False
        
        if not node.quests:
            all_quests_completed = False


        # ----------------------------
        # 🔹 4-1) 상태(Status) 결정
        # ----------------------------
        if user_id:
            # 1. DB에 완료 기록이 있으면 완료
            if node.id in progress_map and progress_map[node.id] == NodeStatus.COMPLETED:
                status = NodeStatus.COMPLETED
            
            # 2. 퀘스트가 다 깨져있으면 완료로 간주
            elif all_quests_completed:
                status = NodeStatus.COMPLETED

            # 3. 해금(Unlock) 여부 판단
            elif not node.prerequisites:
                status = NodeStatus.UNLOCKED
            else:
                unlockable = True
                for parent in node.prerequisites:
                    parent_db = node_str_to_db.get(parent)
                    
                    # 부모가 완료되었는지 확인
                    parent_node = next((n for n in nodes if n.id == parent_db), None)
                    is_parent_done = False

                    # 부모 DB 기록 확인
                    if parent_db in progress_map and progress_map[parent_db] == NodeStatus.COMPLETED:
                        is_parent_done = True
                    # 부모 퀘스트 확인 (user_id가 있을 때만 유효)
                    elif parent_node and parent_node.quests:
                         # 여기도 마찬가지로 user_id가 있을 때만 q.completed를 믿음
                         if all(q.completed for q in parent_node.quests):
                             is_parent_done = True
                    
                    if not is_parent_done:
                        unlockable = False
                        break
                
                status = NodeStatus.UNLOCKED if unlockable else NodeStatus.LOCKED
        else:
            # ⭐ user_id가 없으면(Public 모드) 무조건 첫 번째만 UNLOCKED
            status = NodeStatus.UNLOCKED if node == nodes[0] else NodeStatus.LOCKED

        # ============================================================
        # 🔥 6) 최종 노드 데이터 조립
        # ============================================================
        result_nodes.append({
            "db_id": node.id,
            "id": node.node_id,
            "label": node.label,
            "description": node.description,
            "icon": node.icon_slug,
            "position": node.position,
            "status": status,
            "xp": node.xp_reward,
            "prerequisites": node.prerequisites,
            "resource_link": node.resource_link,
            "thumbnail": node.thumbnail,
            "quests": quests_data,      # 수정된 퀘스트 리스트
        })

    return {
        "track_title": track.title,
        "track_desc": track.description,
        "nodes": result_nodes,
    }


# ================================================================
# 📌 4) 노드 완료 처리 + 다음 노드 자동 해금
# ================================================================
def complete_node(db: Session, user_id: int, node_db_id: int):
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

    _unlock_next_nodes(db, user_id, node_db_id)
    return progress


# ================================================================
# 📌 5) 다음 노드 자동 해금 로직
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

        db.add(UserNodeProgress(
            user_id=user_id,
            node_db_id=n.id,
            status=NodeStatus.UNLOCKED
        ))

    db.commit()