// src/components/roadmap/TodayQuests.jsx

import React from "react";
import { Play, CheckCircle2, BookOpen, Rocket, ExternalLink } from "lucide-react";

export default function TodayQuests({ quests, onCompleteQuest, onInternalLink }) {
  if (!quests || quests.length === 0) {
    return (
      <div className="p-6 bg-white rounded-2xl shadow border text-center">
        <p className="text-gray-500 text-sm">오늘 진행할 퀘스트가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl p-6 shadow border space-y-5">
      <h2 className="text-xl font-bold mb-4">🔥 오늘의 퀘스트</h2>

      {quests.map((q) => {
        const isInternal = q.resource_link?.startsWith("internal://");
        const isCompleted = q.completed;

        return (
          <div 
            key={q.quest_id}
            className={`p-4 rounded-xl border transition
              ${isCompleted 
                ? "bg-green-50 border-green-300"
                : "bg-gray-50 border-gray-200"}
            `}
          >
            {/* 제목 + XP */}
            <div className="flex justify-between">
              <div>
                <p className="font-bold text-gray-800">{q.title}</p>
                <p className="text-xs text-gray-500 mt-1">{q.node_label}</p>
              </div>

              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-lg h-fit">
                +{q.xp} XP
              </span>
            </div>

            {/* 설명 */}
            <p className="text-gray-600 text-sm mt-3 leading-relaxed">
              {q.description}
            </p>

            {/* 리소스 버튼 */}
            <button
              onClick={() => {
                if (isInternal) onInternalLink(q.resource_link);
                else window.open(q.resource_link, "_blank");
              }}
              className={`w-full flex justify-between items-center p-3 mt-3 rounded-lg border transition
                ${isInternal 
                  ? "bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
                  : "bg-white border-gray-200 hover:bg-gray-100"}
              `}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-9 h-9 rounded-lg text-white flex justify-center items-center
                    ${isInternal ? "bg-emerald-500" : "bg-slate-800"}
                  `}
                >
                  {isInternal ? <Rocket size={18} /> : <BookOpen size={18} />}
                </div>

                <div>
                  <p className="font-semibold text-sm">
                    {isInternal ? "내부 기능 실행" : "강의 열기"}
                  </p>
                  <p className="text-xs text-gray-500">
                    {isInternal ? "AI Career Compass" : "opentutorials.org 이동"}
                  </p>
                </div>
              </div>

              {isInternal 
                ? <Play size={16} className="text-emerald-600" />
                : <ExternalLink size={16} className="text-gray-500" />
              }
            </button>

            {/* 완료 버튼 */}
            <button
              disabled={isCompleted}
              onClick={() => onCompleteQuest(q)}
              className={`w-full mt-3 py-3 rounded-lg font-bold flex items-center justify-center gap-2
                ${isCompleted
                  ? "bg-green-500 text-white cursor-default"
                  : "bg-blue-600 hover:bg-blue-700 text-white"}
              `}
            >
              {isCompleted ? (
                <>
                  <CheckCircle2 size={18} /> 완료됨
                </>
              ) : (
                <>
                  <Play size={18} /> 학습 완료
                </>
              )}
            </button>
          </div>
        );
      })}
    </div>
  );
}
