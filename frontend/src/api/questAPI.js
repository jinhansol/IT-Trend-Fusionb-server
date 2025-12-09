// src/api/questAPI.js
import axios from "axios";

const API = "http://localhost:8000/api/quest";

// ------------------------------------------------------------
// ⭐ 오늘의 학습 퀘스트 5개 가져오기
// ------------------------------------------------------------
export async function fetchTodayQuests(userId) {
  try {
    const res = await axios.get(`${API}/today/${userId}`);
    return res.data; // List<QuestResponse>
  } catch (err) {
    console.error("[QuestAPI] Failed to fetch today quests:", err);
    throw err;
  }
}

// ------------------------------------------------------------
// ⭐ 퀘스트 완료 처리
// ------------------------------------------------------------
export async function completeQuest(userId, questId) {
  try {
    const res = await axios.post(`${API}/complete/${userId}/${questId}`);
    return res.data.quest; // QuestCompleteResponse.quest
  } catch (err) {
    console.error("[QuestAPI] Failed to complete quest:", err);
    throw err;
  }
}
