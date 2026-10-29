// Technology filter chips. One row, scrolls sideways on small screens.
export default function TechFilter({ technologies, value, onChange }) {
  // A filter that came from a link (e.g. a Career unit) may not be among the current
  // top technologies; keep it visible so it can be cleared.
  if (value && !technologies.some((t) => t.slug === value)) {
    technologies = [{ slug: value, name: value }, ...technologies];
  }
  if (!technologies.length) return null;
  const chip = (active) =>
    `shrink-0 px-3 py-1.5 rounded-full text-sm font-semibold border transition ${
      active ? "bg-slate-800 text-white border-slate-800" : "bg-white text-slate-600 border-slate-200 hover:border-slate-400"
    }`;
  return (
    <div className="flex gap-2 overflow-x-auto pb-1" role="group" aria-label="기술 필터">
      <button type="button" className={chip(!value)} aria-pressed={!value} onClick={() => onChange(null)}>
        전체
      </button>
      {technologies.map((tech) => (
        <button
          key={tech.slug}
          type="button"
          className={chip(value === tech.slug)}
          aria-pressed={value === tech.slug}
          onClick={() => onChange(value === tech.slug ? null : tech.slug)}
        >
          {tech.name}
        </button>
      ))}
    </div>
  );
}
