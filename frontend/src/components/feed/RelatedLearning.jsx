// Career units for the technology the user picked in the filter (P2).
// Shown only for an explicit filter choice, never inferred from article tags, and
// worded as a technology-level link (not "this article is explained by this unit").
import { Link } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { fetchTechnologyUnits } from "../../api/content";
import { useApiResource } from "../../hooks/useApiResource";

export default function RelatedLearning({ tech }) {
  const state = useApiResource(() => (tech ? fetchTechnologyUnits(tech) : Promise.resolve(null)), [tech]);
  if (!tech || state.status !== "ready" || !state.data || state.data.units.length === 0) return null;
  const { technology, units } = state.data;

  return (
    <section aria-label="관련 학습" className="mb-6 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4">
      <p className="text-sm font-bold flex items-center gap-2 mb-2">
        <GraduationCap size={16} aria-hidden="true" /> {technology.name}을(를) 다루는 Career 학습
      </p>
      <ul className="flex flex-wrap gap-2">
        {units.map((unit) => (
          <li key={`${unit.track.slug}/${unit.slug}`}>
            <Link
              to={`/career/${unit.track.slug}/${unit.slug}`}
              className="inline-block text-sm px-3 py-1.5 rounded-lg bg-white border border-emerald-200 text-emerald-800 hover:bg-emerald-100"
            >
              {unit.track.title} · {unit.position}. {unit.title}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
