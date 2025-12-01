import React from "react";

export default function JobCard({ job }) {
  return (
    <div className="bg-white rounded-xl border p-4 shadow-sm flex flex-col gap-2 hover:shadow-md transition">
      {/* 상단 기본 정보 */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="font-semibold">{job.company}</h3>
          <p className="text-sm text-gray-600">{job.title}</p>
        </div>

        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
        >
          공고 보기 →
        </a>
      </div>

      {/* 위치 정보 */}
      {job.location && (
        <p className="text-sm text-gray-500">{job.location}</p>
      )}

      {/* 태그 */}
      {Array.isArray(job.tags) && job.tags.length > 0 && (
        <div className="flex gap-2 flex-wrap mt-2">
          {job.tags.map((tag, idx) => (
            <span
              key={idx}
              className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* 날짜 */}
      {job.posted_date && (
        <p className="text-xs text-gray-400 mt-1">
          등록일: {new Date(job.posted_date).toLocaleDateString("ko-KR")}
        </p>
      )}
    </div>
  );
}
