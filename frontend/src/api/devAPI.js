// src/api/devAPI.js
import axios from "axios";

const API_BASE = "http://localhost:8000/api/dev";

// Axios 전용 인스턴스
const api = axios.create({
  baseURL: API_BASE,
});

// 요청마다 자동 토큰 포함
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
// 📌 태그 필터
// -----------------------------
export async function fetchFilteredDevFeed(tags) {
  try {
    const query = tags.length ? `?tags=${tags.join(",")}` : "";
    const res = await api.get(`/filter${query}`);
    return res.data;
  } catch (err) {
    console.error("❌ fetchFilteredDevFeed error:", err);
    throw err;
  }
}

// -----------------------------
// 📌 view_count 증가
// -----------------------------
export async function increaseViewCount(source, postId) {
  try {
    const res = await api.post("/view", {
      source,
      post_id: postId,
    });
    return res.data;
  } catch (err) {
    console.error("❌ increaseViewCount error:", err);
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
