import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  LabelList,
} from "recharts";

// ✅ [수정 1] 백엔드에서 오는 카테고리 이름(Key)과 정확히 일치시켰습니다.
const COLORS = {
  "Error & Bug": "#EF4444",   // error
  "Environment": "#10B981",   // setup
  "Deployment": "#3B82F6",    // deploy
  "Performance": "#F59E0B",   // performance
  "Development": "#8B5CF6",   // api
  "Others": "#9CA3AF",        // none
};

export default function IssueInsightChart({ data }) {
  
  // ✅ [수정 2] 데이터 변환 로직 강화
  // 백엔드가 배열로 주든, 객체(딕셔너리)로 주든 찰떡같이 알아듣고 배열로 변환합니다.
  let list = [];

  if (data?.issues) {
    if (Array.isArray(data.issues)) {
      // 1. 이미 배열인 경우 (Backend가 수정될 경우 대비)
      list = data.issues;
    } else if (typeof data.issues === "object") {
      // 2. 객체(Dictionary)인 경우 -> 배열로 변환 ({Key: Value} -> [{category: Key, count: Value}])
      list = Object.entries(data.issues).map(([key, value]) => ({
        category: key,
        count: value,
      }));
    }
  }

  // ✅ [수정 3] count가 높은 순서대로 정렬 (차트가 예쁘게 나옴)
  list.sort((a, b) => b.count - a.count);

  // 리스트 → recharts용 데이터 구성
  const chartData = list.map((d) => ({
    category: d.category,
    count: d.count,
    // 키가 없으면 회색(#9CA3AF) 처리
    fill: COLORS[d.category] || "#9CA3AF",
  }));

  if (chartData.length === 0) {
    return <p className="text-gray-500 text-sm py-10 text-center">No issue insight data available.</p>;
  }

  return (
    <div className="w-full h-80 p-6 bg-white rounded-xl shadow-sm border">
      <ResponsiveContainer>
        <BarChart
          data={chartData}
          layout="vertical"
          barSize={28}
          margin={{ top: 0, right: 30, left: 20, bottom: 0 }} // 여백 조정
        >
          <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#e5e7eb" />

          <XAxis type="number" hide />

          <YAxis
            type="category"
            dataKey="category"
            width={120}
            tick={{ fill: "#374151", fontSize: 13, fontWeight: 500 }}
          />

          <Tooltip
            cursor={{ fill: "transparent" }}
            formatter={(value) => [`${value} posts`, "Count"]}
            contentStyle={{
              background: "white",
              borderRadius: "8px",
              border: "1px solid #ddd",
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            }}
          />

          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            <LabelList dataKey="count" position="right" fill="#6B7280" fontSize={12} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}