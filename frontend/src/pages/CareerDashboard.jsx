// src/pages/CareerDashboard.jsx
import React, { useEffect, useState, useCallback } from "react";
import CareerChart from "../components/career/CareerChart";
import JobCard from "../components/career/JobCard";
import LearnMaterialCard from "../components/career/LearnMaterialCard";

import {
  fetchCareerDashboard,
  fetchLearningRecommend,
} from "../api/careerAPI";

// ✅ userAPI에서 getInterests 추가 (관심사 조회용)
import { getInterests } from "../api/userAPI"; 

export default function CareerDashboard() {
  const [careerData, setCareerData] = useState(null);
  const [learningList, setLearningList] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // 차트 모드: 'frontend' 또는 'backend'
  const [chartMode, setChartMode] = useState("frontend"); 

  // 페이지당 6개
  const [page, setPage] = useState(1);
  const pageSize = 6;

  // 🛠️ [Helper] 토큰에서 User ID 추출하는 함수
  const getUserIdFromToken = () => {
    const token = localStorage.getItem("token");
    if (!token) return null;
    try {
      // JWT 디코딩 (base64)
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      
      const payload = JSON.parse(jsonPayload);
      return payload.id || payload.user_id || payload.sub; 
    } catch (e) {
      console.error("Token decode error:", e);
      return null;
    }
  };

  // ✅ [수정] 데이터 로드 함수를 useCallback으로 감싸서 재사용 가능하게 변경
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const userId = getUserIdFromToken();

      // 1. 데이터 병렬 요청
      const promises = [
          fetchCareerDashboard("/dashboard"),
          fetchLearningRecommend().catch(() => ({ learning: [] })),
      ];

      if (userId) {
          promises.push(getInterests(userId).catch(() => null));
      }

      const [dashboardData, learningData, interestData] = await Promise.all(promises);

      // 2. 데이터 병합 로직
      let finalMode = dashboardData.mode;
      let finalUserSkills = dashboardData.user_skills || [];

      // DB에서 가져온 유저 데이터가 있다면 분석 시작
      if (interestData) {
          const dbTechStack = interestData.tech_stack || [];
          const dbInterests = interestData.interest_topics || interestData.interests || [];
          
          // 기술 스택이나 관심사가 하나라도 있으면 Personal 모드 강제 전환
          if (dbTechStack.length > 0 || dbInterests.length > 0) {
              finalMode = "personalized";
              
              if (finalUserSkills.length === 0) {
                  finalUserSkills = dbTechStack.length > 0 ? dbTechStack : dbInterests;
              }
          }
      }

      // 병합된 데이터 적용
      setCareerData({
          ...dashboardData,
          mode: finalMode,
          user_skills: finalUserSkills
      });

      // 학습 데이터 적용
      setLearningList(Array.isArray(learningData) ? learningData : learningData.learning || []);

    } catch (error) {
      console.error("데이터 로딩 실패:", error);
    } finally {
      setLoading(false);
    }
  }, []); // 의존성 배열 비움 (항상 동일한 함수 참조 유지)

  // ✅ [수정] useEffect에서 초기 로드 및 이벤트 리스너 등록
  useEffect(() => {
    // 1. 처음 마운트 시 데이터 로드
    loadData();

    // 2. 로그인/로그아웃 이벤트("auth-change") 감지 -> 데이터 새로고침
    const handleAuthChange = () => {
        console.log("🔔 로그인 상태 변경 감지! 대시보드를 새로고침합니다.");
        loadData();
    };

    window.addEventListener("auth-change", handleAuthChange);

    // 3. 컴포넌트 언마운트 시 리스너 제거 (메모리 누수 방지)
    return () => {
        window.removeEventListener("auth-change", handleAuthChange);
    };
  }, [loadData]);


  if (loading || !careerData) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <p className="text-gray-400 animate-pulse">데이터를 분석 중입니다...</p>
        </div>
    );
  }

  // ✅ 데이터 해체
  const { 
      mode, 
      jobs, 
      frontend_trends = [], 
      backend_trends = [], 
      user_skills 
  } = careerData;

  // ✅ 차트 데이터 스위칭
  const currentTrends = chartMode === "frontend" ? frontend_trends : backend_trends;

  // 차트 컴포넌트로 보낼 데이터 가공
  const trendChartData = currentTrends.map((t) => ({
    name: t.skill,
    value: t.count,
  }));

  // 공고 페이지네이션 처리
  const totalJobs = jobs?.length || 0;
  const totalPages = Math.ceil(totalJobs / pageSize);
  const start = (page - 1) * pageSize;
  const paginatedJobs = (jobs || []).slice(start, start + pageSize);

  // 요약 통계 계산
  const calculateTopSkill = () => {
    if (!jobs || jobs.length === 0) return "-";
    const tagCount = {};
    jobs.forEach(job => {
      if (job.tags) {
        job.tags.forEach(tag => tagCount[tag] = (tagCount[tag] || 0) + 1);
      }
    });
    const sortedTags = Object.entries(tagCount).sort((a, b) => b[1] - a[1]);
    return sortedTags.length > 0 ? sortedTags[0][0] : "-";
  };

  const topSkill = calculateTopSkill();
  const newThisWeek = Math.floor(totalJobs * 0.2); 

  return (
    <div className="min-h-screen bg-[#F8F9FA] p-8 font-sans text-gray-800">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* 1. 헤더 */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                {mode === "personalized" ? "💼 맞춤 채용 추천" : "📈 전체 채용 트렌드"}
                {mode === "personalized" && (
                    <span className="bg-indigo-100 text-indigo-700 text-xs px-2 py-1 rounded-full font-medium">
                        Personalized
                    </span>
                )}
            </h1>
            <p className="text-gray-500 text-sm mt-2">
                {mode === "personalized" 
                    ? "선택하신 기술 스택을 기반으로 분석된 공고입니다." 
                    : "현재 시장에서 가장 인기 있는 채용 공고들입니다."}
            </p>
          </div>

          {mode === "personalized" && user_skills && user_skills.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-end max-w-md">
                  {user_skills.map((skill, idx) => (
                      <span key={idx} className="px-3 py-1 bg-white border border-indigo-200 text-indigo-600 text-xs rounded-full font-semibold shadow-sm">
                          #{skill}
                      </span>
                  ))}
              </div>
          )}
        </header>

        {/* 2. 상단: 기술 트렌드 차트 (토글 적용) */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold flex items-center gap-2">
              📊 분야별 필수 기술 순위
            </h2>
            
            <div className="flex items-center gap-3">
                {/* ✅ Frontend / Backend 토글 버튼 */}
                <div className="bg-gray-100 p-1 rounded-lg flex text-xs font-medium">
                    <button
                        onClick={() => setChartMode("frontend")}
                        className={`px-3 py-1.5 rounded-md transition-all ${
                            chartMode === "frontend" 
                            ? "bg-white text-indigo-600 shadow-sm font-bold" 
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                    >
                        Frontend
                    </button>
                    <button
                        onClick={() => setChartMode("backend")}
                        className={`px-3 py-1.5 rounded-md transition-all ${
                            chartMode === "backend" 
                            ? "bg-white text-indigo-600 shadow-sm font-bold" 
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                    >
                        Backend
                    </button>
                </div>
                
                <span className="text-xs text-gray-500 bg-gray-50 px-2.5 py-1 rounded-md border border-gray-200">
                    최근 8주 기준
                </span>
            </div>
          </div>
          
          <div className="w-full h-[320px]">
             {trendChartData.length > 0 ? (
                 <CareerChart data={trendChartData} />
             ) : (
                 <div className="h-full flex items-center justify-center text-gray-400 text-sm">
                     분석할 데이터가 충분하지 않습니다.
                 </div>
             )}
          </div>
        </section>

        {/* 3. 메인 그리드 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* 👈 왼쪽: 채용 공고 리스트 */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex justify-between items-end px-1">
                  <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                    {mode === "personalized" ? "🎯 추천 공고" : "💼 최신 공고"}
                  </h2>
                  <span className="text-xs text-gray-500">
                    총 {totalJobs}건 중 {page}페이지
                  </span>
            </div>
            
            <div className="space-y-4">
              {paginatedJobs.length > 0 ? (
                paginatedJobs.map((job, index) => (
                  <JobCard key={job.id || index} job={job} />
                ))
              ) : (
                <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 text-gray-400">
                  <p className="mb-2">조건에 딱 맞는 공고를 찾지 못했습니다. 😢</p>
                  <p className="text-sm">관심사를 조금 더 넓게 설정해보세요.</p>
                </div>
              )}
            </div>

            {/* 페이지네이션 */}
            {totalPages > 1 && (
                <div className="flex justify-center gap-2 mt-4">
                  <button
                    onClick={() => setPage((p) => Math.max(p - 1, 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white rounded-lg border">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                    disabled={page === totalPages}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-50 transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}
          </div>

          {/* 👉 오른쪽: 통계 + 학습 추천 */}
          <div className="lg:col-span-1 space-y-8 sticky top-6">
            
            {/* 요약 통계 */}
            <div>
                <h3 className="font-bold text-gray-800 mb-4 px-1">요약 통계</h3>
                <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-500">검색된 공고</span>
                        <span className="font-bold text-gray-900 text-lg">{totalJobs}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-500">신규 업데이트</span>
                        <span className="font-bold text-green-600">+{newThisWeek}</span>
                    </div>
                    <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                        <span className="text-sm text-gray-500">추천 공고 TOP 스킬</span>
                        <span className="font-bold text-blue-600">{topSkill}</span>
                    </div>
                </div>
            </div>

            {/* 학습 추천 */}
            <div>
                <div className="flex items-center gap-2 mb-4 px-1">
                    <h3 className="font-bold text-gray-800">📚 맞춤 학습 추천</h3>
                </div>
                
                <div className="grid grid-cols-1 gap-4">
                    {learningList.length > 0 ? (
                        learningList.slice(0, 5).map((item, i) => (
                        <LearnMaterialCard key={i} item={item} />
                        ))
                    ) : (
                        <p className="text-gray-400 text-xs text-center py-4 bg-white rounded-xl border border-gray-100">
                        학습 추천 데이터를 불러오는 중...
                        </p>
                    )}
                </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}