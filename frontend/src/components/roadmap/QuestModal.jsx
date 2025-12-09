// src/components/roadmap/QuestModal.jsx
import React, { useEffect, useCallback } from "react";
import { X, ExternalLink, Play, BookOpen, Rocket, CheckCircle2 } from "lucide-react";

export default function QuestModal({
  node,
  isOpen,
  onClose,
  onCompleteQuest,
  onInternalLink,
}) {
  // ----------------------------------------------
  // ⭐ 훅은 항상 최상단에서 실행되어야 함 (return null 보다 위!)
  // ----------------------------------------------
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // ----------------------------------------------
  // ⭐ 내부 링크 처리 — useCallback으로 안정화
  // ----------------------------------------------
  const handleResourceClick = useCallback(
    (quest) => {
      const link = quest.resource_link || "";
      const isInternal = link.startsWith("internal://");

      if (isInternal) {
        onInternalLink?.(link);
        return;
      }

      window.open(link, "_blank");
    },
    [onInternalLink]
  );

  // ----------------------------------------------
  // ⭐ 렌더 차단 (훅 아래로 내려야 함)
  // ----------------------------------------------
  if (!isOpen || !node) return null;

  const quests = node.quests || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-xl overflow-hidden relative flex flex-col max-h-[90vh]">

        {/* 닫기 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-black/10 rounded-full hover:bg-black/20 transition z-50"
        >
          <X size={20} className="text-gray-600" />
        </button>

        {/* 헤더 */}
        <div className="w-full px-6 py-6 border-b border-gray-200">
          <h2 className="text-2xl font-extrabold text-gray-900">{node.label}</h2>
          <p className="text-gray-500 text-sm mt-1">총 {quests.length}개의 퀘스트</p>
        </div>

        {/* 퀘스트 목록 */}
        <div className="p-6 overflow-y-auto flex-1 space-y-5">
          {quests.map((q) => {
            const isInternal = q.resource_link?.startsWith("internal://");
            const isCompleted = q.completed;

            return (
              <div
                key={q.quest_id || `${node.node_id}-${q.title}`}
                className={`p-4 rounded-xl border transition 
                  ${isCompleted ? "bg-green-50 border-green-300" : "bg-gray-50 border-gray-200"}
                `}
              >
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-bold text-gray-900">{q.title}</h3>
                  <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-lg">
                    +{q.xp} XP
                  </span>
                </div>

                <p className="text-gray-600 text-sm mb-3 leading-relaxed">{q.description}</p>

                <button
                  onClick={() => handleResourceClick(q)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg border text-left transition
                    ${isInternal
                      ? "bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
                      : "bg-white border-gray-200 hover:bg-gray-100"}
                  `}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center text-white 
                      ${isInternal ? "bg-emerald-500" : "bg-slate-800"}`}
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
                    : <ExternalLink size={16} className="text-gray-400" />}
                </button>

                <button
                  disabled={isCompleted}
                  onClick={() => onCompleteQuest(q)}
                  className={`mt-3 w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 
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

        <div className="border-t bg-white p-4">
          <button
            onClick={onClose}
            className="w-full py-3 rounded-xl font-bold text-gray-600 border border-gray-300 hover:bg-gray-100"
          >
            닫기
          </button>
        </div>

      </div>
    </div>
  );
}
