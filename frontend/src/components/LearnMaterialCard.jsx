// src/components/LearnMaterialCard.jsx
import React from "react";

export default function LearnMaterialCard({ item }) {
  return (
    <div className="border rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition">
      <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">{item.tag}</span>
      <h3 className="font-semibold mt-2 text-gray-800">{item.title}</h3>
      <p className="text-sm text-gray-500 mb-3">{item.source}</p>
      <a
        href="#"
        className="text-blue-600 text-sm font-medium hover:underline"
      >
        Learn More →
      </a>
    </div>
  );
}
