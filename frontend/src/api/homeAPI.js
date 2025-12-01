// src/api/homeAPI.js
import axios from "axios";

// Axios 인스턴스 (공통 설정)
const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
});

// 토큰 자동 포함 (나중에 Personal 기능용)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")?.trim();
  if (token && token !== "null" && token !== "undefined") {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * 🏠 홈 화면 전체 데이터 가져오기 (News + Charts)
 * - 로그인 여부는 백엔드에서 판단하거나, 프론트에서 분기 가능
 * - 현재는 Public 데이터 위주
 */
export async function fetchHomeFeed(keyword = null) {
  try {
    // 1. 키워드가 있으면 검색, 없으면 일반 홈 피드
    const endpoint = keyword 
      ? `/home/search?keyword=${encodeURIComponent(keyword)}` 
      : "/home/public"; 
      // 나중에 Personal 생기면 여기서 조건문으로 '/home/personal' 호출하면 됨

    console.log("📡 [HomeAPI] 요청:", endpoint);
    const res = await api.get(endpoint);

    console.log("✅ [HomeAPI] 응답:", res.data);

    return {
      news: res.data.news || [],
      charts: res.data.charts || {
        category_ratio: [],
        keyword_ranking: [],
        weekly_trend: [],
      },
    };
  } catch (err) {
    console.error("❌ [HomeAPI] Feed Error:", err);
    // 에러 나도 화면이 안 죽게 빈 데이터 반환
    return {
      news: [],
      charts: { category_ratio: [], keyword_ranking: [], weekly_trend: [] },
    };
  }
}

/**
 * 📰 뉴스만 따로 가져오기 (필요 시 사용)
 */
export async function fetchLatestNews() {
  try {
    const res = await api.get("/news/latest");
    return res.data;
  } catch (err) {
    console.error("❌ [HomeAPI] News Error:", err);
    return [];
  }
}

/**
 * 📊 트렌드 요약 가져오기 (필요 시 사용)
 */
export async function fetchTrendSummary(keyword = "IT") {
  try {
    const res = await api.get("/trend/recommend", { params: { keyword } });
    return res.data;
  } catch (err) {
    console.error("❌ [HomeAPI] Trend Error:", err);
    return { message: "데이터를 불러오는 중 오류가 발생했습니다." };
  }
}