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
    
    // ✅ [핵심] 백엔드 데이터를 빠짐없이 전달해야 함!
    return {
      mode: data.mode || "public",
      jobs: data.jobs || [],
      trends: data.trends || [],           // 전체 트렌드 (혹시 몰라 유지)
      user_skills: data.user_skills || [], // 유저 스킬 목록
      
      // 👇 여기가 비어있어서 차트가 안 나왔던 것! 추가 완료!
      frontend_trends: data.frontend_trends || [], 
      backend_trends: data.backend_trends || [],
    };
  } catch (e) {
    console.error("❌ [fetchCareerDashboard] 오류:", e);
    // 에러 발생 시 빈 껍데기 반환 (화면 멈춤 방지)
    return { 
        mode: "public", jobs: [], trends: [], user_skills: [],
        frontend_trends: [], backend_trends: [] 
    };
  }
}

/**
 * 📚 AI 학습 추천
 * - 토큰을 실어 보내야 개인화된 추천을 받을 수 있습니다.
 */
export async function fetchLearningRecommend() {
  const token = localStorage.getItem("token"); // 토큰 가져오기

  try {
    const res = await fetch(`${BASE_URL}/learning`, {
      headers: { 
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }), // 토큰 탑승
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