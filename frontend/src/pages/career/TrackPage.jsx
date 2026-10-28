import { Link, useParams } from "react-router-dom";
import { Clock } from "lucide-react";
import { fetchTrack } from "../../api/learning";
import { useApiResource } from "../../hooks/useApiResource";
import LoadState from "../../components/learn/LoadState";

export default function TrackPage() {
  const { trackSlug } = useParams();
  const state = useApiResource(() => fetchTrack(trackSlug), [trackSlug]);

  if (state.status !== "ready") {
    return <LoadState state={state} notFoundText="찾을 수 없는 학습 트랙입니다." />;
  }
  const track = state.data;

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 text-left">
      <Link to="/career" className="text-sm text-slate-500 hover:text-indigo-600">
        ← Career
      </Link>
      <h1 className="text-3xl font-extrabold mt-3 mb-2">{track.title}</h1>
      {track.description && <p className="text-slate-600 mb-8">{track.description}</p>}

      {track.units.length === 0 ? (
        <p className="text-slate-500">아직 공개된 단원이 없습니다.</p>
      ) : (
        <ol className="space-y-4">
          {track.units.map((unit) => (
            <li key={unit.slug}>
              <Link
                to={`/career/${track.slug}/${unit.slug}`}
                className="flex gap-5 items-start bg-white rounded-2xl border border-slate-100 shadow-sm p-5 hover:border-indigo-200 hover:shadow-md transition"
              >
                <span className="shrink-0 w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 font-bold flex items-center justify-center">
                  {unit.position}
                </span>
                <div className="flex-1">
                  <h2 className="font-bold text-lg">{unit.title}</h2>
                  {unit.summary && <p className="text-sm text-slate-600 mt-1">{unit.summary}</p>}
                  <div className="flex gap-4 text-xs text-slate-500 mt-3">
                    <span>활동 {unit.activity_count}개</span>
                    {unit.estimated_minutes && (
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> 약 {unit.estimated_minutes}분
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
