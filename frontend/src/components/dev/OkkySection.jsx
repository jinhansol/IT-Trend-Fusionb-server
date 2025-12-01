import React, { useState } from "react";
import DevCard from "./DevCard";

export default function OkkySection({ data, filter }) {
  const [page, setPage] = useState(1);
  const perPage = 10;

  // 🔥 data는 이제 배열이 아니라 { items, total } 구조임
  const listData = data?.items || [];

  if (!listData || listData.length === 0)
    return <p className="text-gray-500 text-sm">No OKKY posts found.</p>;

  // 필터 적용
  const filtered =
    filter === "all"
      ? listData
      : listData.filter((d) => d.tags?.includes(filter));

  // 페이지네이션 계산
  const totalPage = Math.ceil(filtered.length / perPage);
  const start = (page - 1) * perPage;
  const list = filtered.slice(start, start + perPage);

  return (
    <section className="space-y-4">
      {/* 2열 그리드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {list.map((post) => (
          <DevCard key={post.id} item={post} />
        ))}
      </div>

      {/* 페이지네이션 */}
      <div className="flex justify-center gap-4 mt-8">
        <button
          onClick={() => setPage((p) => p - 1)}
          disabled={page <= 1}
          className="px-4 py-2 bg-gray-200 rounded disabled:bg-gray-100"
        >
          Prev
        </button>

        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={page >= totalPage}
          className="px-4 py-2 bg-gray-200 rounded disabled:bg-gray-100"
        >
          Next
        </button>
      </div>
    </section>
  );
}
