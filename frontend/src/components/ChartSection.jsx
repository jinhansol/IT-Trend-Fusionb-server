// components/ChartSection.jsx

import React from "react";
import {
  PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis,
  LineChart, Line, CartesianGrid,
  ResponsiveContainer,
} from "recharts";

const COLORS = [
  "#4F46E5", "#06B6D4", "#10B981",
  "#F59E0B", "#EF4444", "#6366F1"
];

export default function ChartSection({ charts }) {
  if (!charts) return null;

  const { category_ratio, keyword_ranking, weekly_trend } = charts;

  return (
    <section className="mt-20">
      <h2 className="text-2xl font-semibold mb-8">
        📊 IT 기술 트렌드 분석
      </h2>

      {/* 1️⃣ 기술 카테고리 비중 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-12">
        <h3 className="font-semibold text-lg mb-4">기술 카테고리 비중</h3>

        {category_ratio?.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={category_ratio}
                dataKey="count"
                nameKey="category"
                outerRadius={120}
                label
              >
                {category_ratio.map((_, idx) => (
                  <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400">데이터가 없습니다.</p>
        )}
      </div>

      {/* 2️⃣ 키워드 TOP 20 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm mb-12">
        <h3 className="font-semibold text-lg mb-4">핫 키워드 TOP 20</h3>

        {keyword_ranking?.length > 0 ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={keyword_ranking}>
              <XAxis dataKey="keyword" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#4F46E5" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400">데이터가 없습니다.</p>
        )}
      </div>

      {/* 3️⃣ 주별 트렌드 변화 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h3 className="font-semibold text-lg mb-4">주별 기술 트렌드 변화</h3>

        {weekly_trend?.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={weekly_trend}>
              <XAxis dataKey="week" />
              <YAxis />
              <Tooltip />
              <CartesianGrid strokeDasharray="3 3" />
              <Line type="monotone" dataKey="count" stroke="#06B6D4" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400">데이터가 없습니다.</p>
        )}
      </div>
    </section>
  );
}
