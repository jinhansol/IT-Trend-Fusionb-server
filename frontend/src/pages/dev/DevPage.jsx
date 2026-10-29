import { useState } from "react";
import { fetchChannelPosts, fetchDevChannels, fetchTrends } from "../../api/content";
import { useApiResource } from "../../hooks/useApiResource";
import { usePagedList } from "../../hooks/usePagedList";
import FeedList from "../../components/feed/FeedList";
import FeedUpdated from "../../components/feed/FeedUpdated";
import RelatedLearning from "../../components/feed/RelatedLearning";
import { useTechParam } from "../../hooks/useTechParam";
import TechFilter from "../../components/feed/TechFilter";
import { RankBars } from "../../components/feed/TrendCharts";

// Metric names differ by kind of site; a metric the site does not provide is hidden.
const METRICS = {
  blog: [
    { key: "score", label: "반응" },
    { key: "comment_count", label: "댓글" },
  ],
  community: [
    { key: "score", label: "포인트" },
    { key: "comment_count", label: "댓글" },
  ],
  qna: [
    { key: "score", label: "점수" },
    { key: "comment_count", label: "답변" },
    { key: "view_count", label: "조회" },
  ],
};

function ChannelTabs({ channels, value, onChange }) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-slate-200" role="tablist" aria-label="소스">
      {channels.map((channel) => (
        <button
          key={channel.slug}
          type="button"
          role="tab"
          aria-selected={value === channel.slug}
          onClick={() => onChange(channel.slug)}
          className={`shrink-0 px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px transition ${
            value === channel.slug
              ? "border-indigo-600 text-indigo-700"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          {channel.name}
        </button>
      ))}
    </div>
  );
}

function SortToggle({ channel, value, onChange }) {
  const option = (sort, label, disabled) => (
    <button
      type="button"
      aria-pressed={value === sort}
      disabled={disabled}
      onClick={() => onChange(sort)}
      className={`px-3 py-1.5 text-sm font-semibold rounded-lg ${
        value === sort ? "bg-white shadow-sm text-slate-900" : "text-slate-500"
      } disabled:opacity-40`}
      title={disabled ? "이 소스는 인기 지표를 제공하지 않습니다" : undefined}
    >
      {label}
    </button>
  );
  return (
    <div className="inline-flex bg-slate-100 rounded-xl p-1" role="group" aria-label="정렬">
      {option("latest", "최신순", false)}
      {option("popular", "주간 인기", !channel.has_metrics)}
    </div>
  );
}

function ChannelFeed({ channel, tech }) {
  // The parent keys this component by channel, so the sort resets when the tab changes.
  const [sort, setSort] = useState("latest");
  const effectiveSort = channel.has_metrics ? sort : "latest";
  const list = usePagedList(
    (page) => fetchChannelPosts(channel.slug, { sort: effectiveSort, days: 7, page, size: 12, tech }),
    [channel.slug, effectiveSort, tech]
  );
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 my-5">
        <p className="text-sm text-slate-500">{channel.sources.map((s) => s.name).join(" · ")}</p>
        <SortToggle channel={channel} value={effectiveSort} onChange={setSort} />
      </div>
      <FeedList
        list={list}
        metrics={METRICS[channel.kind] ?? []}
        emptyText={effectiveSort === "popular" ? "최근 7일 동안 올라온 글이 없습니다." : "아직 수집된 글이 없습니다."}
      />
    </div>
  );
}

// DevHub 2.0 Dev: developer posts and questions from official APIs and feeds.
export default function DevPage() {
  const channels = useApiResource(fetchDevChannels, []);
  const trends = useApiResource(() => fetchTrends("dev", 7), []);
  const [selected, setSelected] = useState(null);
  const [tech, setTech] = useTechParam();
  const report = trends.status === "ready" ? trends.data : null;

  const list = channels.status === "ready" ? channels.data : [];
  const channel = list.find((c) => c.slug === selected) ?? list[0];

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 text-left">
      <header className="flex flex-wrap items-end justify-between gap-2 mb-6">
        <div>
          <h1 className="text-3xl font-extrabold">Dev</h1>
          <p className="text-slate-500">개발자 커뮤니티와 기술 블로그의 글을 소스별로 모았습니다.</p>
        </div>
        <FeedUpdated scope="dev" />
      </header>

      {report && (
        <div className="mb-4">
          <TechFilter technologies={report.technologies} value={tech} onChange={setTech} />
        </div>
      )}
      <RelatedLearning tech={tech} />

      {channels.status === "loading" && <p className="text-slate-400 py-10 text-center">불러오는 중...</p>}
      {channels.status === "error" && (
        <p className="text-slate-600 py-10 text-center">소스 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
      )}
      {channels.status === "ready" && list.length === 0 && (
        <p className="text-slate-500 py-10 text-center">아직 등록된 소스가 없습니다.</p>
      )}
      {channel && (
        <>
          <ChannelTabs channels={list} value={channel.slug} onChange={setSelected} />
          <ChannelFeed key={channel.slug} channel={channel} tech={tech} />
        </>
      )}

      <section className="mt-16" aria-labelledby="dev-trends">
        <h2 id="dev-trends" className="text-2xl font-bold mb-1">수집 글 기술 언급량</h2>
        <p className="text-sm text-slate-500 mb-6">최근 7일 모든 소스에서 수집한 글 {report ? `${report.total}건` : ""} 중 기술 이름이 언급된 글 수입니다. 실제 기술 성장세나 인기를 뜻하지 않습니다.</p>
        {report && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RankBars title="언급 글 수 상위 기술" items={report.technologies} />
            <RankBars title="분야별 언급 글 수" items={report.fields} />
          </div>
        )}
      </section>
    </main>
  );
}
