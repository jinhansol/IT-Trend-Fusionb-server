// src/api/careerAPI.js

const BASE_URL = "http://127.0.0.1:8000/api/career";

/**
 * Career Dashboard API
 */
export async function fetchCareerDashboard(endpoint = "/public") {
  const token = localStorage.getItem("token");

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    console.log("📡 [fetchCareerDashboard] 응답:", data);

    return {
      mode: data.mode || "public",
      jobs: data.jobs || [],
      trends: data.trends || [],
      user_skills: data.user_skills || [],
    };
  } catch (e) {
    console.error("❌ [fetchCareerDashboard] 오류:", e);
    return {
      mode: "public",
      jobs: [],
      trends: [],
      user_skills: [],
    };
  }
}

// ⭐ 신규: AI 학습 추천 API
export async function fetchLearningRecommend() {
  try {
    const res = await fetch(`${BASE_URL}/learning`);
    if (!res.ok) throw new Error("API Error");

    const data = await res.json();
    return data.learning || [];
  } catch (e) {
    console.error("❌ fetchLearningRecommend 오류:", e);
    return [];
  }
}

// ⭐ 신규: 페이징된 채용 공고 API
export async function fetchPagedJobs(page = 1, size = 6) {
  try {
    const res = await fetch(
      `${BASE_URL}/jobs?page=${page}&size=${size}`
    );

    if (!res.ok) throw new Error("API Error");

    return await res.json();
  } catch (e) {
    console.error("❌ fetchPagedJobs 오류:", e);
    return { page: 1, size, total: 0, total_pages: 1, jobs: [] };
  }
}
