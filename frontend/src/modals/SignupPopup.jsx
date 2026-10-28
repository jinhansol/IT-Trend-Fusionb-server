import React, { useState } from "react";
// ✅ 경로 수정: components/common
import PopupLayout from "../components/common/PopupLayout";
import { useAuth } from "../auth/useAuth";
import { authErrorMessage } from "../auth/authErrorMessage";

export default function SignupPopup({ onClose, onSwitch }) {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    displayName: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      // 가입하면 바로 로그인 상태가 됩니다 (서버가 토큰을 발급).
      await register(formData);
      onClose();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PopupLayout title="회원가입" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700">이메일</label>
          <input
            name="email"
            type="email"
            className="w-full border p-2 rounded mt-1"
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">비밀번호</label>
          <input
            name="password"
            type="password"
            className="w-full border p-2 rounded mt-1"
            onChange={handleChange}
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            required
          />
          <p className="text-xs text-gray-500 mt-1">8자 이상</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">이름 (닉네임)</label>
          <input
            name="displayName"
            type="text"
            className="w-full border p-2 rounded mt-1"
            onChange={handleChange}
            maxLength={50}
            required
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition disabled:opacity-60"
        >
          {submitting ? "가입 중..." : "가입하기"}
        </button>

        <p className="text-center text-sm text-gray-600 mt-2">
          이미 계정이 있으신가요?{" "}
          <button type="button" onClick={onSwitch} className="text-blue-600 font-bold underline">
            로그인
          </button>
        </p>
      </form>
    </PopupLayout>
  );
}