import { fetchNews, fetchTrends } from "../../api/content";
import { useApiResource } from "../../hooks/useApiResource";
import { usePagedList } from "../../hooks/usePagedList";
import FeedList from "../../components/feed/FeedList";
import FeedUpdated from "../../components/feed/FeedUpdated";
import RelatedLearning from "../../components/feed/RelatedLearning";
import { useTechParam } from "../../hooks/useTechParam";
import TechFilter from "../../components/feed/TechFilter";
import { DailyTrend, RankBars } from "../../components/feed/TrendCharts";

// DevHub 2.0 Home: IT news collected from RSS feeds, and what they talk about.
export default function HomePage() {
  const [tech, setTech] = useTechParam();
  const trends = useApiResource(() => fetchTrends("news", 7), []);
  const news = usePagedList((page) => fetchNews({ page, size: 12, tech }), [tech]);
  const report = trends.status === "ready" ? trends.data : null;

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 text-left">
      <header className="flex flex-wrap items-end justify-between gap-2 mb-6">
        <div>
          <h1 className="text-3xl font-extrabold">IT 뉴스</h1>
          <p className="text-slate-500">국내외 IT 매체의 최신 기사를 모았습니다. 제목을 누르면 원문으로 이동합니다.</p>
        </div>
        <FeedUpdated scope="news" />
      </header>

      {report && (
        <div className="mb-6">
          <TechFilter technologies={[...report.fields, ...report.technologies].slice(0, 12)} value={tech} onChange={setTech} />
        </div>
      )}
      <RelatedLearning tech={tech} />
      <FeedList list={news} emptyText={tech ? "이 기술에 관한 기사가 아직 없습니다." : "아직 수집된 기사가 없습니다."} />

      <section className="mt-16" aria-labelledby="news-trends">
        <h2 id="news-trends" className="text-2xl font-bold mb-1">수집 기사 기술 언급량</h2>
        <p className="text-sm text-slate-500 mb-6">
          최근 7일 수집 기사 {report ? `${report.total}건` : ""} 중 기술 이름이 언급된 기사 수입니다. 실제 기술 성장세나 인기를 뜻하지 않습니다.
        </p>
        {trends.status === "error" && <p className="text-slate-600">언급량을 불러오지 못했습니다.</p>}
        {report && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RankBars title="분야별 언급 기사 수" items={report.fields} />
            <RankBars title="언급 기사 수 상위 기술" items={report.technologies} />
            <div className="lg:col-span-2">
              <DailyTrend report={report} />
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
