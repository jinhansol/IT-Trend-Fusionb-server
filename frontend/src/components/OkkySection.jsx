// src/components/dev/OkkySection.jsx
import React from "react";
import DevCard from "./DevCard";

export default function OkkySection({ data, filter }) {
  if (!data || data.length === 0)
    return <p className="text-gray-500 text-sm">No OKKY posts found.</p>;

  const filtered = filter === "all"
    ? data
    : data.filter((d) => d.tags?.includes(filter));

  return (
    <section className="space-y-4">
      {filtered.map((post) => (
        <DevCard key={post.url} item={post} />
      ))}
    </section>
  );
}
