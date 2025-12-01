import React, { useState } from "react";
// ✅ 경로 수정: components/common
import PopupLayout from "../components/common/PopupLayout";
// ✅ API 수정: authAPI -> userAPI
import { registerUser, checkEmail } from "../api/userAPI";

export default function SignupPopup({ onClose, onSwitch, setUser }) {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    username: "",
    main_focus: "Career", // 기본값
  });
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      // 1. 이메일 중복 체크
      const exists = await checkEmail(formData.email);
      if (exists) {
        setError("이미 사용 중인 이메일입니다.");
        return;
      }

      // 2. 회원가입 요청
      const data = await registerUser(formData);
      
      // 3. 바로 로그인 처리
      setUser(data.user);
      localStorage.setItem("token", data.access_token);
      
      onClose(); // 팝업 닫기 (또는 관심사 팝업으로 이어지게 처리 가능)
    } catch (err) {
      setError("회원가입 중 오류가 발생했습니다.");
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
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">이름 (닉네임)</label>
          <input
            name="username"
            type="text"
            className="w-full border p-2 rounded mt-1"
            onChange={handleChange}
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">주요 관심 분야</label>
          <select
            name="main_focus"
            className="w-full border p-2 rounded mt-1"
            onChange={handleChange}
            value={formData.main_focus}
          >
            <option value="Career">취업 (Career)</option>
            <option value="Dev">개발 (Dev)</option>
          </select>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition"
        >
          가입하기
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