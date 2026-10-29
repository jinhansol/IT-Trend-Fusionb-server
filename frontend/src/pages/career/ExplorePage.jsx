// Career exploration: every published role in a fixed order, the same for every visitor
// (no ranking by learner type, records or settings). P3.
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { fetchCareerRoles } from "../../api/careers";
import { useApiResource } from "../../hooks/useApiResource";
import LoadState from "../../components/learn/LoadState";

function RoleCard({ role }) {
  return (
    <Link
      to={`/career/roles/${role.slug}`}
      className="flex flex-col h-full bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md hover:border-indigo-200 transition"
    >
      <h2 className="text-xl font-bold mb-2">{role.name}</h2>
      <p className="text-sm text-slate-600 mb-4 flex-1">{role.summary}</p>
      {role.core_technologies.length > 0 && (
        <ul className="flex flex-wrap gap-1.5 mb-3" aria-label={`${role.name} 핵심 기술`}>
          {role.core_technologies.map((tech) => (
            <li key={tech.slug} className="text-xs font-semibold px-2 py-1 rounded-md bg-slate-100 text-slate-700">
              {tech.name}
            </li>
          ))}
        </ul>
      )}
      <span className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600">
        자세히 보기 <ArrowRight size={14} />
      </span>
    </Link>
  );
}

export default function ExplorePage() {
  const state = useApiResource(fetchCareerRoles, []);

  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 py-10 text-left">
      <Link to="/career" className="text-sm text-slate-500 hover:text-indigo-600">
        ← Career
      </Link>
      <h1 className="text-3xl font-extrabold mt-3 mb-2">진로 탐색</h1>
      <p className="text-slate-500 mb-8">
        IT 직무가 하는 일과 쓰는 기술을 둘러보세요. 마음에 드는 직무는 진로 후보로 저장하거나 학습 목표로 삼을 수 있어요.
      </p>

      {state.status !== "ready" ? (
        <LoadState state={state} />
      ) : state.data.length === 0 ? (
        <p className="text-slate-500">아직 공개된 직무 정보가 없습니다.</p>
      ) : (
        <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {state.data.map((role) => (
            <li key={role.slug}>
              <RoleCard role={role} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
