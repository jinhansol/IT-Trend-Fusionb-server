# backend/services/quest_service.py
# flake8: noqa

from datetime import date
from sqlalchemy.orm import Session

from database.models import (
    LearningQuest,
    LearningResource,
    UserProfile,
    UserNodeProgress,
    SkillNode,
    NodeStatus,
)

# roadmap_service에서 노드 완료 함수 가져오기
from services.roadmap_service import complete_node


def today_str():
    return date.today().isoformat()

# ... (recommend_from_node, generate_quests_from_resources 함수는 기존 유지) ...
# (코드가 너무 길어지니 변경 없는 부분은 생략 표시합니다. 위 함수들은 그대로 두세요!)

# =====================================================================
# 📌 3) 오늘의 추천 퀘스트 생성 (기존 유지)
# =====================================================================
def get_today_quests(db: Session, user_id: int):
    # ... (기존 코드 그대로 유지) ...
    # 기존 로직이 잘 작동하므로 변경하지 않았습니다.
    # 파일 내에 기존 코드가 있다면 그대로 두셔도 됩니다.
    
    # 편의를 위해 앞부분 생략하고, 변경된 complete_quest 위주로 작성합니다.
    pass 


# =====================================================================
# 📌 4) 퀘스트 완료 처리 (⭐ 핵심 수정)
# =====================================================================
def complete_quest(db: Session, user_id: int, quest_id: int):

    quest = db.query(LearningQuest).filter_by(id=quest_id).first()
    if not quest:
        return None

    # 1. 퀘스트 완료 상태 변경
    quest.completed = True
    quest.last_recommended = None

    # 2. 유저 XP 지급
    user = db.query(UserProfile).filter_by(id=user_id).first()
    if user:
        user.current_xp += quest.xp
        while user.current_xp >= 100:
            user.current_xp -= 100
            user.level += 1

    # 3. ⭐ [핵심] 형제 퀘스트(같은 노드) 모두 완료 체크
    if quest.node_db_id:
        # 같은 노드 ID를 가진 모든 퀘스트 조회
        sibling_quests = db.query(LearningQuest).filter(
            LearningQuest.node_db_id == quest.node_db_id
        ).all()
        
        # 하나라도 안 깬 게 있는지 확인 (all returns True if list is empty or all true)
        all_cleared = all(q.completed for q in sibling_quests)
        
        # 전부 다 깼을 때만 노드 완료 처리!
        if all_cleared:
            print(f"🎉 Node {quest.node_db_id} All Quests Cleared! Unlocking Next...")
            complete_node(db, user_id, quest.node_db_id)
    
    # (기존의 불안정한 텍스트 매칭 로직은 제거하거나 else로 처리)
    
    db.commit()
    return quest


def reset_today_recommendations(db: Session):
    quests = db.query(LearningQuest).all()
    for q in quests:
        q.last_recommended = None
    db.commit()
    return True