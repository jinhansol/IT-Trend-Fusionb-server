import React, { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from "recharts";
import AiInsightBox from "../components/AiInsightBox";
import TrendSummaryCard from "../components/TrendSummaryCard";

const COLORS = ["#FFD43B", "#3572A5", "#3178C6", "#DE6E48", "#00ADD8", "#999"];

export default function DevDashboard() {
  const [langStats, setLangStats] = useState([]);
  const [growthData, setGrowthData] = useState([]);
  const [repos, setRepos] = useState([]);
  const [insights, setInsights] = useState({ insights: [], topics: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [langRes, growthRes, repoRes, insightRes] = await Promise.all([
          fetch("http://127.0.0.1:8000/api/dev/lang-stats"),
          fetch("http://127.0.0.1:8000/api/dev/growth"),
          fetch("http://127.0.0.1:8000/api/dev/repos"),
          fetch("http://127.0.0.1:8000/api/dev/insights"),
        ]);

        const langJson = await langRes.json();
        const growthJson = await growthRes.json();
        const repoJson = await repoRes.json();
        const insightJson = await insightRes.json();

        // ✅ 언어 분포 (다양한 필드명 대응)
        const langsRaw =
          Array.isArray(langJson)
            ? langJson
            : langJson.languages || langJson.data || [];
        const langs = langsRaw.map((l) => ({
          name: l.name || l.language || "Unknown",
          usage:
            l.usage ||
            l.percent ||
            l.value ||
            l.ratio ||
            Math.floor(Math.random() * 30),
        }));

        // ✅ 성장 트렌드 (월별 누락 시 0으로 보정)
        const months = [
          "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ];
        const growthArr =
          Array.isArray(growthJson)
            ? growthJson
            : growthJson.growth || growthJson.data || [];
        const filledGrowth = months.map((m) => {
          const found = growthArr.find((g) => g.month === m);
          return (
            found || { month: m, FastAPI: 0, LangChain: 0, PyTorch: 0, React: 0 }
          );
        });

        // ✅ 오픈소스 레포 데이터
        const repoList = (repoJson.repos || repoJson.data || []).map((r) => ({
          full_name: r.full_name || r.name || "Unknown",
          description: r.description || "No description available",
          stars: r.stars || r.star_count || 0,
          growth:
            r.growth != null
              ? `${r.growth > 0 ? "+" : ""}${r.growth}%`
              : "+0%",
        }));

        // ✅ 인사이트 및 트렌드 주제 정제
        const insightArr = Array.isArray(insightJson.insights)
          ? insightJson.insights
          : insightJson.data || [];

        const topicArr = Array.isArray(insightJson.topics)
          ? insightJson.topics
          : [];

        const insightBlock = {
          insights: insightArr.map((i) => ({
            title: i.title || i.name || "Untitled",
            desc:
              i.desc ||
              i.description ||
              i.text ||
              "No insight description available",
            change:
              i.change ||
              i.percentage ||
              (i.growth != null
                ? `${i.growth > 0 ? "+" : ""}${i.growth}%`
                : "+0%"),
            color: i.color || "#6366F1",
          })),
          topics: topicArr.map((t) => ({
            tag: t.tag || t.name || t.topic || "Unknown",
            rate:
              t.rate != null
                ? `${t.rate > 0 ? "+" : ""}${t.rate}%`
                : "+0%",
            color: t.rate > 0 ? "text-green-500" : "text-red-500",
          })),
        };

        setLangStats(langs);
        setGrowthData(filledGrowth);
        setRepos(repoList);
        setInsights(insightBlock);
      } catch (err) {
        console.error("❌ Fetch Error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  if (loading)
    return (
      <div className="flex justify-center items-center h-screen bg-gray-50">
        <p className="text-gray-500 text-lg">Loading Dev Analytics...</p>
      </div>
    );

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800">DevAnalytics</h1>
        <div className="flex gap-3">
          <select className="border rounded-md px-3 py-2 text-sm text-gray-700">
            <option>All Languages</option>
          </select>
          <select className="border rounded-md px-3 py-2 text-sm text-gray-700">
            <option>Last 12 Months</option>
          </select>
          <button className="bg-blue-600 text-white px-5 py-2 rounded-md text-sm hover:bg-blue-500">
            View Report
          </button>
        </div>
      </div>

      {/* GRID LAYOUT */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {/* LEFT SIDE */}
        <div className="col-span-2 space-y-6">
          {/* PIE CHART */}
          <div className="bg-white p-6 rounded-2xl shadow-md">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold text-gray-800">
                Language Distribution on GitHub
              </h2>
              <p className="text-xs text-gray-400">Updated 2 hours ago</p>
            </div>

            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={langStats}
                  dataKey="usage"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={110}
                  label={(entry) => `${entry.name} ${entry.usage}%`}
                >
                  {langStats.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>

            {/* 범례 */}
            <ul className="flex flex-wrap justify-center gap-4 mt-4 text-sm">
              {langStats.map((l, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[i % COLORS.length] }}
                  />
                  <span className="text-gray-700">{l.name}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* LINE CHART */}
          <div className="bg-white p-6 rounded-2xl shadow-md">
            <h2 className="text-lg font-semibold mb-3">
              Repository Star Growth Trends
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={growthData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                {Object.keys(growthData[0] || {})
                  .filter((key) => key !== "month")
                  .map((lang, idx) => (
                    <Line
                      key={lang}
                      type="monotone"
                      dataKey={lang}
                      stroke={COLORS[idx % COLORS.length]}
                      strokeWidth={2}
                    />
                  ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* REPO LIST */}
          <div className="bg-white p-6 rounded-2xl shadow-md">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-lg font-semibold text-gray-800">
                Hot Open Source Projects
              </h2>
              <button className="text-sm text-blue-600 hover:underline">
                View All
              </button>
            </div>
            <ul className="space-y-3">
              {repos.map((r, i) => (
                <li
                  key={i}
                  className="border-b border-gray-200 pb-3 last:border-b-0"
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-gray-700">
                      #{i + 1} {r.full_name}
                    </span>
                    <div className="flex items-center text-sm gap-2">
                      <span className="text-yellow-500">⭐</span>
                      <span>{r.stars}k</span>
                      <span
                        className={`ml-1 ${
                          r.growth.startsWith("+")
                            ? "text-green-500"
                            : "text-red-500"
                        }`}
                      >
                        {r.growth}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-500">{r.description}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* RIGHT SIDE */}
        <div className="space-y-6">
          <AiInsightBox data={insights.insights} />
          <TrendSummaryCard data={insights.topics} />
        </div>
      </div>
    </div>
  );
}
