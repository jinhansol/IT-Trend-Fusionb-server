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

  // 로그인 여부 체크
  const token = localStorage.getItem("token");
  const endpoint = token ? "/dashboard" : "/public";

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await fetchCareerDashboard(endpoint);
        setCareerData(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
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
          : "IT Career Dashboard"}
      </h1>

      {/* 기술 수요 트렌드 */}
      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="font-semibold text-gray-800 mb-4">기술 수요 트렌드</h2>
        <CareerChart data={trends} />

        <p className="mt-3 text-sm text-gray-500">
          최근 8주간 채용 공고에서 언급된 기술 스택을 분석해 만든 차트입니다.
        </p>
      </div>

      {/* 채용 정보 + 인사이트 */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="font-semibold text-gray-800 mb-4">추천 채용 공고</h2>

          {jobs.length > 0 ? (
            <div className="space-y-4">
              {jobs.map((job, i) => (
                <JobCard key={i} job={job} />
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
                desc: `지난 8주간 가장 많이 언급된 기술은 ${trends[0]?.skill} 입니다.`,
              },
              {
                title: "기술 성장성",
                desc: "백엔드·프론트엔드보다 AI 관련 직무 공고 증가율이 빠른 편입니다.",
              },
              {
                title: "취업 전략",
                desc: "실무형 프로젝트 경험이 기술 역량보다 더 큰 차별점이 됩니다.",
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
              title: "최근 기술 트렌드 분석법",
              tag: "추천",
              desc: "실제 채용 데이터를 기반으로 기술 트렌드를 이해하는 방법",
              link: "https://github.com",
            }}
          />
          <LearnMaterialCard
            item={{
              title: "AI 기반 이력서 작성",
              tag: "핫",
              desc: "개발자 채용 담당자가 실제로 보는 핵심 포인트",
              link: "https://fastcampus.co.kr",
            }}
          />
          <LearnMaterialCard
            item={{
              title: "실무형 프로젝트 구성법",
              tag: "추천",
              desc: "신입/주니어 개발자에게 가장 중요한 포트폴리오 구성 요소",
              link: "https://inflearn.com",
            }}
          />
        </div>
      </div>
    </div>
  );
}
