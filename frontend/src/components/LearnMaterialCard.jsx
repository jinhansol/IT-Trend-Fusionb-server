// src/components/LearnMaterialCard.jsx
import React from "react";

export default function LearnMaterialCard({ item }) {
  return (
    <div className="border rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition">
      
      {/* 태그 */}
      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">
        {item.tag}
      </span>

      {/* 제목 */}
      <h3 className="font-semibold mt-2 text-gray-800">{item.title}</h3>

      {/* 요약 설명 2~3줄 */}
      {item.desc && (
        <p className="text-sm text-gray-600 mt-2 line-clamp-3">
          {item.desc}
        </p>
      )}

      {/* 출처 */}
      {item.source && (
        <p className="text-sm text-gray-500 mt-1">{item.source}</p>
      )}

      <a
        href={item.link || "#"}
        className="text-blue-600 text-sm font-medium hover:underline block mt-3"
      >
        Learn More →
      </a>
    </div>
  );
}
