// src/pages/CareerDashboard.jsx
import React, { useEffect, useState } from "react";
import CareerChart from "../components/CareerChart";
import JobCard from "../components/JobCard";
import QuickStatsBox from "../components/QuickStatsBox";
import LearnMaterialCard from "../components/LearnMaterialCard";

import { fetchCareerDashboard, fetchLearningRecommend } from "../api/careerAPI";

export default function CareerDashboard() {
  const [careerData, setCareerData] = useState(null);
  const [learningList, setLearningList] = useState([]);   // ⭐ 추가
  const [loading, setLoading] = useState(true);

  // 🚀 페이징 상태
  const [page, setPage] = useState(1);
  const pageSize = 5;

  const token = localStorage.getItem("token");
  const endpoint = token ? "/dashboard" : "/public";

  useEffect(() => {
    async function loadData() {
      setLoading(true);

      // 기존 Career 데이터
      const data = await fetchCareerDashboard(endpoint);
      setCareerData(data);

      // ⭐ AI 학습 추천 불러오기
      const learning = await fetchLearningRecommend();
      setLearningList(learning);

      setLoading(false);
    }
    loadData();
  }, []);

  if (loading || !careerData) {
    return <div className="p-6 text-center text-gray-500">불러오는 중...</div>;
  }

  const { mode, jobs, trends, user_skills } = careerData;

  // 🔥 페이징 처리
  const totalPages = Math.ceil(jobs.length / pageSize);
  const start = (page - 1) * pageSize;
  const paginatedJobs = jobs.slice(start, start + pageSize);

  return (
    <div className="p-6 space-y-8 bg-[#fafafa]">

      {/* 타이틀 */}
      <h1 className="text-xl font-bold text-gray-800">
        {mode === "personalized"
          ? `${user_skills.join(", ")} 기반 대시보드`
          : "기반 대시보드"}
      </h1>

      {/* 기술 수요 트렌드 */}
      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="font-semibold text-gray-800 mb-4">기술 수요 트렌드</h2>

        <CareerChart data={trends} />

        <p className="mt-3 text-sm text-gray-500">
          최근 8주간 채용 공고 데이터 기반 기술 트렌드입니다.
        </p>
      </div>

      {/* 메인 레이아웃 */}
      <div className="grid grid-cols-3 gap-6">

        {/* 좌측: 채용 공고 + 페이징 */}
        <div className="col-span-2 bg-white rounded-xl shadow-sm p-6 border">

          <h2 className="font-semibold text-gray-800 mb-4">추천 채용 공고</h2>

          {paginatedJobs.length > 0 ? (
            <div className="space-y-4">
              {paginatedJobs.map((job, index) => (
                <JobCard key={index} job={job} />
              ))}
            </div>
          ) : (
            <p className="text-gray-500">추천 공고가 없습니다.</p>
          )}

          {/* 페이징 UI */}
          <div className="flex items-center justify-center gap-4 mt-6">
            <button
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              disabled={page === 1}
              className={`px-4 py-2 rounded border ${
                page === 1
                  ? "text-gray-400 border-gray-300 bg-gray-100"
                  : "bg-white hover:bg-gray-50"
              }`}
            >
              이전
            </button>

            <span className="text-gray-700 font-medium">
              {page} / {totalPages}
            </span>

            <button
              onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
              disabled={page === totalPages}
              className={`px-4 py-2 rounded border ${
                page === totalPages
                  ? "text-gray-400 border-gray-300 bg-gray-100"
                  : "bg-white hover:bg-gray-50"
              }`}
            >
              다음
            </button>
          </div>
        </div>

        {/* 우측: 요약 통계 + 학습 추천 */}
        <div className="flex flex-col gap-6">

          {/* 요약 통계 */}
          <QuickStatsBox
            stats={{
              total: jobs.length,
              newThisWeek: Math.floor(jobs.length * 0.3),
              responseRate: 20,
            }}
          />

          {/* ⭐ AI 기반 학습 추천 */}
          <div className="bg-white rounded-xl shadow-sm p-6 border">
            <h2 className="font-semibold text-gray-800 mb-4">학습 추천</h2>

            <div className="grid grid-cols-1 gap-4">
              {learningList.map((item, i) => (
                <LearnMaterialCard key={i} item={item} />
              ))}
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
