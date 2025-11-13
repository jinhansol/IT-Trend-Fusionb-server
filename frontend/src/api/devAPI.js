// src/api/devAPI.js
import axios from "axios";

const BASE = "http://127.0.0.1:8000/api/dev";

function getHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export const fetchDevTrends = async (keyword = "") => {
  const token = localStorage.getItem("token");
  const isLoggedIn = !!token;

  const endpoint = isLoggedIn
    ? `${BASE}/trend?keyword=${encodeURIComponent(keyword)}`
    : `${BASE}/public?keyword=${encodeURIComponent(keyword)}`;

  try {
    console.log("📡 [DevAPI] 요청:", endpoint);

    const res = await axios.get(endpoint, { headers: getHeaders() });
    console.log("✅ [DevAPI] 응답:", res.data);

    return res.data.results || [];

  } catch (err) {
    console.error("❌ [DevAPI] Error:", err);
    return [];
  }
};
