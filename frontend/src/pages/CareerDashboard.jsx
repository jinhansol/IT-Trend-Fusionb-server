// src/pages/CareerDashboard.jsx
import React, { useState, useEffect } from "react";
import CareerChart from "../components/CareerChart";
import JobCard from "../components/JobCard";
import AiInsightBox from "../components/AiInsightBox";
import QuickStatsBox from "../components/QuickStatsBox";
import LearnMaterialCard from "../components/LearnMaterialCard";
import { fetchCareerData } from "../api/careerAPI"; // ✅ 실제 백엔드 연동

export default function CareerDashboard() {
  const [selectedSkill, setSelectedSkill] = useState("Python");
  const [selectedRole, setSelectedRole] = useState("프론트엔드 개발자");
  const [careerData, setCareerData] = useState({
    jobs: [],
    insights: [],
    stats: {},
    learning: [],
  });
  const [loading, setLoading] = useState(true);

  // ✅ 최초 및 스킬 변경 시 백엔드 데이터 로드
  useEffect(() => {
    async function loadCareerData() {
      try {
        setLoading(true);
        const jobs = await fetchCareerData(selectedSkill);
        setCareerData((prev) => ({
          ...prev,
          jobs,
          insights: [
            {
              title: "Market Trend",
              desc: "프론트엔드 직군은 협업 능력과 모던 프레임워크 경험이 중요합니다.",
            },
            {
              title: "Skill Gap",
              desc: `${selectedSkill} 학습 시 채용 기회가 약 35% 증가합니다.`,
            },
            {
              title: "Salary Insight",
              desc: "React, Python 개발자는 평균 연봉이 10~15% 높습니다.",
            },
          ],
          stats: {
            total: 1247,
            newThisWeek: 89,
            myApplications: 12,
            responseRate: 25,
          },
          learning: [
            {
              title: "Complete Guide to React Hooks",
              tag: "Trending",
              desc: "컴포넌트 디자인을 위한 React Hooks 마스터 가이드",
              link: "https://www.inflearn.com",
            },
            {
              title: "TypeScript for Beginners",
              tag: "Popular",
              desc: "대규모 앱 개발을 위한 TypeScript 기본과 패턴",
              link: "https://github.com",
            },
            {
              title: "Node.js Backend Development",
              tag: "New",
              desc: "Node.js와 Express를 활용한 서버 구축 기초",
              link: "https://www.inflearn.com",
            },
          ],
        }));
      } catch (error) {
        console.error("[CareerDashboard] 데이터 로드 오류:", error);
      } finally {
        setLoading(false);
      }
    }

    loadCareerData();
  }, [selectedSkill]);

  // ✅ 로딩 상태 처리
  if (loading) {
    return (
      <div className="p-6 text-center text-gray-500">
        커리어 데이터를 불러오는 중입니다...
      </div>
    );
  }

  const { jobs, insights, stats, learning } = careerData;

  return (
    <div className="p-6 space-y-8 bg-[#fafafa]">
      {/* 상단 필터 영역 */}
      <div className="flex items-center gap-4">
        <select
          className="border border-gray-300 p-2 rounded-md"
          value={selectedSkill}
          onChange={(e) => setSelectedSkill(e.target.value)}
        >
          <option>React</option>
          <option>TypeScript</option>
          <option>Node.js</option>
          <option>Python</option>
          <option>AI</option>
        </select>

        <select
          className="border border-gray-300 p-2 rounded-md"
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
        >
          <option>프론트엔드 개발자</option>
          <option>백엔드 개발자</option>
          <option>AI 엔지니어</option>
        </select>

        <button
          onClick={() => fetchCareerData(selectedSkill)}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          새로고침
        </button>
      </div>

      {/* 기술 수요 트렌드 */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h2 className="font-semibold text-gray-800 mb-4">기술 수요 트렌드</h2>
        <CareerChart />
      </div>

      {/* 채용 정보 + 인사이트 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 좌측: 채용 리스트 */}
        <div className="col-span-2 bg-white rounded-xl shadow-sm p-6 border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-800">최근 채용 공고</h2>
            <p className="text-xs text-gray-400">2시간 전 업데이트됨</p>
          </div>

          {jobs && jobs.length > 0 ? (
            <div className="space-y-4">
              {jobs.map((job, idx) => (
                <JobCard key={idx} job={job} />
              ))}
            </div>
          ) : (
            <p className="text-gray-500">현재 표시할 채용 공고가 없습니다.</p>
          )}
        </div>

        {/* 우측: 인사이트 + 통계 */}
        <div className="flex flex-col gap-6">
          <div className="flex-[0.7] bg-blue-50 rounded-xl shadow-sm">
            <AiInsightBox insights={insights} />
          </div>
          <div className="flex-[0.3] bg-white rounded-xl shadow-sm p-6">
            <QuickStatsBox stats={stats} />
          </div>
        </div>
      </div>

      {/* 학습 추천 */}
      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h2 className="font-semibold text-gray-800 mb-4">학습 추천</h2>
        <div className="grid grid-cols-3 gap-4">
          {learning.map((item, idx) => (
            <LearnMaterialCard key={idx} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
}
