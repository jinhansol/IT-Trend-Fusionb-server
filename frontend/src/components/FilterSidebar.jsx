import React, { useEffect, useState } from "react";
import { fetchDevTags } from "../../api/devAPI";

export default function FilterSidebar({ selected, onSelect }) {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadTags = async () => {
      try {
        const res = await fetchDevTags(); // API에서 동적 태그 가져오기
        setTags(res.tags || []);
      } catch (err) {
        console.error("❌ Failed to load tags:", err);
      } finally {
        setLoading(false);
      }
    };

    loadTags();
  }, []);

  if (loading) {
    return (
      <aside className="w-60 bg-white border rounded-xl p-4 h-fit">
        <p className="text-gray-500 text-sm">Loading tags...</p>
      </aside>
    );
  }

  return (
    <aside className="w-60 bg-white border rounded-xl p-4 h-fit">
      <h2 className="text-sm font-semibold text-gray-600 mb-3">
        Filter by Tags
      </h2>

      <div className="space-y-2">
        {/* 전체 보기 */}
        <button
          onClick={() => onSelect("all")}
          className={`w-full text-left px-3 py-2 rounded-md border text-sm ${
            selected === "all"
              ? "bg-emerald-600 text-white border-emerald-600"
              : "bg-gray-50 hover:bg-gray-100 border-gray-300"
          }`}
        >
          All
        </button>

        {/* 동적으로 태그 목록 렌더링 */}
        {tags.map((tag) => (
          <button
            key={tag}
            onClick={() => onSelect(tag)}
            className={`w-full text-left px-3 py-2 rounded-md border text-sm
              ${
                selected === tag
                  ? "bg-emerald-600 text-white border-emerald-600"
                  : "bg-gray-50 hover:bg-gray-100 border-gray-300"
              }`}
          >
            {tag}
          </button>
        ))}
      </div>
    </aside>
  );
}
