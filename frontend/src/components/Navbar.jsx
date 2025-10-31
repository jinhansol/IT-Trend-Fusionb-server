import React from "react";
import { Link } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="flex justify-between items-center px-6 py-3 bg-white shadow-sm">
      {/* 로고 클릭 시 홈으로 이동 */}
      <Link
        to="/"
        className="text-xl font-bold"
      >
        <span className="text-green-600">Dev</span>
        <span className="text-gray-900">Hub</span>
      </Link>

      {/* 네비게이션 메뉴 */}
      <div className="flex gap-6 text-sm text-gray-600">
        <Link
          to="/career"
          className="hover:text-green-600 transition-colors"
        >
          Career
        </Link>
        <Link
          to="/dev"
          className="hover:text-green-600 transition-colors"
        >
          Dev
        </Link>
        <Link
          to="/ai-insight"
          className="hover:text-green-600 transition-colors"
        >
          AI Insight
        </Link>
      </div>

      {/* 우측 사용자 정보 */}
      <div className="text-sm text-gray-700">
        Welcome, <span className="font-semibold text-gray-900">Chaeun</span> 👋
      </div>
    </nav>
  );
}
