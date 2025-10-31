import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function Detail() {
  const navigate = useNavigate();
  const { state } = useLocation();

  // ✅ 데이터 유효성 확인
  if (!state) {
    return (
      <div className="flex flex-col justify-center items-center h-screen bg-gray-50">
        <h1 className="text-2xl font-bold text-gray-600 mb-2">⚠️ 채용 정보를 불러올 수 없습니다.</h1>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          ⬅ 이전으로 돌아가기
        </button>
      </div>
    );
  }

  const { title, company, info, description } = state;

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 flex flex-col items-center">
      <div className="bg-white shadow-lg rounded-2xl p-8 max-w-3xl w-full">
        {/* 상단 영역 */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center border-b pb-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-blue-600">{title}</h1>
            <p className="text-gray-700 text-lg mt-2">{company}</p>
            <p className="text-sm text-gray-500 mt-1">{info}</p>
          </div>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 md:mt-0 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition"
          >
            ⬅ 목록으로
          </button>
        </div>

        {/* 채용 상세 설명 */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">📄 모집 요강</h2>
          <p className="text-gray-700 leading-relaxed whitespace-pre-line">
            {description ||
              "해당 직무의 상세 설명이 제공되지 않았습니다. AI 분석 기반 데이터에서 추출된 정보입니다."}
          </p>
        </section>

        {/* 주요 요구 기술 */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">💡 주요 기술 스택</h2>
          <div className="flex flex-wrap gap-2">
            {["Python", "React", "TypeScript", "Node.js", "AI"].map((tech, i) => (
              <span
                key={i}
                className="bg-indigo-100 text-indigo-600 px-3 py-1 rounded-full text-sm font-medium"
              >
                {tech}
              </span>
            ))}
          </div>
        </section>

        {/* 기업 정보 */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-3">🏢 기업 정보</h2>
          <ul className="text-gray-700 space-y-1 text-sm">
            <li>📍 위치: 서울특별시 강남구 테헤란로 000</li>
            <li>👥 직원 수: 약 200명</li>
            <li>🌐 홈페이지: <a href="#" className="text-blue-500 hover:underline">www.company.co.kr</a></li>
            <li>💼 업종: IT / 소프트웨어 개발</li>
          </ul>
        </section>

        {/* 지원 버튼 */}
        <div className="text-center mt-10">
          <button
            onClick={() => alert("지원 페이지로 이동합니다 (시뮬레이션).")}
            className="bg-indigo-500 text-white px-6 py-3 rounded-lg hover:bg-indigo-600 transition shadow"
          >
            ✉️ 지원하러 가기
          </button>
        </div>
      </div>

      {/* 하단 네비게이션 */}
      <div className="flex gap-4 mt-6">
        <button
          onClick={() => navigate("/career")}
          className="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300 transition"
        >
          ← 커리어 대시보드
        </button>
        <button
          onClick={() => navigate("/")}
          className="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300 transition"
        >
          🏠 홈으로
        </button>
      </div>
    </div>
  );
}
