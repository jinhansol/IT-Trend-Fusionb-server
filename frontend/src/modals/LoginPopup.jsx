import React, { useState } from "react";
import { loginUser } from "../api/authAPI";
import PopupLayout from "../components/PopupLayout";

export default function LoginPopup({ onClose, onSwitch, setUser, onShowInterest }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await loginUser(email, password);

      // ✅ 사용자 정보 및 토큰 저장
      setUser(data.user);
      localStorage.setItem("token", data.access_token);

      // ✅ 팝업 닫기 후 관심분야 설정 팝업 띄우기
      onClose();
      setTimeout(() => {
        onShowInterest?.();
      }, 800);

    } catch (err) {
      setError(err.response?.data?.detail || "로그인 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PopupLayout title="Welcome back ⚡" onClose={onClose}>
      <form onSubmit={handleLogin} className="space-y-5">
        {/* 이메일 */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="example@email.com"
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
          />
        </div>

        {/* 비밀번호 */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
          />
        </div>

        {/* 에러 메시지 */}
        {error && <p className="text-red-500 text-sm">{error}</p>}

        {/* 로그인 버튼 */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-md transition"
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      {/* 회원가입 전환 */}
      <div className="mt-8 text-center text-sm text-gray-500">
        Don’t have an account?{" "}
        <button
          onClick={onSwitch}
          className="text-emerald-600 font-medium hover:underline"
        >
          Sign Up
        </button>
      </div>
    </PopupLayout>
  );
}
