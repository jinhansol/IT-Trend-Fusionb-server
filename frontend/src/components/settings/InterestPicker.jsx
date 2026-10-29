// Pick interested technologies from the published list, grouped by kind with search.
// Saved as a whole; a retired technology the user already had stays until removed.
import { useState } from "react";
import { replaceInterests } from "../../api/personalization";
import { groupByKind, matches } from "./personalizationText";

const CHIP = (on) =>
  `px-3 py-1.5 rounded-full text-sm font-semibold border transition disabled:opacity-40 ${
    on ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"
  }`;

export default function InterestPicker({ technologies, saved, limit, onSaved }) {
  const [selected, setSelected] = useState(saved.map((i) => i.slug));
  const [query, setQuery] = useState("");
  const [state, setState] = useState({ status: "idle", message: "" });

  const retired = saved.filter((i) => !i.available);
  const full = selected.length >= limit;
  const changed = [...selected].sort().join() !== saved.map((i) => i.slug).sort().join();
  const toggle = (slug) =>
    setSelected((current) => (current.includes(slug) ? current.filter((s) => s !== slug) : [...current, slug]));
  const groups = groupByKind(technologies.filter((t) => matches(t, query)));

  const save = async () => {
    setState({ status: "saving", message: "" });
    try {
      await replaceInterests(selected);
      await onSaved();
      setState({ status: "saved", message: "관심 기술을 저장했습니다." });
    } catch {
      setState({ status: "error", message: "저장하지 못했습니다. 잠시 후 다시 시도해 주세요." });
    }
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="기술 검색"
          aria-label="관심 기술 검색"
          className="flex-1 min-w-0 rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <span className="text-sm text-slate-500" aria-live="polite">
          {selected.length}/{limit}
        </span>
      </div>
      {retired.length > 0 && (
        <ul className="flex flex-wrap gap-2 mb-3" aria-label="더 이상 제공되지 않는 관심 기술">
          {retired
            .filter((i) => selected.includes(i.slug))
            .map((i) => (
              <li key={i.slug}>
                <button type="button" className={CHIP(true)} aria-pressed onClick={() => toggle(i.slug)}>
                  {i.name} (제공 중단) ✕
                </button>
              </li>
            ))}
        </ul>
      )}
      <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
        {groups.map((group) => (
          <fieldset key={group.kind}>
            <legend className="text-xs font-semibold text-slate-500 mb-1">{group.label}</legend>
            <div className="flex flex-wrap gap-2">
              {group.items.map((tech) => {
                const on = selected.includes(tech.slug);
                return (
                  <button
                    key={tech.slug}
                    type="button"
                    className={CHIP(on)}
                    aria-pressed={on}
                    disabled={!on && full}
                    onClick={() => toggle(tech.slug)}
                  >
                    {tech.name}
                  </button>
                );
              })}
            </div>
          </fieldset>
        ))}
        {groups.length === 0 && <p className="text-sm text-slate-500">검색 결과가 없습니다.</p>}
      </div>
      {full && <p className="text-xs text-slate-500 mt-2">관심 기술은 최대 {limit}개까지 고를 수 있어요.</p>}
      <div className="flex items-center gap-3 mt-4">
        <button
          type="button"
          onClick={save}
          disabled={state.status === "saving" || !changed}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-50"
        >
          {state.status === "saving" ? "저장 중..." : "관심 기술 저장"}
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
