import React, { useEffect, useState } from "react";
import { fetchHomeFeed } from "../api/homeAPI";
import NewsCard from "../components/NewsCard";

import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";

const COLORS = ["#2563EB", "#0EA5E9", "#38BDF8", "#4ADE80", "#F87171", "#A78BFA", "#FB923C"];

export default function Home() {
  const [feed, setFeed] = useState({
    news: [],
    charts: {
      category_ratio: [],
      keyword_ranking: [],
      weekly_trend: [],
    },
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadFeed = async () => {
      try {
        const data = await fetchHomeFeed();

        setFeed({
          news: data.news || [],
          charts: data.charts || {
            category_ratio: [],
            keyword_ranking: [],
            weekly_trend: [],
          },
        });
      } catch (err) {
        console.error(err);
        setError("데이터를 불러오는 중 오류가 발생했습니다.");
      } finally {
        setLoading(false);
      }
    };

    loadFeed();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-gray-400">
        ⏳ 최신 IT 기술 뉴스를 불러오는 중입니다...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen text-red-500">
        ❌ {error}
      </div>
    );
  }

  const { category_ratio, keyword_ranking, weekly_trend } = feed.charts;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800">
      <main className="max-w-6xl mx-auto px-8 py-10">

        {/* 뉴스 */}
        <section className="mt-6">
          <h2 className="text-2xl font-semibold mb-6">📰 최신 기술 뉴스</h2>

          {feed.news.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {feed.news.slice(0, 8).map((item, idx) => (
                <NewsCard key={idx} item={item} />
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-10">표시할 뉴스가 없습니다.</p>
          )}
        </section>

        {/* 트렌드 */}
        <section className="mt-20">
          <h2 className="text-2xl font-semibold mb-10">📊 IT 기술 트렌드 분석</h2>

          {/* 카테고리 비중 */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm mb-14">
            <h3 className="font-semibold text-lg mb-4">기술 카테고리 비중</h3>

            {category_ratio.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={category_ratio} dataKey="count" nameKey="category" outerRadius={110} label>
                      {category_ratio.map((_, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>

                <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {category_ratio.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                      <span className="text-sm">{item.category} — <strong>{item.count}</strong>건</span>
                    </div>
                  ))}
                </div>
              </>
            ) : <p className="text-gray-400 text-sm">데이터 없음</p>}
          </div>

          {/* 키워드 */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm mb-14">
            <h3 className="font-semibold text-lg mb-4">핫 키워드 TOP 20</h3>

            {keyword_ranking.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={keyword_ranking.slice(0, 10)}>
                    <XAxis dataKey="keyword" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="count" fill="#2563EB" />
                  </BarChart>
                </ResponsiveContainer>

                <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                  {keyword_ranking.slice(0, 12).map((item, idx) => (
                    <div key={idx} className="text-sm">
                      🔹 <strong>{item.keyword}</strong> — {item.count}회
                    </div>
                  ))}
                </div>
              </>
            ) : <p className="text-gray-400 text-sm">데이터 없음</p>}
          </div>

          {/* 주별 변화 */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <h3 className="font-semibold text-lg mb-4">주별 기술 트렌드 변화</h3>

            {weekly_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={weekly_trend}>
                  <XAxis dataKey="week" />
                  <YAxis />
                  <Tooltip />
                  <CartesianGrid strokeDasharray="3 3" />
                  <Line type="monotone" dataKey="count" stroke="#0EA5E9" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            ) : <p className="text-gray-400 text-sm">데이터 없음</p>}
          </div>

        </section>
      </main>
    </div>
  );
}
