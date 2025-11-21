// src/components/CareerChart.jsx
import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";

const COLORS = ["#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444"];

export default function CareerChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center text-gray-500 py-10">
        기술 데이터 없음
      </div>
    );
  }

  // 🔢 퍼센트 계산
  const total = data.reduce((sum, item) => sum + item.count, 0);

  const chartData = data.map((item, index) => ({
    name: item.skill,
    value: item.count,
    percent: ((item.count / total) * 100).toFixed(1),
  }));

  return (
    <div className="flex flex-col items-center justify-center w-full">
      
      {/* 🎯 도넛 차트 */}
      <div style={{ width: "340px", height: "340px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={90}
              outerRadius={130}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* 🟦 커스텀 레전드 (기술명 + 퍼센트) */}
      <div className="flex flex-wrap justify-center gap-4 mt-4 text-sm text-gray-700">
        {chartData.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: COLORS[index % COLORS.length] }}
            ></span>
            <span>
              {item.name} ({item.percent}%)
            </span>
          </div>
        ))}
      </div>

    </div>
  );
}
