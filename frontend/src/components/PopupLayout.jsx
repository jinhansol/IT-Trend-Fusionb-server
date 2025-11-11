import React from "react";

export default function PopupLayout({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex justify-center items-center z-50">
      {/* 팝업 컨테이너 */}
      <div className="bg-white w-[600px] max-h-[90vh] rounded-2xl shadow-2xl p-10 relative animate-fadeIn overflow-y-auto">
        {/* 닫기 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>

        {/* 타이틀 */}
        {title && (
          <div className="mb-8 text-center">
            <h2 className="text-2xl font-semibold text-gray-900">{title}</h2>
          </div>
        )}

        {/* 본문 콘텐츠 (각 팝업에서 전달) */}
        {children}
      </div>
    </div>
  );
}
