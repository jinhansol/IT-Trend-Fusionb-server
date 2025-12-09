// src/api/aiAPI.js
import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000/api/ai";

export async function sendMessage(messages) {
  try {
    const response = await axios.post(`${BASE_URL}/chat`, { messages });
    return response.data; // { role: "assistant", content: "..." }
  } catch (error) {
    console.error("❌ AI API Error:", error);
    return { role: "assistant", content: "죄송합니다. 서버 연결에 실패했습니다." };
  }
}