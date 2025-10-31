export default function SearchBar({ onSearch }) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter") onSearch();
  };

  return (
    <div className="w-full flex justify-center mt-10">
      <input
        type="text"
        placeholder="IT 트렌드 키워드를 입력하세요 (예: AI, 클라우드, Python)"
        className="w-2/3 md:w-1/2 border border-gray-300 rounded-l-lg p-3 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
        onKeyDown={handleKeyDown}
      />
      <button
        onClick={onSearch}
        className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-r-lg transition"
      >
        검색
      </button>
    </div>
  );
}
