// src/api/careerAPI.js

const BASE_URL = "http://127.0.0.1:8000/api/career";

/**
 * Career Dashboard API
 * - 백엔드에서 Public/Personal 모드 및 차트 데이터를 받아옵니다.
 */
export async function fetchCareerDashboard(endpoint = "/dashboard") {
  const token = localStorage.getItem("token");

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    
    return {
      mode: data.mode || "public",
      jobs: data.jobs || [],
      // 백엔드에서 분리해서 보내주는 트렌드 데이터 연결
      frontend_trends: data.frontend_trends || [], 
      backend_trends: data.backend_trends || [],
      user_skills: data.user_skills || [],
    };
  } catch (e) {
    console.error("❌ [fetchCareerDashboard] 오류:", e);
    return { 
        mode: "public", jobs: [], user_skills: [],
        frontend_trends: [], backend_trends: [] 
    };
  }
}

/**
 * 🔄 [NEW] 워크넷 데이터 수동 갱신 (관리자/테스트용)
 */
export async function refreshCareerData() {
  const token = localStorage.getItem("token");
  try {
    const res = await fetch(`${BASE_URL}/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });
    if (!res.ok) throw new Error("Refresh Failed");
    return await res.json();
  } catch (e) {
    console.error("❌ Refresh Error:", e);
    return null;
  }
}

/**
 * 📚 AI 학습 추천
 */
export async function fetchLearningRecommend() {
  const token = localStorage.getItem("token");

  try {
    const res = await fetch(`${BASE_URL}/learning`, {
      headers: { 
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });

    if (!res.ok) throw new Error("API Error");

    const data = await res.json();
    return data.learning || [];
  } catch (e) {
    console.error("❌ fetchLearningRecommend 오류:", e);
    return [];
  }
}

/**
 * 페이징된 채용 공고 API
 */
export async function fetchPagedJobs(page = 1, size = 6) {
  try {
    const res = await fetch(
      `${BASE_URL}/jobs?page=${page}&size=${size}`,
      {
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!res.ok) throw new Error("API Error");
    return await res.json();
  } catch (e) {
    console.error("❌ fetchPagedJobs 오류:", e);
    return { page: 1, size, total: 0, total_pages: 1, jobs: [] };
  }
}