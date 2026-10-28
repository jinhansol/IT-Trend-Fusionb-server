// Small progress widgets. They only display values the server computed.
import { CheckCircle2 } from "lucide-react";

export function XpBar({ xp }) {
  const percent = Math.min(100, Math.round((xp.xp_into_level / xp.xp_for_next_level) * 100));
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="font-extrabold text-lg">Lv {xp.level}</span>
        <span className="text-xs text-slate-500">
          {xp.xp_into_level} / {xp.xp_for_next_level} XP · 누적 {xp.total} XP
        </span>
      </div>
      <div
        className="h-2.5 rounded-full bg-slate-100 overflow-hidden"
        role="progressbar"
        aria-label="다음 레벨까지"
        aria-valuemin={0}
        aria-valuemax={xp.xp_for_next_level}
        aria-valuenow={xp.xp_into_level}
      >
        <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

export function ProgressBar({ done, total, label }) {
  const percent = total ? Math.round((done / total) * 100) : 0;
  return (
    <div
      className="h-2 rounded-full bg-slate-100 overflow-hidden"
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={total}
      aria-valuenow={done}
    >
      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${percent}%` }} />
    </div>
  );
}

const STATES = {
  completed: { text: "완료", className: "bg-emerald-100 text-emerald-700" },
  in_progress: { text: "진행 중", className: "bg-indigo-100 text-indigo-700" },
  not_started: { text: "시작 전", className: "bg-slate-100 text-slate-500" },
};

export function StateBadge({ state }) {
  const { text, className } = STATES[state] ?? STATES.not_started;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-md ${className}`}>
      {state === "completed" && <CheckCircle2 size={12} />}
      {text}
    </span>
  );
}
