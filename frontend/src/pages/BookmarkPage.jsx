// ✅ src/pages/BookmarkPage.jsx
export default function BookmarkPage() {
  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <h1 className="text-3xl font-bold text-blue-600 mb-6">🔖 내 북마크</h1>

      <p className="text-gray-600 mb-10">
        내가 저장한 IT 트렌드 뉴스, 채용 정보, 학습 자료들을 한눈에 모아볼 수 있습니다.
      </p>

      <div className="bg-white shadow rounded-xl p-6 text-gray-500 text-center">
        아직 저장된 북마크가 없습니다 🕊️
        <br />
        <span className="text-sm">홈 화면에서 마음에 드는 카드를 북마크 해보세요.</span>
      </div>
    </div>
  );
}
