// src/components/DevCard.jsx
import React from "react";

export default function DevCard({ item }) {
  return (
    <div className="border bg-white rounded-xl p-5 shadow-sm hover:shadow-md transition">

      {/* 제목 */}
      <a
        href={item.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-lg font-semibold text-emerald-700 hover:underline"
      >
        {item.title}
      </a>

      {/* 작성자 */}
      {item.author && (
        <p className="text-sm text-gray-600 mt-1">by {item.author}</p>
      )}

      {/* 설명(summary) */}
      {item.summary && (
        <p className="text-gray-700 text-sm mt-3 line-clamp-5">
          {item.summary}
        </p>
      )}

      {/* 태그 */}
      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-4">
          {item.tags.map((tag, index) => (
            <span
              key={index}
              className="text-xs px-2 py-1 bg-gray-100 border border-gray-300 rounded-md text-gray-700"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* 날짜 */}
      {item.published_at && (
        <p className="text-xs text-gray-500 mt-4">
          {new Date(item.published_at).toLocaleDateString()}
        </p>
      )}

    </div>
  );
}
