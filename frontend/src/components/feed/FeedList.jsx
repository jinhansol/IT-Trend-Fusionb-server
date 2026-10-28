// Grid of ContentCards with loading, empty, error and "더 보기" states.
import ContentCard from "./ContentCard";

export default function FeedList({ list, metrics, emptyText }) {
  if (list.status === "loading") return <p className="text-slate-400 py-10 text-center">불러오는 중...</p>;
  if (list.status === "error") {
    return <p className="text-slate-600 py-10 text-center">목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>;
  }
  if (list.items.length === 0) return <p className="text-slate-500 py-10 text-center">{emptyText}</p>;

  const now = new Date();
  return (
    <div>
      <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {list.items.map((item) => (
          <li key={item.id}>
            <ContentCard item={item} metrics={metrics} now={now} />
          </li>
        ))}
      </ul>
      <div className="text-center mt-6 space-y-2">
        {list.moreFailed && <p className="text-sm text-rose-600">더 불러오지 못했습니다.</p>}
        {list.hasMore && (
          <button
            type="button"
            onClick={list.loadMore}
            disabled={list.status === "loading-more"}
            className="px-5 py-2 rounded-xl border border-slate-200 bg-white text-sm font-semibold hover:bg-slate-50 disabled:opacity-50"
          >
            {list.status === "loading-more" ? "불러오는 중..." : `더 보기 (${list.items.length}/${list.total})`}
          </button>
        )}
      </div>
    </div>
  );
}
