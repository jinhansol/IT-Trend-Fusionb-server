import React, { useState, useEffect } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import LoginPopup from "../modals/LoginPopup";
import SignupPopup from "../modals/SignupPopup";
import InterestPopup from "../modals/InterestPopup";

export default function HeaderNav() {
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const [showInterest, setShowInterest] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // ✅ 로그인 상태 유지
  useEffect(() => {
    const savedUser = localStorage.getItem("user");
    if (savedUser) setUser(JSON.parse(savedUser));
  }, []);

  // ✅ 첫 로그인 시 관심사 팝업 자동 표시
  useEffect(() => {
    const isFirstLogin = localStorage.getItem("firstLogin");
    if (isFirstLogin === "true") {
      setShowInterest(true);
      localStorage.setItem("firstLogin", "false");
    }
  }, [user]);

  // ✅ 첫 로그인 후 main_focus 페이지 자동 이동
  useEffect(() => {
    if (user?.main_focus) {
      const focus = (user.main_focus || "").toLowerCase();
      const currentPath = location.pathname;

      // 현재 경로가 이미 해당 focus 페이지면 이동 X
      if (focus === "dev" && currentPath !== "/dev") navigate("/dev");
      else if (focus === "career" && currentPath !== "/career") navigate("/career");
      else if ((focus === "insight" || focus === "ai insight") && currentPath !== "/insight")
        navigate("/insight");
    }
  }, [user, navigate, location]);

  // ✅ 로그아웃
  const handleLogout = () => {
    if (window.confirm("정말 로그아웃 하시겠어요? 👋")) {
      localStorage.removeItem("user");
      localStorage.removeItem("firstLogin");
      setUser(null);
      alert("로그아웃 되었습니다.");
      navigate("/");
    }
  };

  const navItems = [
    { name: "Career", path: "/career" },
    { name: "Dev", path: "/dev" },
    { name: "AI Insight", path: "/insight" },
  ];

  // ✅ 메뉴 표시만 제한 (페이지 접근은 허용)
  const filteredNavItems = navItems.filter((item) => {
    if (!user?.main_focus) return true;

    const focus = (user.main_focus || "").toLowerCase();

    if (focus === "career") return item.name !== "Dev";
    if (focus === "dev") return item.name !== "Career";
    if (focus === "insight" || focus === "ai insight")
      return item.name === "AI Insight";

    return true;
  });

  return (
    <>
      {/* 🧭 헤더 */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto flex justify-between items-center px-8 py-4">
          
          {/* 로고 */}
          <Link to="/" className="text-xl font-bold">
            <span className="text-emerald-600">Dev</span>
            <span className="text-gray-900">Hub</span>
          </Link>

          {/* 중앙 메뉴 */}
          <div className="hidden md:flex gap-8 text-gray-600">
            {filteredNavItems.map((item) => (
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

          {/* 우측 */}
          <div className="flex items-center gap-4 text-sm text-gray-700">
            {!user ? (
              <>
                <button
                  onClick={() => setShowLogin(true)}
                  className="hover:text-emerald-600 font-medium transition"
                >
                  Login
                </button>
                <button
                  onClick={() => setShowSignup(true)}
                  className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium transition"
                >
                  Sign Up
                </button>
              </>
            ) : (
              <div className="flex items-center gap-3">
                {/* 이름 클릭 → 관심사 팝업 */}
                <div
                  onClick={() => setShowInterest(true)}
                  className="cursor-pointer hover:text-emerald-600 transition select-none"
                  title="관심분야 수정"
                >
                  Welcome,&nbsp;
                  <span className="font-semibold text-emerald-600">
                    {user.username}
                  </span>{" "}
                  👋
                </div>

                <button
                  onClick={handleLogout}
                  className="border border-gray-300 px-3 py-1.5 rounded-md text-gray-600 hover:bg-gray-100 transition text-xs"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* 팝업 */}
      {showLogin && (
        <LoginPopup
          onClose={() => setShowLogin(false)}
          onSwitch={() => {
            setShowLogin(false);
            setShowSignup(true);
          }}
          setUser={(userData) => {
            setUser(userData);
            if (!localStorage.getItem("firstLogin")) {
              localStorage.setItem("firstLogin", "true");
            }
            localStorage.setItem("user", JSON.stringify(userData));
          }}
        />
      )}

      {showSignup && (
        <SignupPopup
          onClose={() => setShowSignup(false)}
          onSwitch={() => {
            setShowSignup(false);
            setShowLogin(true);
          }}
          setUser={(userData) => {
            setUser(userData);
            localStorage.setItem("firstLogin", "true");
            localStorage.setItem("user", JSON.stringify(userData));
          }}
        />
      )}

      {showInterest && (
        <InterestPopup
          onClose={() => setShowInterest(false)}
          user={user}
          setUser={setUser}
        />
      )}
    </>
  );
}
