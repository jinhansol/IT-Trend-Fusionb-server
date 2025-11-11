// src/api/authAPI.js
import axios from "axios";

// ✅ FastAPI 라우터 prefix에 맞춰 수정
const BASE_URL = "http://localhost:8000/api/auth";

// 로그인
export const loginUser = async (email, password) => {
  const res = await axios.post(`${BASE_URL}/login`, { email, password });
  return res.data;
};

// 회원가입
export const registerUser = async (userData) => {
  const res = await axios.post(`${BASE_URL}/register`, userData);
  return res.data;
};

// ✅ 이메일 중복 체크
export const checkEmail = async (email) => {
  const res = await axios.get(`${BASE_URL}/check-email`, { params: { email } });
  return res.data.exists;
};
