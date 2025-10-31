// ✅ src/pages/TrendInsightPage.jsx
export default function TrendInsightPage() {
  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <h1 className="text-3xl font-bold text-indigo-600 mb-6">
        📊 기술 트렌드 인사이트
      </h1>

      <p className="text-gray-600 mb-8">
        GitHub, 뉴스, 커뮤니티 데이터를 종합 분석하여 최신 IT 트렌드를 한눈에 보여주는 페이지입니다.
      </p>

      <div className="bg-white p-6 rounded-xl shadow text-gray-500 text-center">
        데이터 로딩 중이거나 아직 연결되지 않았습니다.
        <br />
        곧 트렌드 인사이트 분석 그래프와 키워드 클라우드가 표시될 예정입니다.
      </div>
    </div>
  );
}
