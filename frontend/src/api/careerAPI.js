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

    // 🔥 서버에서 내려오는 key 그대로 사용해야 함
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
