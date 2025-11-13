// src/api/careerAPI.js

export async function fetchCareerData(keyword = "") {
  const token = localStorage.getItem("token");
  const isLoggedIn = !!token;

  const endpoint = isLoggedIn
    ? `http://127.0.0.1:8000/api/career/jobs?keyword=${encodeURIComponent(keyword)}`
    : `http://127.0.0.1:8000/api/career/public?keyword=${encodeURIComponent(keyword)}`;

  try {
    console.log("📡 [CareerAPI] 요청:", endpoint);

    const res = await fetch(endpoint, {
      headers: isLoggedIn ? { Authorization: `Bearer ${token}` } : {}
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    console.log("✅ [CareerAPI] 응답:", data);

    return data.results || [];

  } catch (error) {
    console.error("[CareerAPI] Fetch Error:", error);
    return [];
  }
}
