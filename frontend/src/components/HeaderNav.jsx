import React, { useState, useEffect } from "react";
import { Link, NavLink } from "react-router-dom";
import LoginPopup from "../modals/LoginPopup";
import SignupPopup from "../modals/SignupPopup";
import InterestPopup from "../modals/InterestPopup";

export default function HeaderNav() {
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [showSignup, setShowSignup] = useState(false);
  const [showInterest, setShowInterest] = useState(false);

  // 로그인 상태 유지
  useEffect(() => {
    const savedUser = localStorage.getItem("user");
    if (savedUser) setUser(JSON.parse(savedUser));
  }, []);

  // 첫 로그인 → 관심사 팝업 자동 표시
  useEffect(() => {
    if (!user) return;

    const first = localStorage.getItem("firstLogin");

    if (first === "true") {
      setShowInterest(true);
      localStorage.setItem("firstLogin", "false");
    }
  }, [user]);

  // 로그아웃
  const handleLogout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("firstLogin");
    setUser(null);
  };

  const navItems = [
    { name: "Home", path: "/" },
    { name: "Career", path: "/career" },
    { name: "Dev", path: "/dev" },
    { name: "AI Insight", path: "/insight" },
  ];

  const filteredNavItems = navItems.filter((item) => {
    if (!user?.main_focus) return true;

    const focus = user.main_focus.toLowerCase();

    if (focus === "career") return item.name !== "Dev";
    if (focus === "dev") return item.name !== "Career";
    if (focus === "insight") return item.name === "AI Insight" || item.name === "Home";

    return true;
  });

  return (
    <>
      <nav className="sticky top-0 z-50 bg-white border-b">
        <div className="max-w-7xl mx-auto flex justify-between items-center px-8 py-4">

          <Link to="/" className="text-xl font-bold">
            <span className="text-emerald-600">Dev</span>Hub
          </Link>

          <div className="hidden md:flex gap-8">
            {filteredNavItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                className="hover:text-emerald-600"
              >
                {item.name}
              </NavLink>
            ))}
          </div>

          <div className="flex items-center gap-4 text-sm">
            {!user ? (
              <>
                <button onClick={() => setShowLogin(true)}>Login</button>
                <button
                  onClick={() => setShowSignup(true)}
                  className="bg-emerald-500 text-white px-4 py-2 rounded-lg"
                >
                  Sign Up
                </button>
              </>
            ) : (
              <>
                <span className="cursor-pointer" onClick={() => setShowInterest(true)}>
                  Welcome, <strong>{user.username}</strong> 👋
                </span>

                <button className="border px-3 py-1.5 rounded-md" onClick={handleLogout}>
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* 팝업들 */}
      {showLogin && (
        <LoginPopup
          onClose={() => setShowLogin(false)}
          onSwitch={() => {
            setShowLogin(false);
            setShowSignup(true);
          }}
          setUser={(u) => {
            setUser(u);
            localStorage.setItem("user", JSON.stringify(u));
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
          setUser={(u) => {
            setUser(u);
            localStorage.setItem("user", JSON.stringify(u));
            localStorage.setItem("firstLogin", "true");
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
