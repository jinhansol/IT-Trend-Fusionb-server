import React from "react";

export default function NewsCard({ item }) {
  if (!item) return null;

  const sourceColor =
    item.source === "Google News"
      ? "text-blue-500"
      : item.source === "Naver News"
      ? "text-green-600"
      : "text-gray-500";

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-white border border-gray-100 rounded-xl p-6 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all duration-200"
    >
      {/* 📰 뉴스 제목 */}
      <h3 className="text-[16px] font-semibold text-gray-900 leading-snug mb-3 line-clamp-3">
        {item.title}
      </h3>

      {/* 🧠 AI 요약문 */}
      {item.summary && (
        <p className="text-[14px] text-gray-700 mb-4 leading-relaxed line-clamp-4">
          {item.summary}
        </p>
      )}

      {/* 🔹 구분선 + 출처 */}
      <div className="border-t border-gray-100 pt-3 flex justify-between items-center">
        <span className={`text-xs font-medium ${sourceColor}`}>
          {item.source}
        </span>
        <span className="text-xs text-indigo-600 font-semibold hover:underline">
          자세히 보기 →
        </span>
      </div>
    </a>
  );
}
