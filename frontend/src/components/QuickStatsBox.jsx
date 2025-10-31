import React from "react";

export default function QuickStatsBox({ stats }) {
  // 데이터가 없을 경우 대비
  if (!stats) return null;

  return (
    <div className="flex flex-col">
      <h2 className="font-semibold text-gray-800 mb-3 text-sm">요약 통계</h2>

      <div className="text-sm text-gray-700 space-y-2">
        <div className="flex justify-between">
          <span>총 공고 수</span>
          <span className="font-semibold text-gray-900">
            {stats.total || stats.totalJobs || 0}
          </span>
        </div>
        <div className="flex justify-between">
          <span>이번 주 신규</span>
          <span className="font-semibold text-green-600">
            +{stats.newThisWeek || 0}
          </span>
        </div>
        <div className="flex justify-between">
          <span>내 지원 내역</span>
          <span className="font-semibold text-blue-600">
            {stats.applied || stats.applications || 0}
          </span>
        </div>
        <div className="flex justify-between">
          <span>응답률</span>
          <span className="font-semibold text-yellow-600">
            {stats.responseRate || 0}%
          </span>
        </div>
      </div>

      <div className="border-t border-gray-200 mt-5 pt-1 text-xs text-gray-500 text-right">
        2시간 전 업데이트됨
      </div>
    </div>
  );
}
