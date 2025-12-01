// src/components/TopicInsightChart.jsx
import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const COLORS = [
  "#6366F1", "#06B6D4", "#10B981",
  "#F97316", "#EF4444", "#8B5CF6",
  "#14B8A6",
];

export default function TopicInsightChart({ data }) {

  // 백엔드 구조: { clusters: [...] }
  const clusters = data?.clusters || [];

  // 데이터가 없을 때 표시
  if (!Array.isArray(clusters) || clusters.length === 0) {
    return (
        <div className="flex h-full items-center justify-center text-gray-400 text-sm">
            No topic insight available.
        </div>
    );
  }

  // 총 합계 계산 (차트 중앙에 표시용)
  const totalPosts = clusters.reduce((acc, curr) => acc + curr.count, 0);

  return (
    // 전체 컨테이너: 높이를 고정하고 Flex로 좌우 배치
    <div className="w-full h-full flex flex-col sm:flex-row items-center gap-6">

      {/* 🔵 왼쪽: 도넛 차트 */}
      <div className="w-full sm:w-1/2 h-[240px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={clusters}
              cx="50%"
              cy="50%"
              innerRadius={60}  // 안쪽 구멍 크기
              outerRadius={80}  // 바깥쪽 크기
              paddingAngle={4}
              dataKey="count"
              stroke="none"     // 테두리 선 제거 (더 깔끔함)
            >
              {clusters.map((entry, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => `${value} posts`}
              contentStyle={{
                background: "white",
                borderRadius: "8px",
                border: "none",
                boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                fontSize: "14px",
                fontWeight: "bold"
              }}
              itemStyle={{ color: "#374151" }}
            />
          </PieChart>
        </ResponsiveContainer>
        
        {/* 도넛 차트 중앙에 Total 표시 */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
            <span className="block text-2xl font-extrabold text-gray-800">{totalPosts}</span>
            <span className="text-xs text-gray-400 uppercase font-semibold">Total</span>
        </div>
      </div>

      {/* 🔵 오른쪽: 토픽 리스트 (스크롤 적용) */}
      <div className="w-full sm:w-1/2 flex flex-col gap-2 h-[240px] overflow-y-auto pr-2 custom-scrollbar">
        {clusters.map((t, idx) => (
          <div
            key={idx}
            className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50 transition-colors"
          >
            {/* 왼쪽: 색상 점 + 이름 */}
            <div className="flex items-center gap-3 overflow-hidden">
              <span
                className="w-3 h-3 rounded-full flex-shrink-0 shadow-sm"
                style={{ backgroundColor: COLORS[idx % COLORS.length] }}
              />
              <span className="text-sm font-medium text-gray-700 truncate" title={t.topic}>
                {t.topic}
              </span>
            </div>

            {/* 오른쪽: 개수 */}
            <span className="text-sm font-bold text-gray-900 flex-shrink-0">
              {t.count}
            </span>
          </div>
        ))}
      </div>

    </div>
  );
}