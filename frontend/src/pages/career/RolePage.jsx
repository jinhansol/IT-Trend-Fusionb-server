// One career role: what the job does, its technologies and the Career units for each
// technology (technology-level links, P2). Viewing never changes goals or settings. P3.
import { Link, useParams } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { fetchCareerRole } from "../../api/careers";
import { useApiResource } from "../../hooks/useApiResource";
import RoleActions from "../../components/career/RoleActions";
import LoadState from "../../components/learn/LoadState";
import Markdown from "../../components/learn/Markdown";

const IMPORTANCE = [
  { value: "core", label: "핵심 기술" },
  { value: "related", label: "함께 쓰는 기술" },
];

function TechnologyItem({ tech }) {
  const query = `?tech=${encodeURIComponent(tech.slug)}`;
  return (
    <li className="rounded-xl border border-slate-100 bg-white p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="font-bold">{tech.name}</span>
        <Link to={`/${query}`} className="text-sm text-indigo-600 hover:underline">
          IT 뉴스
        </Link>
        <Link to={`/dev${query}`} className="text-sm text-indigo-600 hover:underline">
          Dev 글
        </Link>
      </div>
      {tech.units.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-2" aria-label={`${tech.name} Career 학습`}>
          {tech.units.map((unit) => (
            <li key={`${unit.track.slug}/${unit.slug}`}>
              <Link
                to={`/career/${unit.track.slug}/${unit.slug}`}
                className="inline-block text-sm px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 hover:bg-emerald-100"
              >
                {unit.track.title} · {unit.position}. {unit.title}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-slate-400">아직 이 기술을 다루는 Career 학습이 없습니다.</p>
      )}
    </li>
  );
}

export default function RolePage() {
  const { roleSlug } = useParams();
  const state = useApiResource(() => fetchCareerRole(roleSlug), [roleSlug]);

  if (state.status !== "ready") {
    return <LoadState state={state} notFoundText="찾을 수 없는 직무입니다." />;
  }
  const role = state.data;

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 text-left">
      <Link to="/career/explore" className="text-sm text-slate-500 hover:text-indigo-600">
        ← 진로 탐색
      </Link>
      <h1 className="text-3xl font-extrabold mt-3 mb-2">{role.name}</h1>
      <p className="text-slate-600">{role.summary}</p>
      <RoleActions role={role} />

      <section className="mt-8" aria-labelledby="role-description">
        <h2 id="role-description" className="text-xl font-bold mb-2">하는 일</h2>
        <Markdown>{role.description_md}</Markdown>
        <h3 className="font-bold mt-5 mb-2">대표 업무</h3>
        <ul className="list-disc pl-5 space-y-1 text-slate-700">
          {role.tasks.map((task) => (
            <li key={task}>{task}</li>
          ))}
        </ul>
      </section>

      {IMPORTANCE.map(({ value, label }) => {
        const technologies = role.technologies.filter((t) => t.importance === value);
        if (technologies.length === 0) return null;
        return (
          <section key={value} className="mt-8" aria-label={label}>
            <h2 className="text-xl font-bold mb-3">{label}</h2>
            <ul className="space-y-3">
              {technologies.map((tech) => (
                <TechnologyItem key={tech.slug} tech={tech} />
              ))}
            </ul>
          </section>
        );
      })}

      <section className="mt-8" aria-labelledby="role-references">
        <h2 id="role-references" className="text-sm font-bold text-slate-500 mb-2">참고 자료</h2>
        <ul className="space-y-1 text-sm">
          {role.references.map((ref) => (
            <li key={ref.url}>
              <a
                href={ref.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-indigo-600 hover:underline break-all"
              >
                {ref.title} <ExternalLink size={12} aria-hidden="true" />
              </a>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
