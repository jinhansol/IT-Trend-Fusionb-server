import { Link } from "react-router-dom";
import { fetchTracks } from "../../api/learning";
import { useApiResource } from "../../hooks/useApiResource";
import LoadState from "../../components/learn/LoadState";

// Career hub. Phase 4 adds "my progress", Phase 6 personalization, Phase 7 the roadmap graph.
export default function CareerHomePage() {
  const state = useApiResource(fetchTracks, []);

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 text-left">
      <h1 className="text-3xl font-extrabold mb-2">Career</h1>
      <p className="text-slate-500 mb-8">원하는 트랙, 원하는 단원부터 자유롭게 시작하세요.</p>

      <h2 className="text-xl font-bold mb-4">학습 트랙</h2>

      {state.status !== "ready" ? (
        <LoadState state={state} />
      ) : state.data.length === 0 ? (
        <p className="text-slate-500">아직 공개된 학습 트랙이 없습니다.</p>
      ) : (
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {state.data.map((track) => (
            <li key={track.slug}>
              <Link
                to={`/career/${track.slug}`}
                className="block bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md hover:border-indigo-200 transition"
              >
                <h3 className="text-xl font-bold mb-2">{track.title}</h3>
                {track.description && <p className="text-sm text-slate-600 mb-4">{track.description}</p>}
                <span className="text-xs font-semibold text-indigo-600">단원 {track.unit_count}개</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
