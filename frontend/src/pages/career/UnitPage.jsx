import { Link, useParams } from "react-router-dom";
import { BookOpen, Code, ExternalLink, PlayCircle } from "lucide-react";
import { fetchUnit } from "../../api/learning";
import { useApiResource } from "../../hooks/useApiResource";
import LoadState from "../../components/learn/LoadState";
import Markdown from "../../components/learn/Markdown";

const KINDS = {
  reading: { label: "읽기", Icon: BookOpen },
  video: { label: "영상", Icon: PlayCircle },
  exercise: { label: "실습", Icon: Code },
  external: { label: "외부 자료", Icon: ExternalLink },
};

function ActivityCard({ activity }) {
  const { label, Icon } = KINDS[activity.kind] ?? KINDS.reading;
  return (
    <article className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <header className="flex items-center gap-3 mb-3">
        <span className="w-9 h-9 rounded-lg bg-slate-800 text-white flex items-center justify-center">
          <Icon size={18} />
        </span>
        <div className="flex-1">
          <p className="text-xs text-slate-500">
            {activity.position}. {label}
          </p>
          <h2 className="font-bold text-lg">{activity.title}</h2>
        </div>
        <span
          className={`text-xs font-semibold px-2 py-1 rounded-md ${
            activity.is_required ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"
          }`}
        >
          {activity.is_required ? "필수" : "선택"}
        </span>
      </header>

      {activity.body_md && <Markdown>{activity.body_md}</Markdown>}

      {activity.url && (
        <a
          href={activity.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg border border-slate-200 text-sm font-semibold hover:bg-slate-50"
        >
          자료 열기 <ExternalLink size={14} />
        </a>
      )}
    </article>
  );
}

export default function UnitPage() {
  const { trackSlug, unitSlug } = useParams();
  const state = useApiResource(() => fetchUnit(trackSlug, unitSlug), [trackSlug, unitSlug]);

  if (state.status !== "ready") {
    return <LoadState state={state} notFoundText="찾을 수 없는 단원입니다." />;
  }
  const unit = state.data;

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 text-left">
      <Link to={`/career/${unit.track.slug}`} className="text-sm text-slate-500 hover:text-indigo-600">
        ← {unit.track.title}
      </Link>
      <h1 className="text-3xl font-extrabold mt-3 mb-2">
        {unit.position}. {unit.title}
      </h1>
      {unit.summary && <p className="text-slate-600">{unit.summary}</p>}
      {unit.estimated_minutes && (
        <p className="text-xs text-slate-500 mt-2">예상 학습 시간 약 {unit.estimated_minutes}분</p>
      )}

      <section className="space-y-6 mt-8">
        {unit.activities.map((activity) => (
          <ActivityCard key={activity.slug} activity={activity} />
        ))}
      </section>

      <nav className="flex justify-between mt-10 text-sm font-semibold">
        {unit.prev ? (
          <Link to={`/career/${unit.track.slug}/${unit.prev.slug}`} className="text-indigo-600">
            ← {unit.prev.title}
          </Link>
        ) : (
          <span />
        )}
        {unit.next && (
          <Link to={`/career/${unit.track.slug}/${unit.next.slug}`} className="text-indigo-600">
            {unit.next.title} →
          </Link>
        )}
      </nav>
    </main>
  );
}
