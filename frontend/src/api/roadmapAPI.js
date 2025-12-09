// src/api/roadmapAPI.js
import axios from "axios";

const BASE_URL = "http://localhost:8000/api/roadmap";

// 🔹 공통 인증 헤더
function getAuthHeader() {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ===============================================================
   📌 로드맵 조회(fetchRoadmap)
================================================================ */
export async function fetchRoadmap(slug = "public-preview", userId = null) {
  try {
    let url = "";

    // ⭐ 1) Public 로드맵인데 '로그인된 유저'라면 -> 개인 진행상황 포함된 경로 요청
    if (slug === "public" && userId) {
      url = `${BASE_URL}/web-roadmap/${userId}`;
    }

    // ⭐ 2) Public 기본 로드맵 (비로그인/체험판용 - 초기화된 상태)
    else if (slug === "public-preview" || slug === "public") {
      url = `${BASE_URL}/public`;
    }

    // ⭐ 3) Personal 로드맵
    else if (slug === "personal") {
      if (!userId) throw new Error("❌ personal 로드맵은 userId가 필요합니다.");
      url = `${BASE_URL}/personal/${userId}`;
    }

    // ⭐ 4) fallback → slug 그대로 사용
    else {
      url = `${BASE_URL}/${slug}`;
    }

    const res = await axios.get(url, {
      withCredentials: true,
      headers: {
        ...getAuthHeader(),
      },
    });

    return res.data; // track_title, track_desc, nodes
  } catch (err) {
    console.error("❌ fetchRoadmap Error:", err);
    throw err;
  }
}

/* ===============================================================
   📌 노드 완료 처리 (personal roadmap 기준)
================================================================ */
export async function completeNode(userId, nodeDbId) {
  try {
    if (!userId) throw new Error("❌ completeNode는 userId가 필요합니다.");

    const url = `${BASE_URL}/complete/${userId}/${nodeDbId}`;

    const res = await axios.post(
      url,
      {},
      {
        withCredentials: true,
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeader(),
        },
      }
    );

    return res.data;
  } catch (err) {
    console.error("❌ completeNode Error:", err);
    throw err;
  }
}