import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
} from "recharts";

const data = [
  { name: "React", value: 35 },
  { name: "TypeScript", value: 25 },
  { name: "Node.js", value: 20 },
];

const COLORS = ["#4F46E5", "#06B6D4", "#10B981"]; // React, TypeScript, Node.js

export default function CareerChart() {
  return (
    <div className="flex flex-col items-center justify-center">

      {/* 도넛형 차트 컨테이너 */}
      <div
        style={{
          width: "340px",   // 고정 너비
          height: "340px",  // 동일 높이 → 완벽한 원
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={90}
              outerRadius={130}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index]} />
              ))}
            </Pie>
            <Legend
              verticalAlign="bottom"
              align="center"
              iconType="circle"
              iconSize={10}
              wrapperStyle={{ fontSize: "13px", paddingTop: "10px" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <p className="text-sm text-gray-600 mt-3">
        React 35% · TypeScript 25% · Node.js 20%
      </p>
    </div>
  );
}
