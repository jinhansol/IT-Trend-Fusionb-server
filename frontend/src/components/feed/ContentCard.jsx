// One collected article / post / question. Links open the original site.
// News items may carry a Korean AI translation; the original is shown when there is none.
// A stored AI summary replaces the feed excerpt; without one the card is unchanged.
import { ExternalLink } from "lucide-react";
import { relativeTime } from "../../utils/relativeTime";
import AiSummary from "./AiSummary";

/** metrics: [{ key: "score", label: "반응" }, ...]; a metric the source lacks (null) is hidden. */
export default function ContentCard({ item, metrics = [], now }) {
  const when = item.published_at ?? item.collected_at;
  const shown = metrics.filter((m) => item[m.key] != null);
  const translated = item.translation ?? null;
  const title = translated ? translated.title : item.title;
  const excerpt = translated ? translated.excerpt : item.excerpt;
  return (
    <article className="h-full flex flex-col bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition">
      <p className="text-xs text-slate-500 mb-2 flex flex-wrap gap-x-2">
        <span className="font-semibold text-slate-600">{item.source.name}</span>
        <time dateTime={when} title={new Date(when).toLocaleString()}>
          {relativeTime(when, now)}
        </time>
        {item.author && <span className="truncate max-w-[12rem]">· {item.author}</span>}
        {translated && (
          <span className="text-[11px] font-semibold px-1.5 rounded bg-indigo-50 text-indigo-700">AI 번역</span>
        )}
      </p>
      <h3 className="font-semibold text-slate-900 leading-snug mb-2">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          title={translated ? `원문 제목: ${item.title}` : undefined}
          lang={translated ? "ko" : undefined}
          className="hover:text-indigo-600 inline-flex gap-1 items-start"
        >
          <span className="line-clamp-3">{title}</span>
          <ExternalLink size={12} className="shrink-0 mt-1.5 text-slate-400" aria-hidden="true" />
        </a>
      </h3>
      {item.ai_summary ? (
        <AiSummary summary={item.ai_summary} license={item.source.license} />
      ) : (
        excerpt && <p className="text-sm text-slate-600 leading-relaxed line-clamp-3 mb-3">{excerpt}</p>
      )}
      <div className="mt-auto flex flex-wrap items-center gap-2 pt-2">
        {item.technologies.slice(0, 4).map((tech) => (
          <span key={tech.slug} className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
            {tech.name}
          </span>
        ))}
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
