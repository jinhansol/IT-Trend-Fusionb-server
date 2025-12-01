// src/components/LearnMaterialCard.jsx
import React from "react";
// 아이콘 사용을 위해 lucide-react import (없으면 텍스트로 대체됨)
import { ExternalLink, PlayCircle, BookOpen, GraduationCap } from "lucide-react";

export default function LearnMaterialCard({ item }) {
  // 데이터 호환성 처리
  const tag = item.tag || item.skill || "Skill";
  const title = item.title || `${tag} 배우기`;
  const desc = item.desc || item.reason || "이 기술은 현재 채용 시장에서 가장 수요가 높습니다.";
  
  // 백엔드에서 링크를 주면 쓰고, 없으면 유튜브 검색 기본값
  const link = item.link || `https://www.youtube.com/results?search_query=${tag}+강의`;

  // 링크 종류 판별 (유튜브 URL이면 비디오 아이콘, 아니면 책 아이콘)
  const isVideo = link.includes("youtube");
  const isOfficial = link.includes("docs") || link.includes(".dev") || link.includes(".org");

  return (
    <div className="border border-gray-100 rounded-xl p-4 bg-white shadow-sm hover:shadow-md hover:border-blue-200 transition-all duration-200 group flex flex-col h-full">
      
      {/* 상단: 태그 및 아이콘 */}
      <div className="flex justify-between items-start mb-2">
        <span className="text-xs font-bold bg-indigo-50 text-indigo-600 px-2.5 py-1 rounded-md group-hover:bg-indigo-100 transition-colors">
          {tag}
        </span>
        
        {/* 아이콘: 비디오 vs 문서 vs 일반 */}
        <div className="text-gray-400 group-hover:text-blue-500 transition-colors">
            {isVideo ? <PlayCircle size={18} /> : 
             isOfficial ? <BookOpen size={18} /> : 
             <GraduationCap size={18} />}
        </div>
      </div>

      {/* 제목 */}
      <h3 className="font-bold text-gray-800 text-sm mb-1 line-clamp-1">
        {title}
      </h3>

      {/* 설명 (최대 2줄) */}
      <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed flex-grow">
        {desc}
      </p>

      {/* 하단 버튼 */}
      <a
        href={link}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 w-full py-2 flex items-center justify-center gap-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 active:bg-blue-800 transition-colors shadow-sm"
      >
        {isVideo ? "무료 강의 보기" : "공식 문서 읽기"}
        <ExternalLink size={12} className="opacity-70" />
      </a>
    </div>
  );
}