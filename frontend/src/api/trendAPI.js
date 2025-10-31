import axios from "axios";

const BASE_URL = "http://127.0.0.1:8000/api/trend";

export async function fetchTrendSummary(keyword = "IT") {
  try {
    const res = await axios.get(`${BASE_URL}/recommend`, {
      params: { keyword },
    });
    return res.data;
  } catch (err) {
    console.error("❌ 트렌드 요약 불러오기 실패:", err);
    return { message: "데이터를 불러오는 중 오류가 발생했습니다." };
  }
}
