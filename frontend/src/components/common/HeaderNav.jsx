import React, { useState } from "react";
import { Link, NavLink } from "react-router-dom";

// ✅ 경로 수정: 한 단계 더 위로 올라가야 함 (../ -> ../../)
import LoginPopup from "../../modals/LoginPopup";
import SignupPopup from "../../modals/SignupPopup";
import { useAuth } from "../../auth/useAuth";

// DevHub 2.0: the login state comes from AuthProvider (server session), not localStorage.
// The interest popup is hidden until personalization is rebuilt (Phase 6); it still
// talks to the legacy backend and legacy user ids.

const navItems = [
  { name: "Home", path: "/" },
  { name: "Career", path: "/career" },
  { name: "Dev", path: "/dev" },
];

export default function HeaderNav() {
  const { status, user, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);
  const [showSignup, setShowSignup] = useState(false);

  const handleLogout = async () => {
    await logout();
    // Reload so Career/Dev pages drop any personal data they still hold.
    window.location.href = "/";
  };

  return (
    <>
      <nav className="sticky top-0 z-50 bg-white border-b">
        <div className="max-w-7xl mx-auto flex justify-between items-center px-8 py-4">

          <Link to="/" className="text-xl font-bold">
            <span className="text-emerald-600">Dev</span>Hub
          </Link>

          <div className="hidden md:flex gap-8">
            {navItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                className="hover:text-emerald-600"
              >
                {item.name}
              </NavLink>
            ))}
          </div>

          <div className="flex items-center gap-4 text-sm min-h-[36px]">
            {status === "anonymous" && (
              <>
                <button onClick={() => setShowLogin(true)}>Login</button>
                <button
                  onClick={() => setShowSignup(true)}
                  className="bg-emerald-500 text-white px-4 py-2 rounded-lg"
                >
                  Sign Up
                </button>
              </>
            )}
            {status === "authenticated" && (
              <>
                <span>
                  Welcome, <strong>{user.display_name}</strong> 👋
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
        />
      )}

      {showSignup && (
        <SignupPopup
          onClose={() => setShowSignup(false)}
          onSwitch={() => {
            setShowSignup(false);
            setShowLogin(true);
          }}
        />
      )}
    </>
  );
}
