// src/pages/CareerDashboard.jsx
import React, { useEffect, useState } from "react";
import CareerChart from "../components/CareerChart";
import JobCard from "../components/JobCard";
import AiInsightBox from "../components/AiInsightBox";
import QuickStatsBox from "../components/QuickStatsBox";
import LearnMaterialCard from "../components/LearnMaterialCard";
import { fetchCareerDashboard } from "../api/careerAPI";

export default function CareerDashboard() {
  const [careerData, setCareerData] = useState(null);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem("token");
  const endpoint = token ? "/dashboard" : "/public";

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      const data = await fetchCareerDashboard(endpoint);
      setCareerData(data);
      setLoading(false);
    }
    loadData();
  }, []);

  if (loading || !careerData) {
    return <div className="p-6 text-center text-gray-500">불러오는 중...</div>;
  }

  const { mode, jobs, trends, user_skills } = careerData;

  return (
    <div className="p-6 space-y-8 bg-[#fafafa]">
      <h1 className="text-xl font-bold text-gray-800">
        {mode === "personalized"
          ? `${user_skills.join(", ")} 기반 대시보드`
          : "기반 대시보드"}
      </h1>

      {/* 기술 수요 트렌드 */}
      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="font-semibold text-gray-800 mb-4">기술 수요 트렌드</h2>

        {/* 🔥 동적 데이터 연결 */}
        <CareerChart data={trends} />

        <p className="mt-3 text-sm text-gray-500">
          최근 8주간 채용 공고 데이터 기반 기술 트렌드입니다.
        </p>
      </div>

      {/* 채용 & 인사이트 */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="font-semibold text-gray-800 mb-4">추천 채용 공고</h2>

          {jobs.length > 0 ? (
            <div className="space-y-4">
              {jobs.map((job, index) => (
                <JobCard key={index} job={job} />
              ))}
            </div>
          ) : (
            <p className="text-gray-500">추천 공고가 없습니다.</p>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <AiInsightBox
            insights={[
              {
                title: "기술 트렌드 요약",
                desc:
                  trends.length > 0
                    ? `${trends[0].skill} 기술이 최근 가장 많이 언급되었습니다.`
                    : "데이터가 부족합니다.",
              },
              {
                title: "기술 성장성",
                desc: "백엔드·프론트엔드 대비 AI 직군 성장세가 높습니다.",
              },
              {
                title: "취업 전략",
                desc: "실무형 프로젝트 경험은 경쟁력을 높입니다.",
              },
            ]}
          />

          <QuickStatsBox
            stats={{
              total: jobs.length,
              newThisWeek: Math.floor(jobs.length * 0.3),
              responseRate: 20,
            }}
          />
        </div>
      </div>

      {/* 학습 추천 */}
      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="font-semibold text-gray-800 mb-4">학습 추천</h2>

        <div className="grid grid-cols-3 gap-4">
          <LearnMaterialCard
            item={{
              title: "최근 기술 트렌드 분석",
              tag: "추천",
              desc: "실제 채용 데이터를 기반으로 트렌드 분석",
              link: "#",
            }}
          />
          <LearnMaterialCard
            item={{
              title: "AI 기반 이력서 작성",
              tag: "핫",
              desc: "채용 담당자가 보는 핵심 포인트",
              link: "#",
            }}
          />
          <LearnMaterialCard
            item={{
              title: "실무형 프로젝트 구성법",
              tag: "추천",
              desc: "포트폴리오 전략",
              link: "#",
            }}
          />
        </div>
      </div>
    </div>
  );
}
