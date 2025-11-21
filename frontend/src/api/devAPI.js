// src/api/devAPI.js
import axios from "axios";

const BASE = "http://127.0.0.1:8000/api/dev";

/** 📝 공통 헤더 (JWT 자동 포함) */
function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ----------------------------------------------------------------------
 *  🔓 1) Public Dev Dashboard  (로그인 X)
 * --------------------------------------------------------------------*/
export async function fetchPublicDev({ lang = "", since = "daily" } = {}) {
  try {
    const res = await axios.get(`${BASE}/public`, {
      params: { lang, since },
    });
    return res.data;
  } catch (err) {
    console.error("❌ Public Dev 오류:", err);
    return {
      github_trending: [],
      velog_trending: [],
      velog_tags: [],
    };
  }
}

/* ----------------------------------------------------------------------
 *  🔐 2) Personal Dev Dashboard (JWT 필요)
 * --------------------------------------------------------------------*/
export async function fetchPersonalDev() {
  try {
    const res = await axios.get(`${BASE}/personal`, {
      headers: getAuthHeaders(),
    });
    return res.data;
  } catch (err) {
    console.error("❌ Personal Dev 오류:", err);
    return {
      tech_stack: [],
      github_updates: [],
      velog_recommended: [],
    };
  }
}

/* ----------------------------------------------------------------------
 *  🔍 3) GitHub Trending 개별 요청
 * --------------------------------------------------------------------*/
export async function fetchGithubTrending({
  language = "",
  since = "daily",
} = {}) {
  try {
    const res = await axios.get(`${BASE}/github`, {
      params: { language, since },
    });
    return res.data.results || [];
  } catch (err) {
    console.error("❌ GitHub Trending 오류:", err);
    return [];
  }
}

/* ----------------------------------------------------------------------
 *  🔥 4) Velog: 특정 태그 인기글
 * --------------------------------------------------------------------*/
export async function fetchVelogByTag(tag) {
  try {
    const res = await axios.get(`${BASE}/velog/tag`, {
      params: { tag },
    });
    return res.data.results || [];
  } catch (err) {
    console.error("❌ Velog 태그 오류:", err);
    return [];
  }
}

/* ----------------------------------------------------------------------
 *  ⭐ 5) Velog: Trending 글 
 * --------------------------------------------------------------------*/
export async function fetchVelogTrending() {
  try {
    const res = await axios.get(`${BASE}/velog/trending`);
    return res.data.results || [];
  } catch (err) {
    console.error("❌ Velog Trending 오류:", err);
    return [];
  }
}

/* ----------------------------------------------------------------------
 *  📡 6) Velog RSS (ID 기반)
 * --------------------------------------------------------------------*/
export async function fetchVelogRSS(username) {
  try {
    const res = await axios.get(`${BASE}/velog/rss/${username}`);
    return res.data.results || [];
  } catch (err) {
    console.error("❌ Velog RSS 오류:", err);
    return [];
  }
}
