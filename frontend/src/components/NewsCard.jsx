import React from "react";

export default function NewsCard({ item }) {
  if (!item) return null;

  const fallbackImg = "https://cdn-icons-png.flaticon.com/512/2965/2965879.png";
  const image = item.image || fallbackImg;

  const sourceColor =
    item.source === "Google News"
      ? "text-blue-500"
      : item.source === "Naver News"
      ? "text-green-600"
      : "text-gray-500";

  return (
    <div className="bg-white shadow-sm rounded-2xl overflow-hidden transition-transform hover:-translate-y-1 hover:shadow-lg duration-200">
      {/* 썸네일 */}
      <div className="h-40 w-full bg-gray-100 flex items-center justify-center">
        <img
          src={image}
          alt={item.title}
          className="object-cover h-full w-full"
          onError={(e) => (e.target.src = fallbackImg)}
        />
      </div>

      {/* 본문 */}
      <div className="p-4 flex flex-col justify-between min-h-[180px]">
        <h3 className="text-sm font-semibold text-gray-800 line-clamp-2 mb-1">
          {item.title}
        </h3>
        <p className="text-sm text-gray-600 line-clamp-3">{item.summary}</p>

        <div className="flex justify-between items-center mt-3">
          <span className={`text-xs font-medium ${sourceColor}`}>
            {item.source}
          </span>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-500 hover:text-indigo-600 transition"
          >
            자세히 보기 →
          </a>
        </div>
      </div>
    </div>
  );
}
