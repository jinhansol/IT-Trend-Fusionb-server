// One collected article / post / question. Links open the original site.
// A stored AI summary replaces the feed excerpt; without one the card is unchanged.
// linkOnly: a board row — title, source, date and link only (no excerpt, no AI summary).
// techHref(slug): when given, each technology tag is an in-app link (e.g. to a filtered
// list); the title link stays the only link to the original site.
import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { relativeTime } from "../../utils/relativeTime";
import AiSummary from "./AiSummary";

const TAG = "text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600";

/** metrics: [{ key: "score", label: "반응" }, ...]; a metric the source lacks (null) is hidden. */
export default function ContentCard({ item, metrics = [], now, linkOnly = false, techHref }) {
  const when = item.published_at ?? item.collected_at;
  const shown = metrics.filter((m) => item[m.key] != null);
  return (
    <article className="h-full flex flex-col bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition">
      <p className="text-xs text-slate-500 mb-2 flex flex-wrap gap-x-2">
        <span className="font-semibold text-slate-600">{item.source.name}</span>
        <time dateTime={when} title={new Date(when).toLocaleString()}>
          {relativeTime(when, now)}
        </time>
        {item.author && <span className="truncate max-w-[12rem]">· {item.author}</span>}
      </p>
      <h3 className="font-semibold text-slate-900 leading-snug mb-2">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-indigo-600 inline-flex gap-1 items-start"
        >
          <span className="line-clamp-3">{item.title}</span>
          <ExternalLink size={12} className="shrink-0 mt-1.5 text-slate-400" aria-hidden="true" />
        </a>
      </h3>
      {linkOnly ? null : item.ai_summary ? (
        <AiSummary summary={item.ai_summary} license={item.source.license} />
      ) : (
        item.excerpt && <p className="text-sm text-slate-600 leading-relaxed line-clamp-3 mb-3">{item.excerpt}</p>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
        {item.technologies.slice(0, 4).map((tech) =>
          techHref ? (
            <Link
              key={tech.slug}
              to={techHref(tech.slug)}
              className={`${TAG} hover:bg-indigo-50 hover:text-indigo-700`}
              aria-label={`${tech.name} 기술 기사 보기`}
            >
              {tech.name}
            </Link>
          ) : (
            <span key={tech.slug} className={TAG}>
              {tech.name}
            </span>
          )
        )}
        {shown.length > 0 && (
          <span className="ml-auto text-xs text-slate-500 flex gap-3">
            {shown.map((m) => (
              <span key={m.key}>
                {m.label} <strong className="text-slate-700">{item[m.key].toLocaleString()}</strong>
              </span>
            ))}
          </span>
        )}
      </div>
    </article>
  );
}
