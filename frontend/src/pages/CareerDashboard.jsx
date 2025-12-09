// src/pages/CareerDashboard.jsx
import React, { useEffect, useState, useCallback } from "react";
import { Zap, Rocket, Map, ArrowUpRight, User, BookOpen } from "lucide-react";
// ⭐ Recharts 및 Effect 추가
import { 
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis 
} from "recharts";
import confetti from "canvas-confetti";

// API & Components
import { fetchRoadmap } from "../api/roadmapAPI";
import { completeQuest } from "../api/questAPI"; 
import { getInterests } from "../api/userAPI"; 

import SkillTree from "../components/roadmap/SkillTree";
import QuestModal from "../components/roadmap/QuestModal"; 
import QuizModal from "../components/roadmap/QuizModal"; // ⭐ 퀴즈 모달
import AICompassModal from "../modals/AICompassModal";
import TodayQuests from "../components/roadmap/TodayQuests";

export default function CareerDashboard() {
  const [userId, setUserId] = useState(null);
  
  // ⭐ 맵 상태 관리 (기본값: public 정석 로드맵)
  const [activeMap, setActiveMap] = useState("public"); 
  const [viewType, setViewType] = useState("ALL"); 

  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isPreviewMode, setIsPreviewMode] = useState(false);

  const [selectedNode, setSelectedNode] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [isQuizModalOpen, setIsQuizModalOpen] = useState(false); // 퀴즈 모달 상태

  const [activeQuests, setActiveQuests] = useState([]);

  const [userStats, setUserStats] = useState({
    level: 1,
    xp: 0,
    streak: 3,
    title: "새싹 개발자",
  });

  // ⭐ 나의 개발 능력치 (초기값)
  const [skillStats, setSkillStats] = useState([
    { subject: 'Frontend', A: 30, fullMark: 100 },
    { subject: 'Backend', A: 30, fullMark: 100 },
    { subject: 'CS 지식', A: 20, fullMark: 100 },
    { subject: 'AI/Data', A: 10, fullMark: 100 },
    { subject: 'Tools', A: 40, fullMark: 100 },
    { subject: 'Comm', A: 50, fullMark: 100 },
  ]);

  // 🛠️ 토큰에서 User ID 추출
  const getUserIdFromToken = () => {
    const token = localStorage.getItem("token");
    if (!token) return null;
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const payload = JSON.parse(decodeURIComponent(atob(base64).split('').map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join('')));
      return payload.id || payload.user_id || payload.sub; 
    } catch (e) { return null; }
  };

  // 🛠️ [핵심] 데이터 로드 (시나리오 반영)
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const uid = getUserIdFromToken();
      setUserId(uid ? Number(uid) : null);

      let slug = "web-roadmap"; // 기본: Public
      let isPreview = false;    // 기본: 제한 없음

      // -------------------------------------------------------
      // 1. 맵 결정 로직
      // -------------------------------------------------------
      if (activeMap === "personal") {
          slug = "life-coding";
          
          if (uid) {
              // 로그인 유저: 내 관심사 기반 View 설정 + 정식 모드
              try {
                  const interestData = await getInterests(uid);
                  if (interestData) {
                      const allTags = [...(interestData.tech_stack || []), ...(interestData.interest_topics || [])].join(" ").toLowerCase();
                      if (allTags.includes("frontend") || allTags.includes("react") || allTags.includes("vue")) setViewType("FRONTEND");
                      else if (allTags.includes("backend") || allTags.includes("node") || allTags.includes("spring")) setViewType("BACKEND");
                  }
              } catch (e) { console.warn(e); }
              isPreview = false; 
          } else {
              // 비로그인 유저: Personal 탭 접근 시 -> 체험판 모드 (AI 결과 확인 등)
              console.log("👤 비로그인 + Personal 접근 -> 체험판 모드 ON");
              isPreview = true;
              // viewType은 handlePreviewTrack에서 설정된 값 유지
          }
      } else {
          // Public 탭: 로그인 여부 상관없이 전체 공개 (정석 커리큘럼)
          slug = "web-roadmap";
          setViewType("ALL");
          isPreview = false; 
      }

      setIsPreviewMode(isPreview);

      // -------------------------------------------------------
      // 2. 데이터 Fetch
      // -------------------------------------------------------
      const roadmapData = await fetchRoadmap(slug, uid);
      
      if (roadmapData) {
        console.log(`📍 로드맵 로드: ${slug} (Preview: ${isPreview})`);
        
        // ⭐ 체험판 모드일 때만 강제 잠금 처리
        if (isPreview) {
            const lockedNodes = roadmapData.nodes.map((n, i) => ({
                ...n,
                status: i === 0 ? "UNLOCKED" : "LOCKED" // 첫 번째만 열림
            }));
            setRoadmap({ ...roadmapData, nodes: lockedNodes });
            if (lockedNodes.length > 0) setActiveQuests(lockedNodes[0].quests || []);
        } 
        else {
            // 정식 모드 (DB 상태 그대로 사용)
            setRoadmap(roadmapData);
            
            // 현재 진행 중인 노드 찾아서 퀘스트 띄우기
            const currentStep = roadmapData.nodes.find((n) => n.status === "UNLOCKED");
            if (currentStep) setActiveQuests(currentStep.quests || []);
            else if (roadmapData.nodes.length > 0) setActiveQuests(roadmapData.nodes[0].quests || []);
        }
      }

    } catch (err) {
      console.error("❌ Load Error:", err);
    } finally {
      setLoading(false);
    }
  }, [activeMap]); // activeMap이 바뀔 때마다 재실행

  useEffect(() => {
    loadData();
    const handleAuthChange = () => loadData();
    window.addEventListener("auth-change", handleAuthChange);
    return () => window.removeEventListener("auth-change", handleAuthChange);
  }, [loadData]);


  // ============================================
  // 이벤트 핸들러
  // ============================================
  
  // AI 나침반 결과 클릭 시 -> Personal 맵 + 체험판 모드로 전환
  const handlePreviewTrack = async (type) => {
    setIsAIModalOpen(false);
    
    // 뷰 타입 강제 설정
    if (type === "BACKEND") setViewType("BACKEND");
    else if (type === "FRONTEND") setViewType("FRONTEND");
    else setViewType("ALL");

    // 맵 모드 변경 -> useEffect(loadData) 트리거 -> 비로그인이면 체험판 진입
    setActiveMap("personal"); 
    alert(`🚀 ${type} 커리어 체험판이 시작됩니다! (첫 단계만 무료 공개)`);
  };

  const handleNodeClick = (node) => {
    if (isPreviewMode && node.status === "LOCKED") {
      if (window.confirm("🔒 다음 단계는 로그인이 필요합니다.\n로그인하시겠습니까?")) {
        // navigate('/login'); 
      }
      return;
    }
    setActiveQuests(node.quests || []);
    document.getElementById("today-quest-section")?.scrollIntoView({ behavior: "smooth" });
  };

  const handleInternalLink = (link) => {
    if (link === "internal://compass") {
        setIsModalOpen(false);
        setTimeout(() => setIsAIModalOpen(true), 200);
    }
  };

  const handleQuestComplete = async (quest) => {
    try {
      if (userId) await completeQuest(userId, quest.quest_id);
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.8 }, colors: ["#3B82F6", "#10B981", "#F59E0B"] });

      setRoadmap((prev) => {
        if (!prev) return prev;
        const updatedNodes = prev.nodes.map((n) => {
          if (n.db_id !== quest.node_db_id) return n;
          const updatedQuests = n.quests.map((q) => q.quest_id === quest.quest_id ? { ...q, completed: true } : q);
          const allDone = updatedQuests.every((q) => q.completed);
          setActiveQuests(updatedQuests);
          return { ...n, quests: updatedQuests, status: allDone ? "COMPLETED" : n.status };
        });

        let unlockedNodes = updatedNodes;
        const currentNode = updatedNodes.find((n) => n.db_id === quest.node_db_id);

        if (currentNode && currentNode.status === "COMPLETED") {
            // ⭐ 체험판일 때: 다음 단계 안 열어줌 + 회원가입 유도
            if (isPreviewMode) {
                setTimeout(() => alert("🎉 체험판 학습 완료!\n\n다음 단계(심화 과정)를 진행하려면\n회원가입이 필요합니다. 🚀"), 500);
            } 
            else {
                unlockedNodes = updatedNodes.map((n) => {
                    if (n.prerequisites?.includes(currentNode.id) && n.status === "LOCKED") return { ...n, status: "UNLOCKED" };
                    return n;
                });
            }
        }
        return { ...prev, nodes: unlockedNodes };
      });
      setUserStats((prev) => ({ ...prev, xp: prev.xp + (quest.xp || 0) }));
    } catch (e) { console.error(e); }
  };

  // 퀴즈 완료 핸들러
  const handleQuizFinish = (newStats) => {
      setSkillStats(newStats); 
      setIsQuizModalOpen(false);
      confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } }); 
      alert("🎉 진단 완료! 나의 개발 스탯이 업데이트되었습니다.");
  };

  if (loading || !roadmap) return <div className="min-h-screen bg-slate-50 flex items-center justify-center">로딩중...</div>;

  const completedCount = roadmap.nodes.filter((n) => n.status === "COMPLETED").length;
  const totalCount = roadmap.nodes.length;
  const chartData = [{ name: "Python", value: 35, color: "#6366F1" }, { name: "React", value: 30, color: "#0EA5E9" }, { name: "Node.js", value: 20, color: "#10B981" }, { name: "AWS", value: 15, color: "#F59E0B" }];

  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans text-slate-800 pb-20">
      
      {/* 상단 헤더 */}
      <div className="bg-[#0F172A] text-white pt-8 pb-24 rounded-b-[40px] shadow-2xl relative overflow-hidden">
        <div className="absolute top-[-20%] right-[-10%] w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[100px]"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-[300px] h-[300px] bg-indigo-500/20 rounded-full blur-[80px]"></div>
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row justify-between items-end gap-8 relative z-10">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <span className="bg-slate-800 border border-slate-700 px-3 py-1 rounded-full text-xs font-bold text-slate-300">Lv.{userStats.level} {userStats.title}</span>
              <span className="bg-amber-500 text-white px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 shadow-lg shadow-amber-500/30"><Zap size={12} fill="currentColor" /> {userStats.streak}일 연속</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold mb-2">Ready to code? 🚀</h1>
            <p className="text-slate-400 text-sm font-medium">{isPreviewMode ? "체험판 모드로 둘러보는 중입니다." : "나만의 커리어 로드맵을 달성해보세요!"}</p>
          </div>
          
          {/* 우측 진행상황 카드 (기존 유지) */}
          <div className="w-full md:w-[320px] bg-white/5 p-5 rounded-2xl backdrop-blur-md border border-white/10 shadow-inner">
            <div className="flex justify-between items-end mb-2"><p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Current Progress</p><p className="text-xs font-bold text-amber-400 flex items-center gap-1">Next: Golden Badge 🏅</p></div>
            <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden mb-2"><div className="bg-gradient-to-r from-blue-500 to-cyan-400 h-full rounded-full transition-all duration-1000" style={{ width: `${(userStats.xp / 2000) * 100}%` }}></div></div>
            <div className="flex justify-between text-[10px] text-slate-500 font-medium"><span>Lv.1</span><span>{userStats.xp} / 2,000 XP</span></div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 -mt-16 space-y-8 relative z-20">
        
        {/* Top 3 Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* 1. Top Skills Chart (기존 유지) */}
          <div className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 flex flex-col justify-between h-[340px]">
             <div className="flex justify-between items-start"><h2 className="text-lg font-bold">🔥 Top Skills</h2><span className="text-[10px] bg-slate-100 px-2 py-1 rounded">실시간</span></div><div className="flex flex-col items-center justify-center flex-1"><div className="w-[160px] h-[160px] relative mb-4"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={chartData} innerRadius={50} outerRadius={70} paddingAngle={5} dataKey="value">{chartData.map((entry, i) => (<Cell key={i} fill={entry.color} />))}</Pie><Tooltip /></PieChart></ResponsiveContainer><div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center"><span className="block text-2xl font-bold">100</span><span className="text-[10px] text-slate-400 uppercase tracking-wide">Jobs</span></div></div><div className="flex gap-3 justify-center flex-wrap">{chartData.map((item, idx) => (<div key={idx} className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }}></div><span className="text-xs text-slate-500">{item.name}</span></div>))}</div></div>
          </div>

          {/* 2. AI Compass (기존 유지) */}
          <div className="bg-gradient-to-br from-emerald-500 to-teal-600 rounded-3xl p-7 shadow-xl text-white flex flex-col items-center justify-center text-center h-[340px] cursor-pointer hover:-translate-y-1 transition" onClick={() => setIsAIModalOpen(true)}>
            <div className="bg-white/20 w-16 h-16 rounded-2xl flex items-center justify-center mb-5"><Rocket size={32} /></div>
            <h3 className="text-xl font-bold mb-3">AI 커리어 나침반</h3>
            <p className="text-emerald-50 text-sm leading-relaxed mb-8">내 성향을 분석해 <br /> 최적의 직무를 추천해드려요.</p>
            <button className="bg-white text-emerald-600 px-8 py-3 rounded-xl font-bold flex items-center gap-2">진단 시작하기 <ArrowUpRight size={16} /></button>
          </div>

          {/* 3. ⭐ [Hexagon Stat + Quiz] 나의 개발 스탯 */}
          <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-3xl p-6 shadow-xl text-white flex flex-col justify-between h-[340px]">
            <div className="flex justify-between items-start mb-2"><div><h3 className="text-xl font-bold flex items-center gap-2"><Map size={20} /> 나의 개발 스탯</h3><p className="text-indigo-200 text-xs mt-1">밸런스 있게 성장하고 있나요?</p></div><span className="bg-white/20 text-xs px-2 py-1 rounded-lg font-bold">Lv.{userStats.level}</span></div>
            <div className="flex-1 w-full min-h-[180px] -ml-4"> 
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={skillStats}>
                  <PolarGrid stroke="rgba(255,255,255,0.2)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'white', fontSize: 10, fontWeight: 'bold' }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar name="My Skills" dataKey="A" stroke="#F472B6" strokeWidth={3} fill="#F472B6" fillOpacity={0.4} />
                  <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} itemStyle={{ color: '#6366F1', fontWeight: 'bold' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <button onClick={() => setIsQuizModalOpen(true)} className="bg-white text-indigo-600 px-4 py-3 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-indigo-50 transition-colors mt-2">스탯 분석하기 <ArrowUpRight size={16} /></button>
          </div>
        </div>

        {/* ======================= 스킬트리 (탭 기능 추가) ======================= */}
        <div className="bg-white rounded-3xl p-8 shadow-sm border border-slate-100 min-h-[400px]">
          <div className="flex flex-col sm:flex-row justify-between items-center mb-8 gap-4">
            <h2 className="text-xl font-bold flex items-center gap-2">🗺️ Explorer Map</h2>
            
            {/* ⭐ 탭 버튼: 나의 로드맵(Personal) vs 정석 로드맵(Public) */}
            <div className="flex bg-slate-100 p-1 rounded-lg">
                <button 
                    onClick={() => {
                        if (!userId) {
                            if(window.confirm("🔒 개인 로드맵은 로그인이 필요합니다.\n체험판(AI 진단)을 진행하시겠습니까?")) {
                                setIsAIModalOpen(true);
                            }
                        } else {
                            setActiveMap("personal");
                        }
                    }}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-md transition-all ${activeMap === "personal" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                >
                    <User size={16} /> 나의 로드맵
                </button>
                <button 
                    onClick={() => setActiveMap("public")}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-md transition-all ${activeMap === "public" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
                >
                    <BookOpen size={16} /> 웹 개발 정석
                </button>
            </div>

            <div className="flex items-center gap-2">
              {isPreviewMode && <span className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-xs font-bold">👀 체험판 모드</span>}
              <div className="text-xs font-bold bg-slate-100 px-3 py-1.5 rounded">Total Progress: <span className="text-indigo-600">{Math.round((completedCount / totalCount) * 100)}%</span></div>
            </div>
          </div>

          <div className="bg-slate-50/50 rounded-2xl border border-slate-100 p-8 flex justify-center min-h-[300px] relative">
            <div className="absolute top-4 left-4 text-[10px] font-bold text-slate-300 uppercase">
              {roadmap.track_title || "DevHub Map"}
              {activeMap === "personal" && viewType !== "ALL" && <span className="ml-2 text-indigo-500 font-bold">[{viewType} Focus]</span>}
            </div>
            
            <SkillTree nodes={roadmap.nodes} onNodeClick={handleNodeClick} viewType={viewType} />
          </div>
        </div>

        {/* ======================= 오늘의 퀘스트 ======================= */}
        <div id="today-quest-section" className="scroll-mt-10">
            <TodayQuests quests={activeQuests} onCompleteQuest={handleQuestComplete} onInternalLink={handleInternalLink} />
        </div>
      </div>

      {/* ======================= 모달들 ======================= */}
      <AICompassModal isOpen={isAIModalOpen} onClose={() => setIsAIModalOpen(false)} onPreview={handlePreviewTrack} />
      <QuizModal isOpen={isQuizModalOpen} onClose={() => setIsQuizModalOpen(false)} onFinish={handleQuizFinish} />
      <QuestModal node={selectedNode} isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onCompleteQuest={handleQuestComplete} onInternalLink={handleInternalLink} />
    </div>
  );
}

// // src/pages/CareerDashboard.jsx
// import React, { useEffect, useState, useCallback } from "react";
// import CareerChart from "../components/career/CareerChart";
// import JobCard from "../components/career/JobCard";
// import LearnMaterialCard from "../components/career/LearnMaterialCard";

// import {
//   fetchCareerDashboard,
//   fetchLearningRecommend,
// } from "../api/careerAPI";

// // ✅ userAPI에서 getInterests 추가 (관심사 조회용)
// import { getInterests } from "../api/userAPI"; 

// export default function CareerDashboard() {
//   const [careerData, setCareerData] = useState(null);
//   const [learningList, setLearningList] = useState([]);
//   const [loading, setLoading] = useState(true);
  
//   // 차트 모드: 'frontend' 또는 'backend'
//   const [chartMode, setChartMode] = useState("frontend"); 

//   // 페이지당 6개
//   const [page, setPage] = useState(1);
//   const pageSize = 6;

//   // 🛠️ [Helper] 토큰에서 User ID 추출하는 함수
//   const getUserIdFromToken = () => {
//     const token = localStorage.getItem("token");
//     if (!token) return null;
//     try {
//       // JWT 디코딩 (base64)
//       const base64Url = token.split('.')[1];
//       const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
//       const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
//           return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
//       }).join(''));
      
//       const payload = JSON.parse(jsonPayload);
//       return payload.id || payload.user_id || payload.sub; 
//     } catch (e) {
//       console.error("Token decode error:", e);
//       return null;
//     }
//   };

//   // ✅ [수정] 데이터 로드 함수를 useCallback으로 감싸서 재사용 가능하게 변경
//   const loadData = useCallback(async () => {
//     try {
//       setLoading(true);
//       const userId = getUserIdFromToken();

//       // 1. 데이터 병렬 요청
//       const promises = [
//           fetchCareerDashboard("/dashboard"),
//           fetchLearningRecommend().catch(() => ({ learning: [] })),
//       ];

//       if (userId) {
//           promises.push(getInterests(userId).catch(() => null));
//       }

//       const [dashboardData, learningData, interestData] = await Promise.all(promises);

//       // 2. 데이터 병합 로직
//       let finalMode = dashboardData.mode;
//       let finalUserSkills = dashboardData.user_skills || [];

//       // DB에서 가져온 유저 데이터가 있다면 분석 시작
//       if (interestData) {
//           const dbTechStack = interestData.tech_stack || [];
//           const dbInterests = interestData.interest_topics || interestData.interests || [];
          
//           // 기술 스택이나 관심사가 하나라도 있으면 Personal 모드 강제 전환
//           if (dbTechStack.length > 0 || dbInterests.length > 0) {
//               finalMode = "personalized";
              
//               if (finalUserSkills.length === 0) {
//                   finalUserSkills = dbTechStack.length > 0 ? dbTechStack : dbInterests;
//               }
//           }
//       }

//       // 병합된 데이터 적용
//       setCareerData({
//           ...dashboardData,
//           mode: finalMode,
//           user_skills: finalUserSkills
//       });

//       // 학습 데이터 적용
//       setLearningList(Array.isArray(learningData) ? learningData : learningData.learning || []);

//     } catch (error) {
//       console.error("데이터 로딩 실패:", error);
//     } finally {
//       setLoading(false);
//     }
//   }, []); // 의존성 배열 비움 (항상 동일한 함수 참조 유지)

//   // ✅ [수정] useEffect에서 초기 로드 및 이벤트 리스너 등록
//   useEffect(() => {
//     // 1. 처음 마운트 시 데이터 로드
//     loadData();

//     // 2. 로그인/로그아웃 이벤트("auth-change") 감지 -> 데이터 새로고침
//     const handleAuthChange = () => {
//         console.log("🔔 로그인 상태 변경 감지! 대시보드를 새로고침합니다.");
//         loadData();
//     };

//     window.addEventListener("auth-change", handleAuthChange);

//     // 3. 컴포넌트 언마운트 시 리스너 제거 (메모리 누수 방지)
//     return () => {
//         window.removeEventListener("auth-change", handleAuthChange);
//     };
//   }, [loadData]);


//   if (loading || !careerData) {
//     return (
//         <div className="min-h-screen flex items-center justify-center bg-gray-50">
//             <p className="text-gray-400 animate-pulse">데이터를 분석 중입니다...</p>
//         </div>
//     );
//   }

//   // ✅ 데이터 해체
//   const { 
//       mode, 
//       jobs, 
//       frontend_trends = [], 
//       backend_trends = [], 
//       user_skills 
//   } = careerData;

//   // ✅ 차트 데이터 스위칭
//   const currentTrends = chartMode === "frontend" ? frontend_trends : backend_trends;

//   // 차트 컴포넌트로 보낼 데이터 가공
//   const trendChartData = currentTrends.map((t) => ({
//     name: t.skill,
//     value: t.count,
//   }));

//   // 공고 페이지네이션 처리
//   const totalJobs = jobs?.length || 0;
//   const totalPages = Math.ceil(totalJobs / pageSize);
//   const start = (page - 1) * pageSize;
//   const paginatedJobs = (jobs || []).slice(start, start + pageSize);

//   // 요약 통계 계산
//   const calculateTopSkill = () => {
//     if (!jobs || jobs.length === 0) return "-";
//     const tagCount = {};
//     jobs.forEach(job => {
//       if (job.tags) {
//         job.tags.forEach(tag => tagCount[tag] = (tagCount[tag] || 0) + 1);
//       }
//     });
//     const sortedTags = Object.entries(tagCount).sort((a, b) => b[1] - a[1]);
//     return sortedTags.length > 0 ? sortedTags[0][0] : "-";
//   };

//   const topSkill = calculateTopSkill();
//   const newThisWeek = Math.floor(totalJobs * 0.2); 

//   return (
//     <div className="min-h-screen bg-[#F8F9FA] p-8 font-sans text-gray-800">
//       <div className="max-w-6xl mx-auto space-y-8">
        
//         {/* 1. 헤더 */}
//         <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
//           <div>
//             <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
//                 {mode === "personalized" ? "💼 맞춤 채용 추천" : "📈 전체 채용 트렌드"}
//                 {mode === "personalized" && (
//                     <span className="bg-indigo-100 text-indigo-700 text-xs px-2 py-1 rounded-full font-medium">
//                         Personalized
//                     </span>
//                 )}
//             </h1>
//             <p className="text-gray-500 text-sm mt-2">
//                 {mode === "personalized" 
//                     ? "선택하신 기술 스택을 기반으로 분석된 공고입니다." 
//                     : "현재 시장에서 가장 인기 있는 채용 공고들입니다."}
//             </p>
//           </div>

//           {mode === "personalized" && user_skills && user_skills.length > 0 && (
//               <div className="flex flex-wrap gap-2 justify-end max-w-md">
//                   {user_skills.map((skill, idx) => (
//                       <span key={idx} className="px-3 py-1 bg-white border border-indigo-200 text-indigo-600 text-xs rounded-full font-semibold shadow-sm">
//                           #{skill}
//                       </span>
//                   ))}
//               </div>
//           )}
//         </header>

//         {/* 2. 상단: 기술 트렌드 차트 (토글 적용) */}
//         <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
//           <div className="flex justify-between items-center mb-6">
//             <h2 className="text-lg font-bold flex items-center gap-2">
//               📊 분야별 필수 기술 순위
//             </h2>
            
//             <div className="flex items-center gap-3">
//                 {/* ✅ Frontend / Backend 토글 버튼 */}
//                 <div className="bg-gray-100 p-1 rounded-lg flex text-xs font-medium">
//                     <button
//                         onClick={() => setChartMode("frontend")}
//                         className={`px-3 py-1.5 rounded-md transition-all ${
//                             chartMode === "frontend" 
//                             ? "bg-white text-indigo-600 shadow-sm font-bold" 
//                             : "text-gray-500 hover:text-gray-700"
//                         }`}
//                     >
//                         Frontend
//                     </button>
//                     <button
//                         onClick={() => setChartMode("backend")}
//                         className={`px-3 py-1.5 rounded-md transition-all ${
//                             chartMode === "backend" 
//                             ? "bg-white text-indigo-600 shadow-sm font-bold" 
//                             : "text-gray-500 hover:text-gray-700"
//                         }`}
//                     >
//                         Backend
//                     </button>
//                 </div>
                
//                 <span className="text-xs text-gray-500 bg-gray-50 px-2.5 py-1 rounded-md border border-gray-200">
//                     최근 8주 기준
//                 </span>
//             </div>
//           </div>
          
//           <div className="w-full h-[320px]">
//              {trendChartData.length > 0 ? (
//                  <CareerChart data={trendChartData} />
//              ) : (
//                  <div className="h-full flex items-center justify-center text-gray-400 text-sm">
//                      분석할 데이터가 충분하지 않습니다.
//                  </div>
//              )}
//           </div>
//         </section>

//         {/* 3. 메인 그리드 */}
//         <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
//           {/* 👈 왼쪽: 채용 공고 리스트 */}
//           <div className="lg:col-span-2 space-y-6">
//             <div className="flex justify-between items-end px-1">
//                   <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
//                     {mode === "personalized" ? "🎯 추천 공고" : "💼 최신 공고"}
//                   </h2>
//                   <span className="text-xs text-gray-500">
//                     총 {totalJobs}건 중 {page}페이지
//                   </span>
//             </div>
            
//             <div className="space-y-4">
//               {paginatedJobs.length > 0 ? (
//                 paginatedJobs.map((job, index) => (
//                   <JobCard key={job.id || index} job={job} />
//                 ))
//               ) : (
//                 <div className="text-center py-16 bg-white rounded-2xl border border-gray-100 text-gray-400">
//                   <p className="mb-2">조건에 딱 맞는 공고를 찾지 못했습니다. 😢</p>
//                   <p className="text-sm">관심사를 조금 더 넓게 설정해보세요.</p>
//                 </div>
//               )}
//             </div>

//             {/* 페이지네이션 */}
//             {totalPages > 1 && (
//                 <div className="flex justify-center gap-2 mt-4">
//                   <button
//                     onClick={() => setPage((p) => Math.max(p - 1, 1))}
//                     disabled={page === 1}
//                     className="px-3 py-1.5 text-xs font-medium rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-50 transition-colors"
//                   >
//                     Previous
//                   </button>
//                   <span className="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white rounded-lg border">
//                     {page} / {totalPages}
//                   </span>
//                   <button
//                     onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
//                     disabled={page === totalPages}
//                     className="px-3 py-1.5 text-xs font-medium rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-50 transition-colors"
//                   >
//                     Next
//                   </button>
//                 </div>
//               )}
//           </div>

//           {/* 👉 오른쪽: 통계 + 학습 추천 */}
//           <div className="lg:col-span-1 space-y-8 sticky top-6">
            
//             {/* 요약 통계 */}
//             <div>
//                 <h3 className="font-bold text-gray-800 mb-4 px-1">요약 통계</h3>
//                 <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-4">
//                     <div className="flex justify-between items-center">
//                         <span className="text-sm text-gray-500">검색된 공고</span>
//                         <span className="font-bold text-gray-900 text-lg">{totalJobs}</span>
//                     </div>
//                     <div className="flex justify-between items-center">
//                         <span className="text-sm text-gray-500">신규 업데이트</span>
//                         <span className="font-bold text-green-600">+{newThisWeek}</span>
//                     </div>
//                     <div className="flex justify-between items-center pt-2 border-t border-gray-100">
//                         <span className="text-sm text-gray-500">추천 공고 TOP 스킬</span>
//                         <span className="font-bold text-blue-600">{topSkill}</span>
//                     </div>
//                 </div>
//             </div>

//             {/* 학습 추천 */}
//             <div>
//                 <div className="flex items-center gap-2 mb-4 px-1">
//                     <h3 className="font-bold text-gray-800">📚 맞춤 학습 추천</h3>
//                 </div>
                
//                 <div className="grid grid-cols-1 gap-4">
//                     {learningList.length > 0 ? (
//                         learningList.slice(0, 5).map((item, i) => (
//                         <LearnMaterialCard key={i} item={item} />
//                         ))
//                     ) : (
//                         <p className="text-gray-400 text-xs text-center py-4 bg-white rounded-xl border border-gray-100">
//                         학습 추천 데이터를 불러오는 중...
//                         </p>
//                     )}
//                 </div>
//             </div>

//           </div>
//         </div>

//       </div>
//     </div>
//   );
// }