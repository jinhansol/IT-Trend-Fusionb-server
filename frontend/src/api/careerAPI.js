// src/api/careerAPI.js

// 🧠 실제 FastAPI 백엔드와 연결된 Career 데이터 호출
export async function fetchCareerData(keyword = "Python") {
  try {
    console.log(`[CareerAPI] 서버로 요청: ${keyword}`);

    const response = await fetch(`http://localhost:8000/api/career/jobs?keyword=${keyword}`);
    if (!response.ok) {
      throw new Error("백엔드 API 응답 오류");
    }

    const data = await response.json();
    console.log("[CareerAPI] 받아온 데이터:", data);

    // ✅ results만 반환
    return data.results || [];
  } catch (error) {
    console.error("[CareerAPI] Fetch Error:", error);
    return [];
  }
}

