// src/api/githubAPI.js
const API_BASE = "http://127.0.0.1:8000/api/dev";

/** 언어별 통계 */
export async function fetchLangStats() {
  try {
    const res = await fetch(`${API_BASE}/lang-stats`);
    return await res.json();
  } catch (err) {
    console.error("❌ fetchLangStats 오류:", err);
    return { languages: [] };
  }
}

/** 언어별 성장 추세 */
export async function fetchLangGrowth() {
  try {
    const res = await fetch(`${API_BASE}/growth`);
    return await res.json();
  } catch (err) {
    console.error("❌ fetchLangGrowth 오류:", err);
    return { growth: [] };
  }
}

/** 인기 오픈소스 목록 */
export async function fetchRepos() {
  try {
    const res = await fetch(`${API_BASE}/repos`);
    return await res.json();
  } catch (err) {
    console.error("❌ fetchRepos 오류:", err);
    return { repos: [] };
  }
}

/** AI 인사이트 */
export async function fetchInsights() {
  try {
    const res = await fetch(`${API_BASE}/insights`);
    return await res.json();
  } catch (err) {
    console.error("❌ fetchInsights 오류:", err);
    return { insights: [] };
  }
}
