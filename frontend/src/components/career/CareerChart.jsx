// src/components/career/CareerChart.jsx
import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const COLORS = [
  "#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"
];

export default function CareerChart({ data }) {
  // 데이터 유효성 검사 강화
  const validData = Array.isArray(data) && data.length > 0;

  if (!validData) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm gap-2">
        <div className="w-8 h-8 border-4 border-gray-200 border-t-indigo-500 rounded-full animate-spin"></div>
        <p>데이터를 분석 중입니다...</p>
      </div>
    );
  }

  // 상위 6개만 추출 (값이 큰 순서)
  const top6Data = [...data]
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  // 전체 합계 (퍼센트 계산용)
  const total = top6Data.reduce((sum, item) => sum + item.value, 0);

  const chartData = top6Data.map((item) => ({
    ...item,
    valuePercent: total > 0 ? (item.value / total) * 100 : 0,
  }));

  return (
    <div className="w-full h-full flex flex-col items-center justify-center py-2">
      {/* 도넛 차트 영역 */}
      <div className="w-full h-[220px] relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={85}
              paddingAngle={4}
              cornerRadius={6}
              labelLine={false}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={COLORS[index % COLORS.length]} 
                  strokeWidth={0}
                />
              ))}
            </Pie>
            <Tooltip 
               contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}
               formatter={(value, name) => [`${value}건`, name]}
            />
          </PieChart>
        </ResponsiveContainer>
        
        {/* 중앙 텍스트 (총 공고 수) */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
            <span className="block text-2xl font-bold text-gray-800">{total}</span>
            <span className="text-xs text-gray-400">Total Jobs</span>
        </div>
      </div>

      {/* 커스텀 Legend (범례) */}
      <div className="w-full grid grid-cols-2 gap-y-2 gap-x-4 mt-6 px-6">
        {chartData.map((item, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
                <span className="text-gray-600 font-medium truncate max-w-[80px]" title={item.name}>
                    {item.name}
                </span>
            </div>
            <span className="text-gray-400 text-xs font-mono">
                {item.valuePercent.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}