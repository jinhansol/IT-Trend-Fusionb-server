// Self-rated skills: for each chosen technology, one of three levels. These are the
// user's own ratings, not a verified proficiency. Saved as a whole.
import { useState } from "react";
import { replaceSkills } from "../../api/personalization";
import { SKILL_LEVELS, groupByKind } from "./personalizationText";

export default function SkillEditor({ technologies, saved, limit, onSaved }) {
  const [rows, setRows] = useState(saved.map((s) => ({ slug: s.slug, name: s.name, level: s.level, available: s.available })));
  const [adding, setAdding] = useState("");
  const [state, setState] = useState({ status: "idle", message: "" });

  const chosen = new Set(rows.map((r) => r.slug));
  const groups = groupByKind(technologies.filter((t) => !chosen.has(t.slug)));
  const changed =
    JSON.stringify(rows.map((r) => [r.slug, r.level]).sort()) !== JSON.stringify(saved.map((s) => [s.slug, s.level]).sort());

  const add = (slug) => {
    const tech = technologies.find((t) => t.slug === slug);
    if (tech) setRows((current) => [...current, { slug, name: tech.name, level: "learning", available: true }]);
    setAdding("");
  };
  const setLevel = (slug, level) => setRows((current) => current.map((r) => (r.slug === slug ? { ...r, level } : r)));
  const remove = (slug) => setRows((current) => current.filter((r) => r.slug !== slug));

  const save = async () => {
    setState({ status: "saving", message: "" });
    try {
      await replaceSkills(rows.map((r) => ({ technology: r.slug, level: r.level })));
      await onSaved();
      setState({ status: "saved", message: "역량 자기 평가를 저장했습니다." });
    } catch {
      setState({ status: "error", message: "저장하지 못했습니다. 잠시 후 다시 시도해 주세요." });
    }
  };

  return (
    <div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500 mb-3">아직 평가한 기술이 없습니다.</p>
      ) : (
        <ul className="space-y-2 mb-3">
          {rows.map((row) => (
            <li key={row.slug} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-100 px-3 py-2">
              <span className="font-semibold flex-1 min-w-[8rem]">
                {row.name}
                {!row.available && <span className="text-xs text-slate-500"> (제공 중단)</span>}
              </span>
              <select
                value={row.level}
                onChange={(e) => setLevel(row.slug, e.target.value)}
                aria-label={`${row.name} 역량`}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              >
                {SKILL_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
              <button type="button" onClick={() => remove(row.slug)} className="text-sm text-slate-500 hover:text-rose-600">
                삭제
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={adding}
          onChange={(e) => add(e.target.value)}
          disabled={rows.length >= limit}
          aria-label="평가할 기술 추가"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm max-w-full"
        >
          <option value="">기술 추가…</option>
          {groups.map((group) => (
            <optgroup key={group.kind} label={group.label}>
              {group.items.map((tech) => (
                <option key={tech.slug} value={tech.slug}>
                  {tech.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <span className="text-sm text-slate-500">
          {rows.length}/{limit}
        </span>
      </div>
      <div className="flex items-center gap-3 mt-4">
        <button
          type="button"
          onClick={save}
          disabled={state.status === "saving" || !changed}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-50"
        >
          {state.status === "saving" ? "저장 중..." : "역량 저장"}
        </button>
        {state.message && (
          <p role="status" className={`text-sm ${state.status === "error" ? "text-rose-600" : "text-emerald-700"}`}>
            {state.message}
          </p>
        )}
      </div>
    </div>
  );
}
