import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#ef4444", // Red
  "#8b5cf6", // Violet
  "#ec4899", // Pink
  "#6366f1", // Indigo
  "#14b8a6", // Teal
];

export default function TrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 bg-gray-50 rounded-lg">
        데이터를 불러오는 중입니다...
      </div>
    );
  }

  // 1. 데이터 키 추출 (week 대신 date를 제외하고 추출)
  const allKeys = new Set();
  data.forEach((item) => {
    Object.keys(item).forEach((key) => {
      // 백엔드에서 'date'를 보내주므로 이를 제외한 나머지가 카테고리(AI, Backend 등)
      if (key !== "date" && key !== "week") { 
        allKeys.add(key);
      }
    });
  });
  const categories = Array.from(allKeys);

  // 날짜 포맷팅 함수 (2025-11-27 -> 11/27)
  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      const date = new Date(dateStr);
      return `${date.getMonth() + 1}/${date.getDate()}`;
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="w-full h-[350px] p-4 bg-white rounded-xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-bold text-gray-800 mb-6 text-center">
        📉 일별 기술 트렌드 변화
      </h3>

      <ResponsiveContainer width="100%" height="90%">
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
          
          {/* ✅ [핵심 수정] X축이 이제 'date'를 바라봅니다 */}
          <XAxis 
            dataKey="date" 
            tickFormatter={formatDate}
            tick={{ fill: '#6b7280', fontSize: 12 }} 
            axisLine={{ stroke: '#e5e7eb' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          
          <YAxis 
            tick={{ fill: '#6b7280', fontSize: 12 }} 
            axisLine={false}
            tickLine={false}
          />
          
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
            labelFormatter={(label) => `📅 ${label}`}
          />
          <Legend wrapperStyle={{ paddingTop: '15px' }} />

          {categories.map((cat, index) => (
            <Line
              key={cat}
              type="monotone"
              dataKey={cat}
              name={cat.toUpperCase()}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 2 }} 
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}