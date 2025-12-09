// src/components/roadmap/SkillTree.jsx
import React, { useEffect } from "react";
import Xarrow, { Xwrapper, useXarrow } from "react-xarrows";
import { Lock, Globe, Database, Server, Code, Layout, GitBranch, Compass, Monitor } from "lucide-react";

// ---------------------------------------------------------
// 1. 디자인 뼈대 데이터 (노드 확장 적용)
// ---------------------------------------------------------
const layoutSkeleton = [
  // === Public (Web) ===
  { id: "WEB-01", label: "Web 개념", icon: "web", layout: { col: 0, row: 1.5 }, prerequisites: [] },
  { id: "WEB-02", label: "HTML", icon: "html", layout: { col: 1, row: 0 }, prerequisites: ["WEB-01"] },
  { id: "WEB-04", label: "JS 기초", icon: "js", layout: { col: 2, row: 0 }, prerequisites: ["WEB-02"] },
  { id: "WEB-03", label: "CSS", icon: "css", layout: { col: 2, row: 1 }, prerequisites: ["WEB-01"] },
  { id: "WEB-06", label: "Backend", icon: "backend", layout: { col: 2, row: 2 }, prerequisites: ["WEB-01"] },
  { id: "WEB-07", label: "DB(MySQL)", icon: "db", layout: { col: 2, row: 3 }, prerequisites: ["WEB-01"] },
  { id: "WEB-05", label: "JS 심화", icon: "js", layout: { col: 3, row: 0 }, prerequisites: ["WEB-04"] },
  { id: "WEB-08", label: "Git / GitHub", icon: "git", layout: { col: 4, row: 1.5 }, prerequisites: ["WEB-05", "WEB-03", "WEB-06", "WEB-07"] },
  { id: "WEB-09", label: "Deploy", icon: "deploy", layout: { col: 5, row: 1.5 }, prerequisites: ["WEB-08"] },
  { id: "WEB-10", label: "Career AI", icon: "career", layout: { col: 6, row: 1.5 }, prerequisites: ["WEB-09"] },

  // === Personal (Life Coding) - FE/BE 4단계 ===
  // 1. 공통
  { id: "LC-01", label: "Web Essentials", icon: "web", layout: { col: 0, row: 1.5 }, prerequisites: [] },
  
  // 2. Frontend Branch
  { id: "LC-FE-01", label: "HTML/CSS", icon: "html", layout: { col: 2, row: 0.5 }, prerequisites: ["LC-01"] },
  { id: "LC-FE-02", label: "JS Core", icon: "js", layout: { col: 3, row: 0.5 }, prerequisites: ["LC-FE-01"] },
  { id: "LC-FE-03", label: "React & UI", icon: "react", layout: { col: 4, row: 0.5 }, prerequisites: ["LC-FE-02"] },
  { id: "LC-FE-04", label: "Next.js/State", icon: "code", layout: { col: 5, row: 0.5 }, prerequisites: ["LC-FE-03"] },

  // 3. Backend Branch
  { id: "LC-BE-01", label: "Server/Linux", icon: "server", layout: { col: 2, row: 2.5 }, prerequisites: ["LC-01"] },
  { id: "LC-BE-02", label: "Lang (Py/Node)", icon: "python", layout: { col: 3, row: 2.5 }, prerequisites: ["LC-BE-01"] },
  { id: "LC-BE-03", label: "Database", icon: "db", layout: { col: 4, row: 2.5 }, prerequisites: ["LC-BE-02"] },
  { id: "LC-BE-04", label: "DevOps/Cloud", icon: "cloud", layout: { col: 5, row: 2.5 }, prerequisites: ["LC-BE-03"] },

  // 4. 심화
  { id: "LC-ADV", label: "Deep Dive", icon: "career", layout: { col: 7, row: 1.5 }, prerequisites: ["LC-FE-04", "LC-BE-04"] },
];

