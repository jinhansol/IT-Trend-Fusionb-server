import React from "react";

export default function AiInsightBox({ data = [] }) {
  return (
    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white p-5 rounded-2xl shadow-md">
      <h2 className="text-lg font-semibold mb-4">AI Insights</h2>
      <ul className="space-y-4">
        {data.map((item, i) => (
          <li key={i} className="border-b border-indigo-400/30 pb-3 last:border-0">
            <div className="flex justify-between items-center mb-1">
              <p className="font-medium">{item.title}</p>
              <span className="text-sm font-semibold text-green-300">
                {item.change}
              </span>
            </div>
            <p className="text-sm text-indigo-100">{item.desc}</p>
          </li>
        ))}
      </ul>
      <button className="mt-5 w-full bg-white/20 text-white py-2 rounded-lg text-sm font-semibold hover:bg-white/30 transition">
        View Detailed Analysis
      </button>
    </div>
  );
}
