// One learning goal with its linked Career units and the user's own progress.
// The unit list is fixed for the chosen target (catalog order), not a recommendation.
import { Link } from "react-router-dom";
import { StateBadge } from "../learn/ProgressBits";

const KIND_LABELS = { role: "직무", technology: "기술", track: "트랙" };
const STATUS_LABELS = { active: "진행 중", achieved: "달성", archived: "보관" };

function targetLink(target) {
  if (!target.available) return null;
  if (target.kind === "role") return `/career/roles/${target.slug}`;
  if (target.kind === "track") return `/career/${target.slug}`;
  return `/dev?tech=${encodeURIComponent(target.slug)}`;
}

export function GoalUnits({ units }) {
  if (units.length === 0) return null;
  const done = units.filter((u) => u.state === "completed").length;
  return (
    <div className="mt-3">
      <p className="text-xs text-slate-500 mb-1">
        연결된 Career 학습 {done}/{units.length} 완료
      </p>
      <ul className="flex flex-wrap gap-2">
        {units.map((unit) => (
          <li key={`${unit.track.slug}/${unit.slug}`}>
            <Link
              to={`/career/${unit.track.slug}/${unit.slug}`}
              className="inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-indigo-300"
            >
              {unit.track.title} · {unit.position}. {unit.title}
              <StateBadge state={unit.state} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function GoalCard({ goal, children }) {
  const { target } = goal;
  const link = target && targetLink(target);
  return (
    <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm" aria-label={`목표: ${goal.title}`}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-bold text-lg flex-1 min-w-0 break-words">{goal.title}</h3>
        <span className="text-xs font-semibold px-2 py-1 rounded-md bg-slate-100 text-slate-600">
          {STATUS_LABELS[goal.status]}
        </span>
      </div>
      <p className="text-sm text-slate-500 mt-1 flex flex-wrap gap-x-3">
        {target &&
          (link ? (
            <Link to={link} className="text-indigo-600 hover:underline">
              {KIND_LABELS[target.kind]}: {target.name}
            </Link>
          ) : (
            <span>
              {KIND_LABELS[target.kind]}: {target.name} (더 이상 제공되지 않음)
            </span>
          ))}
        {goal.target_date && <span>목표일 {goal.target_date}</span>}
      </p>
      <GoalUnits units={goal.units} />
      {children}
    </article>
  );
}
