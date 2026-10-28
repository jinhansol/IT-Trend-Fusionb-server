import React, { useState } from "react";
// ✅ 경로 수정: components/common
import PopupLayout from "../components/common/PopupLayout";
import { useAuth } from "../auth/useAuth";
import { authErrorMessage } from "../auth/authErrorMessage";

export default function LoginPopup({ onClose, onSwitch }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login({ email, password });
      onClose();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PopupLayout title="로그인" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">이메일</label>
          <input
            type="email"
            className="w-full border p-2 rounded mt-1"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">비밀번호</label>
          <input
            type="password"
            className="w-full border p-2 rounded mt-1"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-emerald-600 text-white py-2 rounded-lg hover:bg-emerald-700 transition disabled:opacity-60"
        >
          {submitting ? "로그인 중..." : "로그인"}
        </button>

        <p className="text-center text-sm text-gray-600 mt-2">
          계정이 없으신가요?{" "}
          <button type="button" onClick={onSwitch} className="text-emerald-600 font-bold underline">
            회원가입
          </button>
        </p>
      </form>
    </PopupLayout>
  );
}