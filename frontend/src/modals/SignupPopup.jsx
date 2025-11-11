import React, { useState } from "react";
import { registerUser, checkEmail } from "../api/authAPI";
import PopupLayout from "../components/PopupLayout";

export default function SignupPopup({ onClose, onSwitch }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [emailAvailable, setEmailAvailable] = useState(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  // ✅ 이메일 중복 체크
  const handleCheckEmail = async () => {
    if (!email) return;
    setChecking(true);
    try {
      const exists = await checkEmail(email);
      setEmailAvailable(!exists);
    } catch {
      setEmailAvailable(null);
    } finally {
      setChecking(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess(false);

    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    if (emailAvailable === false) {
      setError("이미 등록된 이메일입니다.");
      return;
    }

    try {
      setLoading(true);
      await registerUser({ username, email, password });
      setSuccess(true);
      setTimeout(() => onSwitch(), 1000);
    } catch (err) {
      setError(err.response?.data?.detail || "회원가입 실패. 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PopupLayout title="Create your account ✨" onClose={onClose}>
      <form onSubmit={handleSignup} className="space-y-5">
        {/* 이름 */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="홍길동"
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
          />
        </div>

        {/* 이메일 */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Email
          </label>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setEmailAvailable(null);
              }}
              onBlur={handleCheckEmail}
              placeholder="example@email.com"
              required
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            {checking ? (
              <span className="text-sm text-gray-500 self-center">확인 중...</span>
            ) : emailAvailable === true ? (
              <span className="text-sm text-emerald-600 self-center">✓ 사용 가능</span>
            ) : emailAvailable === false ? (
              <span className="text-sm text-red-500 self-center">이미 존재</span>
            ) : null}
          </div>
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
            placeholder="8자리 이상 입력"
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
          />
        </div>

        {/* 비밀번호 확인 */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            Confirm Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="비밀번호 확인"
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-emerald-500 outline-none"
          />
        </div>

        {/* 메시지 */}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {success && (
          <p className="text-emerald-600 text-sm font-medium">
            ✅ 회원가입이 완료되었습니다!
          </p>
        )}

        {/* 버튼 */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white py-2 rounded-md transition"
        >
          {loading ? "Signing up..." : "Create Account"}
        </button>
      </form>

      {/* 로그인으로 이동 */}
      <div className="mt-8 text-center text-sm text-gray-500">
        Already have an account?{" "}
        <button
          onClick={onSwitch}
          className="text-emerald-600 font-medium hover:underline"
        >
          Sign In
        </button>
      </div>
    </PopupLayout>
  );
}
