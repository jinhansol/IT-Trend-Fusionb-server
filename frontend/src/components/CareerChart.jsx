// src/components/CareerChart.jsx
import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
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

  const chartData = data.map((item, index) => ({
    name: item.skill,
    value: item.count,
  }));

  return (
    <div className="flex flex-col items-center justify-center w-full">
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

            <Legend verticalAlign="bottom" height={36} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
