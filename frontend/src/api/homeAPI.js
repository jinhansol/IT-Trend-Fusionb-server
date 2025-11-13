export async function fetchHomeFeed(keyword = null) {
  const token = localStorage.getItem("token");
  const isLoggedIn = !!token;

  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : "";

  const endpoint = isLoggedIn
    ? `http://127.0.0.1:8000/api/home/feed${query}`
    : `http://127.0.0.1:8000/api/home/public${query}`;   // 🔥 여기 수정!

  try {
    console.log("📡 [HomeAPI] 요청:", endpoint);

    const res = await fetch(endpoint, {
      headers: isLoggedIn ? { Authorization: `Bearer ${token}` } : {},
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    console.log("✅ [HomeAPI] 응답:", data);
    return data;

  } catch (err) {
    console.error("❌ [HomeAPI] Error:", err);
    return { insight: "", results: [], github_chart: [], top_repos: [] };
  }
}
