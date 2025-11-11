// src/api/interestAPI.js
import axios from "axios";

const BASE_URL = "http://localhost:8000/api/interests";

// ✅ 관심사 저장
export const saveInterests = async (user_id, interests, main_focus) => {
  const res = await axios.post("http://localhost:8000/api/interests/save", {
    user_id,
    interests,
    main_focus,
  });
  return res.data;
};

// ✅ 관심사 조회
export const getInterests = async (user_id) => {
  const res = await axios.get(`http://localhost:8000/api/interests/${user_id}`);
  return res.data;
};
