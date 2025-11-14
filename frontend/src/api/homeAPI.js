export async function fetchHomeFeed(keyword = null) {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : "";

  const endpoint = `http://127.0.0.1:8000/api/home/public${query}`;

  try {
    console.log("📡 [HomeAPI] 요청:", endpoint);

    const res = await fetch(endpoint);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    console.log("✅ [HomeAPI] 응답:", data);

    return {
      news: data.news || [],
      charts: data.charts || {
        category_ratio: [],
        keyword_ranking: [],
        weekly_trend: [],
      },
    };

  } catch (err) {
    console.error("❌ [HomeAPI] Error:", err);
    return {
      news: [],
      charts: {
        category_ratio: [],
        keyword_ranking: [],
        weekly_trend: [],
      },
    };
  }
}
