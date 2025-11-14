// src/api/careerAPI.js

const BASE_URL = "http://127.0.0.1:8000/api/career";

/**
 * Career Dashboard 전용 API
 * 로그인 시 → "/dashboard"
 * 비로그인 시 → "/public"
 */
export async function fetchCareerDashboard(endpoint = "/public") {
  const token = localStorage.getItem("token");

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: token
        ? { Authorization: `Bearer ${token}` }
        : {},
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    console.log("📡 [fetchCareerDashboard] 응답:", data);

    // CareerDashboard.jsx가 요구하는 구조
    return {
      mode: data.mode || "public",
      jobs: data.results || [],
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



/**
 * 🔄 하위 호환용: 기존 fetchCareerData
 * (개별 키워드로 Job 검색용)
 */
export async function fetchCareerData(keyword = "") {
  const token = localStorage.getItem("token");

  const endpoint = token
    ? `${BASE_URL}/jobs?keyword=${encodeURIComponent(keyword)}`
    : `${BASE_URL}/public?keyword=${encodeURIComponent(keyword)}`;

  try {
    console.log("📡 [CareerAPI] 요청:", endpoint);

    const res = await fetch(endpoint, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    console.log("✅ [CareerAPI] 응답:", data);

    return data.results || [];
  } catch (error) {
    console.error("❌ [CareerAPI] Fetch Error:", error);
    return [];
  }
}
