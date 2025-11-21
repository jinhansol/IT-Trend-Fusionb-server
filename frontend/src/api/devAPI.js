// src/api/devAPI.js
import axios from "axios";

const BASE = "http://127.0.0.1:8000/api/dev";

/* JWT 포함 헤더 */
function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/* ---------------------------------------------------------------------
 * 🔥 1) 통합 DevFeed — Public / Personal 자동 분기
 * -------------------------------------------------------------------*/
export async function fetchDevFeed() {
  try {
    const res = await axios.get(`${BASE}/`, {
      headers: getAuthHeaders(),
    });
    return res.data;
  } catch (err) {
    console.error("❌ DevFeed 오류:", err);
    return {
      mode: "public",
      velog_trending: [],
      velog_tags: [],
      github_trending: [],
      velog_recommended: [],
      velog_interest_match: [],
      github_recommended: [],
    };
  }
}

/* ---------------------------------------------------------------------
 *  (선택) GitHub Trending — 디버그용
 * -------------------------------------------------------------------*/
export async function fetchGithubTrending({
  language = "",
  since = "daily",
} = {}) {
  try {
    const res = await axios.get(`${BASE}/github`, {
      params: { language, since },
      headers: getAuthHeaders(),
    });
    return res.data.results || [];
  } catch (err) {
    console.error("❌ GitHub Trending 오류:", err);
    return [];
  }
}

/* Velog Tag 글 */
export async function fetchVelogByTag(tag) {
  try {
    const res = await axios.get(`${BASE}/velog/tag`, {
      params: { tag },
      headers: getAuthHeaders(),
    });
    return res.data.results || [];
  } catch (err) {
    console.error("❌ Velog Tag 오류:", err);
    return [];
  }
}

/* Velog Trending */
export async function fetchVelogTrending() {
  try {
    const res = await axios.get(`${BASE}/velog/trending`, {
      headers: getAuthHeaders(),
    });
    return res.data.results || [];
  } catch (err) {
    console.error("❌ Velog Trending 오류:", err);
    return [];
  }
}
