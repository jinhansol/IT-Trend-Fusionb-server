import React from "react";
import { NavLink, Link, useLocation } from "react-router-dom";

export default function HeaderNav() {
  const location = useLocation();

  // 네비게이션 항목
  const navItems = [
    { name: "Career", path: "/career" },
    { name: "Dev", path: "/dev" },
    { name: "AI Insight", path: "/insight" },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto flex justify-between items-center px-10 py-4">
        {/* ✅ 로고 클릭 시 홈("/")으로 이동 */}
        <Link
          to="/"
          className="text-xl font-semibold text-gray-900 tracking-tight hover:opacity-80 transition"
        >
          <span className="text-emerald-600">Dev</span>Hub
        </Link>

        {/* ✅ 중앙 메뉴 */}
        <div className="hidden md:flex gap-8 text-gray-600">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `font-medium hover:text-emerald-600 transition-colors ${
                  isActive ? "text-emerald-600 font-semibold" : ""
                }`
              }
            >
              {item.name}
            </NavLink>
          ))}
        </div>

        {/* ✅ 오른쪽 프로필 표시 */}
        <div className="text-gray-700 text-sm md:text-base select-none">
          Welcome,&nbsp;
          <span className="font-semibold">Chaeun 👋</span>
        </div>
      </div>
    </nav>
  );
}
