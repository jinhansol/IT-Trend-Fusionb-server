import axios from "axios";
const BASE_URL = "http://127.0.0.1:8000/api/news";

export async function fetchNews() {
  try {
    const res = await axios.get(`${BASE_URL}/latest`);
    return res.data;
  } catch (err) {
    console.error("❌ 뉴스 불러오기 실패:", err);
    return [];
  }
}
