// ✅ Home Feed API — 뉴스 + GitHub + 인사이트 통합
export async function fetchHomeFeed(keyword = "AI 트렌드") {
  try {
    const res = await fetch(
      `http://127.0.0.1:8000/api/home/feed?keyword=${encodeURIComponent(
        keyword
      )}`
    );

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    return res.json();
  } catch (err) {
    console.error("❌ [homeAPI] Error:", err);
    return { news: [], insight: "", github_chart: [], top_repos: [] };
  }
}
