import axios from "axios";
const BASE_URL = "http://127.0.0.1:8000/api/dev";

/** 🔹 언어 분포 데이터 (PieChart용) */
export const fetchLanguageStats = async () => {
  const res = await axios.get(`${BASE_URL}/lang-stats`);
  return res.data.languages;
};

/** 🔹 인기 오픈소스 리포지토리 (리스트 + 그래프용) */
export const fetchRepoTrends = async () => {
  const res = await axios.get(`${BASE_URL}/repos`);
  return res.data.repos;
};

/** 🔹 AI 인사이트 (사이드 패널용) */
export const fetchAiInsights = async () => {
  const res = await axios.get(`${BASE_URL}/insights`);
  return res.data.insights;
};

/** 🔹 Repository Growth 데이터 (LineChart용) */
export const fetchGrowthData = async () => {
  const res = await axios.get(`${BASE_URL}/growth`);
  return res.data.growth;
};