export default function SkillTree({ nodes = [], onNodeClick, viewType = "ALL" }) {
  const updateXarrow = useXarrow(); 

  useEffect(() => {
    const timer = setTimeout(() => { updateXarrow(); }, 100);
    return () => clearTimeout(timer);
  }, [nodes, viewType]);

  // ⭐ [핵심 복구] viewType에 따른 필터링 로직
  const filteredSkeleton = layoutSkeleton.filter(skeleton => {
      const id = skeleton.id;
      
      // Public(WEB)은 항상 표시 (혹은 여기서도 숨길 수 있음)
      if (id.startsWith("WEB-")) return true;

      // Personal 공통 노드는 항상 표시
      if (id === "LC-01" || id === "LC-ADV") return true;

      // Frontend 모드면 Backend 숨김
      if (viewType === "FRONTEND" && id.includes("LC-BE")) return false;

      // Backend 모드면 Frontend 숨김
      if (viewType === "BACKEND" && id.includes("LC-FE")) return false;

      return true; // 기본값: 다 보여줌
  });

  const displayNodes = filteredSkeleton.map(skeleton => {
      const serverNode = (nodes || []).find(n => n.id === skeleton.id);
      if (!serverNode) return null;

      return {
          ...skeleton,
          status: serverNode.status, 
          xp: serverNode.xp,
          db_id: serverNode.db_id,
          quests: serverNode.quests,
          prerequisites: skeleton.prerequisites 
      };
  }).filter(Boolean);

  // ... (아이콘, 스타일 설정 코드는 기존과 동일) ...
  const ICONS = {
    web: <Monitor size={20} />, html: <Layout size={18} />, css: <Layout size={18} />, js: <Code size={18} />,
    backend: <Server size={18} />, db: <Database size={18} />, git: <GitBranch size={18} />,
    deploy: <Server size={18} />, career: <Compass size={18} />, default: <Globe size={18} />,
    react: <Code size={18} />, server: <Server size={18} />, code: <Code size={18} />, python: <Code size={18} />, cloud: <Server size={18} />
  };

  const getNodeStyle = (status) => {
    const base = "w-14 h-14 rounded-full flex items-center justify-center border-[2px] transition-all duration-300 shadow-sm z-20 bg-white";
    switch (status) {
      case "COMPLETED": return `${base} bg-emerald-50 text-emerald-600 border-emerald-400 shadow-emerald-100 ring-2 ring-emerald-50 cursor-pointer hover:scale-110`;
      case "UNLOCKED": return `${base} text-yellow-500 border-yellow-400 shadow-yellow-100 ring-2 ring-yellow-50 cursor-pointer hover:scale-110`;
      case "LOCKED": default: return `${base} text-slate-400 border-slate-200 bg-slate-50 cursor-not-allowed`;
    }
  };

  const X_SPACING = 180;
  const Y_SPACING = 100;
  const maxCol = Math.max(...displayNodes.map(n => n.layout.col), 0);
  const containerWidth = (maxCol + 1) * X_SPACING + 100;
  const BASE_Y = 250; 
  const ROW_OFFSET = 1.5; 

  return (
    <div className="relative w-full h-[500px] bg-slate-50/30 flex flex-col border rounded-xl overflow-hidden">
      <div className="relative w-full h-full overflow-auto cursor-grab active:cursor-grabbing">
        <div className="relative h-full mx-10" style={{ width: `${containerWidth}px` }}>
          <Xwrapper>
            {displayNodes.map((node) => {
              const leftPos = node.layout.col * X_SPACING + 50; 
              const topPos = (node.layout.row - ROW_OFFSET) * Y_SPACING + BASE_Y;

              return (
                <div
                  key={node.id}
                  id={`node-${node.id}`}
                  className="absolute flex flex-col items-center transform -translate-y-1/2 -translate-x-1/2 transition-all duration-500"
                  style={{ left: leftPos, top: topPos }}
                  onClick={() => { if (node.status !== "LOCKED") onNodeClick(node); }}
                >
                  <div className={getNodeStyle(node.status)}>
                    {node.status === "LOCKED" ? <Lock size={16} /> : (ICONS[node.icon] || ICONS.default)}
                  </div>
                  <div className="mt-2 text-center w-24">
                    <p className={`text-xs font-bold leading-tight ${node.status === 'LOCKED' ? 'text-slate-400' : 'text-slate-700'}`}>
                      {node.label}
                    </p>
                    {node.status !== 'LOCKED' && (
                        <span className="text-[9px] bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded-full mt-1 inline-block">
                            +{node.xp} XP
                        </span>
                    )}
                  </div>
                </div>
              );
            })}
            {displayNodes.map((node) =>
              (node.prerequisites || []).map((preId) => {
                 // 화면에 있는 노드끼리만 연결
                 if (!displayNodes.find(n => n.id === preId)) return null;
                 return (
                    <Xarrow
                      key={`${preId}-${node.id}`}
                      start={`node-${preId}`}
                      end={`node-${node.id}`}
                      startAnchor="right"
                      endAnchor="left"
                      color="#CBD5E1"
                      strokeWidth={1.5}
                      path="smooth"
                      curveness={0.4}
                      headSize={3}
                      zIndex={0}
                    />
                 );
              })
            )}
          </Xwrapper>
        </div>
      </div>
    </div>
  );
}