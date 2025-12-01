// src/api/userAPI.js
import axios from "axios";

// 공통 Axios 인스턴스
const api = axios.create({
  baseURL: "http://localhost:8000/api", // 공통 베이스 URL
});

// 토큰 자동 포함 (나중에 인증 필요할 때를 대비)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/* ==============================================
   🔐 인증 (Auth) 관련
   ============================================== */

// 로그인
export const loginUser = async (email, password) => {
  try {
    const res = await api.post("/auth/login", { email, password });
    
    // ✅ [수정] 로그인 성공 시 토큰 저장 및 이벤트 발생
    if (res.data.access_token) {
      localStorage.setItem("token", res.data.access_token);
      
      // 🔔 브라우저 전체에 "로그인 상태 변경됨" 알림 방송
      window.dispatchEvent(new Event("auth-change"));
    }

    return res.data;
  } catch (err) {
    console.error("❌ 로그인 실패:", err);
    throw err;
  }
};

// 회원가입
export const registerUser = async (userData) => {
  try {
    const res = await api.post("/auth/register", userData);
    return res.data;
  } catch (err) {
    console.error("❌ 회원가입 실패:", err);
    throw err;
  }
};

// 이메일 중복 체크
export const checkEmail = async (email) => {
  try {
    const res = await api.get("/auth/check-email", { params: { email } });
    return res.data.exists;
  } catch (err) {
    console.error("❌ 이메일 확인 실패:", err);
    return false;
  }
};

/* ==============================================
   ❤️ 관심사 (Interests) 관련
   ============================================== */

// 관심사 저장
export const saveInterests = async (user_id, interests, main_focus) => {
  try {
    const res = await api.post("/interests/save", {
      user_id,
      interests,
      main_focus,
    });
    return res.data;
  } catch (err) {
    console.error("❌ 관심사 저장 실패:", err);
    throw err;
  }
};

// 관심사 조회
export const getInterests = async (user_id) => {
  try {
    const res = await api.get(`/interests/${user_id}`);
    return res.data;
  } catch (err) {
    console.error("❌ 관심사 조회 실패:", err);
    return null;
  }
};