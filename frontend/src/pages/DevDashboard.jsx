// src/pages/DevDashboard.jsx
import React, { useEffect, useState, useCallback } from "react";
import {
  fetchDevPublic,
  fetchDevPersonal,
  fetchDevTopicInsight,
  fetchDevIssueInsight,
} from "../api/devAPI";

// 유저 관심사 조회 API
import { getInterests } from "../api/userAPI";

import OkkySection from "../components/dev/OkkySection";
import DevtoSection from "../components/dev/DevtoSection";
import TopicInsightChart from "../components/dev/TopicInsightChart";
import IssueInsightChart from "../components/dev/IssueInsightChart";

export default function DevDashboard() {
  // 초기 상태: items가 비어있는 FeedSection 구조로 초기화
  const [feed, setFeed] = useState({ 
      okky: { items: [], total: 0 }, 
      devto: { items: [], total: 0 } 
  });
  const [topicInsight, setTopicInsight] = useState(null);
  const [issueInsight, setIssueInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // 모드 상태: 'public' or 'personal'
  const [viewMode, setViewMode] = useState("public");
  const [personalInterests, setPersonalInterests] = useState([]);
  
  const [activeTab, setActiveTab] = useState("okky");

  // 🛠️ 토큰에서 User ID 추출
  const getUserIdFromToken = () => {
    const token = localStorage.getItem("token");
    if (!token) return null;
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      const payload = JSON.parse(jsonPayload);
      return payload.id || payload.user_id || payload.sub; 
    } catch (e) {
      return null;
    }
  };

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const userId = getUserIdFromToken();

      // 1. 인사이트(차트) 데이터 (실패해도 빈값 처리)
      const topicReq = fetchDevTopicInsight().catch(() => ({ clusters: [] }));
      const issueReq = fetchDevIssueInsight().catch(() => ({ issues: {} }));

      // 2. 유저 관심사 확인 및 모드 결정
      let userInterests = [];
      let mode = "public";

      if (userId) {
        try {
            const interestData = await getInterests(userId);
            if (interestData) {
                // tech_stack과 interests를 모두 합침
                const dbTech = interestData.tech_stack || [];
                const dbInterests = interestData.interest_topics || interestData.interests || [];
                userInterests = [...new Set([...dbTech, ...dbInterests])];
                
                // 관심사가 있다면 Personal 모드로 진입
                if (userInterests.length > 0) {
                    mode = "personal";
                }
            }
        } catch (e) {
            console.warn("관심사 조회 실패 (Public 모드로 진행):", e);
        }
      }

      // 3. 모드에 따른 피드 데이터 요청
      let feedData = null;
      if (mode === "personal") {
          try {
              // 백엔드가 Personal도 Public과 동일하게 { okky, devto } 구조로 반환해줌
              feedData = await fetchDevPersonal();
          } catch (e) {
              console.warn("Personal Feed 요청 실패 -> Public으로 전환");
              mode = "public";
              feedData = await fetchDevPublic();
          }
      } else {
          feedData = await fetchDevPublic();
      }

      // 4. 모든 데이터 수신 완료 대기
      const [topic, issue] = await Promise.all([topicReq, issueReq]);

      // 5. 상태 업데이트
      setTopicInsight(topic);
      setIssueInsight(issue);
      
      // feedData가 null일 경우 안전하게 빈 구조 할당
      setFeed(feedData || { okky: { items: [], total: 0 }, devto: { items: [], total: 0 } });
      
      setViewMode(mode);
      setPersonalInterests(userInterests);

    } catch (err) {
      console.error("❌ Dev Dashboard Load Error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // 초기 로드 및 로그인 이벤트 리스너
  useEffect(() => {
    loadData();
    const handleAuthChange = () => loadData();
    window.addEventListener("auth-change", handleAuthChange);
    return () => window.removeEventListener("auth-change", handleAuthChange);
  }, [loadData]);

  if (loading) return <div className="text-center py-20 text-gray-400">트렌드 분석 중...</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-16">
      
      {/* 🔹 헤더 섹션 */}
      <div className="text-center space-y-3">
        <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight flex items-center justify-center gap-3">
          👨‍💻 Developer Dashboard
          {viewMode === "personal" && (
             <span className="bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wide">
               My Feed
             </span>
          )}
        </h1>
        <p className="text-gray-500">
          {viewMode === "personal"
            ? "설정하신 기술 스택과 관심사를 기반으로 엄선된 아티클입니다." 
            : "최신 개발 트렌드와 핫한 이슈를 한눈에 확인하세요."}
        </p>
        
        {/* 적용된 태그 리스트 */}
        {viewMode === "personal" && personalInterests.length > 0 && (
            <div className="flex flex-wrap justify-center gap-2 mt-2">
                {personalInterests.map((tag, idx) => (
                    <span key={idx} className="px-3 py-1 bg-white border border-blue-200 text-blue-600 text-xs rounded-full font-medium shadow-sm">
                        #{tag}
                    </span>
                ))}
            </div>
        )}
      </div>

      {/* 🔹 인사이트 차트 (공통) */}
      <section>
        <div className="flex items-center justify-center mb-8">
           <h2 className="text-2xl font-bold text-gray-800">Insight Overview</h2>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col items-center">
            <h3 className="text-lg font-semibold mb-2 text-gray-800">🔥 Trending Topics</h3>
            <div className="w-full h-[350px] flex items-center justify-center">
                {topicInsight ? <TopicInsightChart data={topicInsight} /> : <p className="text-gray-400">Loading...</p>}
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col items-center">
            <h3 className="text-lg font-semibold mb-2 text-gray-800">⚠ Issue Breakdown</h3>
            <div className="w-full h-[350px] flex items-center justify-center">
                {issueInsight ? <IssueInsightChart data={issueInsight} /> : <p className="text-gray-400">Loading...</p>}
            </div>
          </div>
        </div>
      </section>

      <hr className="border-gray-200" />

      {/* 🔹 아티클 섹션 */}
      <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row items-center justify-between mb-8 gap-4">
            <h2 className="text-2xl font-bold text-gray-800 border-l-4 border-green-500 pl-4">
                {viewMode === "personal" ? "🎯 Recommended Articles" : "Community Articles"}
            </h2>
            
            {/* 탭 버튼 */}
            <div className="flex bg-gray-100 p-1.5 rounded-xl">
               <button
                 onClick={() => setActiveTab("okky")}
                 className={`px-6 py-2 text-sm font-bold rounded-lg transition-all shadow-sm ${
                   activeTab === "okky" ? "bg-white text-green-600 ring-1 ring-black/5" : "text-gray-500 hover:text-gray-700 hover:bg-gray-200/50 shadow-none"
                 }`}
               >
                 OKKY
               </button>
               <button
                 onClick={() => setActiveTab("devto")}
                 className={`px-6 py-2 text-sm font-bold rounded-lg transition-all shadow-sm ${
                   activeTab === "devto" ? "bg-white text-blue-600 ring-1 ring-black/5" : "text-gray-500 hover:text-gray-700 hover:bg-gray-200/50 shadow-none"
                 }`}
               >
                 Dev.to
               </button>
            </div>
        </div>

        <div className="min-h-[500px]">
            {activeTab === "okky" && (
              <div className="animate-fade-in">
                 {/* 데이터 전달 시 feed.okky 전체 객체를 넘깁니다 (Section 내부에서 items, total 사용) */}
                 <OkkySection data={feed.okky} filter="all" />
              </div>
            )}
            {activeTab === "devto" && (
              <div className="animate-fade-in">
                 <DevtoSection data={feed.devto} filter="all" />
              </div>
            )}
            
            {/* 데이터가 없을 때 메시지 */}
            {activeTab === "okky" && (!feed.okky?.items || feed.okky.items.length === 0) && (
                <div className="text-center py-20 text-gray-400">해당 조건에 맞는 OKKY 게시글이 없습니다.</div>
            )}
            {activeTab === "devto" && (!feed.devto?.items || feed.devto.items.length === 0) && (
                <div className="text-center py-20 text-gray-400">해당 조건에 맞는 Dev.to 게시글이 없습니다.</div>
            )}
        </div>
      </section>

    </div>
  );
}