import React, { useEffect, useState } from "react";
import { fetchHomeFeed } from "../api/homeAPI";
import HeaderNav from "../components/HeaderNav";
import NewsCard from "../components/NewsCard";
import GithubChart from "../components/GithubChart";

export default function Home() {
  const [feed, setFeed] = useState({
    insight: "",
    news: [],
    github_chart: [],
    top_repos: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFeed = async () => {
      try {
        const data = await fetchHomeFeed();
        console.log("✅ [Home] API 응답:", data);

        // 안전하게 데이터 구조 보정
        setFeed({
          insight: data?.insight || "이번 주 AI 트렌드를 불러오는 중입니다.",
          news: Array.isArray(data?.news) ? data.news : [],
          github_chart: Array.isArray(data?.github_chart)
            ? data.github_chart
            : [],
          top_repos: Array.isArray(data?.top_repos) ? data.top_repos : [],
        });
      } catch (err) {
        console.error("❌ 홈 피드 로드 실패:", err);
        setFeed({
          insight: "데이터를 불러오는 중 오류가 발생했습니다.",
          news: [],
          github_chart: [],
          top_repos: [],
        });
      } finally {
        setLoading(false);
      }
    };
    loadFeed();
  }, []);

  if (loading)
    return <div className="text-center py-20 text-gray-400">⏳ Loading...</div>;

  if (!feed)
    return (
      <div className="text-center py-20 text-red-500">
        ❌ No data available
      </div>
    );

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      <main className="max-w-6xl mx-auto px-8 py-10">
        {/* 🟢 AI Weekly Insight */}
        <div className="bg-emerald-100 border border-emerald-200 rounded-xl p-5 mb-12 shadow-sm">
          <h2 className="text-emerald-700 font-semibold text-lg mb-1">
            💡 AI 주간 인사이트
          </h2>
          <p className="text-gray-700 text-base leading-relaxed">
            {feed.insight ||
              "이번 주 AI 기술 트렌드 요약을 불러오는 중입니다."}
          </p>
        </div>

        {/* 📰 최신 기술 뉴스 */}
        <section className="mt-10">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            📰 최신 기술 뉴스
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {feed.news && feed.news.length > 0 ? (
              feed.news.slice(0, 10).map((item, idx) => (
                <NewsCard key={idx} item={item} />
              ))
            ) : (
              <p className="col-span-4 text-gray-500 text-center">
                표시할 뉴스가 없습니다.
              </p>
            )}
          </div>
        </section>

        {/* 💻 GitHub Trends */}
        <section className="mt-16">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            💻 GitHub Trends
          </h2>

          <div className="grid grid-cols-[1.4fr,0.6fr] gap-8">
            {/* 왼쪽: 언어별 성장 그래프 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 h-[400px]">
              <h3 className="text-base font-semibold text-gray-800 mb-4">
                📊 언어별 성장 비율
              </h3>
              {feed.github_chart && feed.github_chart.length > 0 ? (
                <GithubChart data={feed.github_chart} />
              ) : (
                <p className="text-gray-400 text-sm text-center pt-16">
                  데이터를 불러오는 중입니다...
                </p>
              )}
            </div>

            {/* 오른쪽: 인기 저장소 요약 */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 h-[400px] overflow-y-auto">
              <h3 className="text-base font-semibold text-gray-800 mb-4">
                ⭐ 인기 GitHub 저장소 요약
              </h3>
              <ul className="space-y-5">
                {feed.top_repos && feed.top_repos.length > 0 ? (
                  feed.top_repos.map((repo, idx) => (
                    <li
                      key={idx}
                      className="border-l-4 border-indigo-500 pl-3 hover:bg-indigo-50 rounded-sm transition-all"
                    >
                      <a
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-indigo-600 hover:underline"
                      >
                        {repo.name}
                      </a>
                      <p className="text-xs text-gray-400 mt-1">
                        {repo.tag || "기타"}
                      </p>
                      <p className="text-sm text-gray-700 mt-1 leading-snug line-clamp-3">
                        {repo.description || "요약 정보 없음"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1 italic">
                        💬 {repo.trend_summary || "트렌드 정보 없음"}
                      </p>
                    </li>
                  ))
                ) : (
                  <p className="text-gray-500 text-sm">데이터가 없습니다.</p>
                )}
              </ul>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
