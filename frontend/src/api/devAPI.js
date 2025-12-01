// src/api/devAPI.js
import axios from "axios";

const API_BASE = "http://localhost:8000/api/dev";

// Axios 인스턴스
const api = axios.create({
  baseURL: API_BASE,
});

// 토큰 자동 포함
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token")?.trim();
  if (token && token !== "null" && token !== "undefined") {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// -----------------------------
// 📌 Public Dev Feed
// -----------------------------
export async function fetchDevPublic() {
  try {
    const res = await api.get("/public");
    return res.data;
  } catch (err) {
    console.error("❌ fetchDevPublic error:", err);
    throw err;
  }
}

// -----------------------------
// 📌 Personal Dev Feed
// -----------------------------
export async function fetchDevPersonal() {
  try {
    const res = await api.get("/personal");
    return res.data;
  } catch (err) {
    console.error("❌ fetchDevPersonal error:", err);
    throw err;
  }
}

// -----------------------------
// 📌 Source별 페이지네이션
// /source/okky?page=1&size=10
// -----------------------------
export async function fetchDevSource(source, page = 1, size = 10) {
  try {
    const res = await api.get(`/source/${source}?page=${page}&size=${size}`);
    return res.data;
  } catch (err) {
    console.error("❌ fetchDevSource error:", err);
    throw err;
  }
}

// -----------------------------
// 📌 전체 태그 수집
// -----------------------------
export async function fetchDevTags() {
  try {
    const res = await api.get("/tags");
    return res.data;
  } catch (err) {
    console.error("❌ fetchDevTags error:", err);
    throw err;
  }
}

/* ================================================
 🔥 NEW — Topic Insight (Topic Cluster)
================================================= */
export async function fetchDevTopicInsight() {
  try {
    const res = await api.get("/insight/topic");
    return res.data;
  } catch (err) {
    console.error("❌ fetchDevTopicInsight error:", err);
    throw err;
  }
}

/* ================================================
 🔥 NEW — Issue Insight (Error/Performance/Deploy 통계)
================================================= */
export async function fetchDevIssueInsight() {
  try {
    const res = await api.get("/insight/issues");
    return res.data;
  } catch (err) {
    console.error("❌ fetchDevIssueInsight error:", err);
    throw err;
  }
}
