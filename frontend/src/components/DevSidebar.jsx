// src/components/DevSidebar.jsx
import React from "react";

export default function DevSidebar({ selected, onSelect }) {
  const categories = [
    { key: "all", label: "All" },
    { key: "frontend", label: "Front-end" },
    { key: "backend", label: "Back-end" },
    { key: "ai", label: "AI / ML" },
    { key: "devops", label: "DevOps" },
    { key: "career", label: "Career" },
  ];

  return (
    <aside className="w-60 bg-white border rounded-xl p-5 h-fit shadow-sm">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">
        Filter by Category
      </h2>

      <div className="space-y-2">
        {categories.map((c) => (
          <button
            key={c.key}
            onClick={() => onSelect(c.key)}
            className={`w-full px-3 py-2 rounded-md border text-left text-sm font-medium transition
              ${
                selected === c.key
                  ? "bg-emerald-600 text-white border-emerald-600"
                  : "bg-gray-50 text-gray-700 border-gray-300 hover:bg-gray-100"
              }
            `}
          >
            {c.label}
          </button>
        ))}
      </div>
    </aside>
  );
}
