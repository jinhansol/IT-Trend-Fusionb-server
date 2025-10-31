import React from "react";

export default function TrendSummaryCard({ data = [] }) {
  return (
    <div className="bg-white p-5 rounded-2xl shadow-md">
      <h2 className="text-lg font-semibold mb-4 text-gray-800">
        Trending Topics
      </h2>
      <ul className="space-y-2">
        {data.map((t, i) => (
          <li
            key={i}
            className="flex justify-between items-center text-sm border-b border-gray-200 pb-2 last:border-0"
          >
            <span className="font-medium text-gray-700">#{t.tag}</span>
            <span className={t.color}>{t.rate}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
