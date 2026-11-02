// DevHub 2.0 Home: the latest IT news and Dev articles side by side (three each, newest
// first, from the stored content), and the way into News, Dev and Career. Every visit reads
// the database through the API; nothing is collected here.
import { Link, Navigate, useLocation } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { fetchDevArticles, fetchNews } from "../../api/content";
import { useApiResource } from "../../hooks/useApiResource";
import FeedList from "../../components/feed/FeedList";

const LATEST = 3;

/** FeedList takes a paged list; Home shows one fixed page without "더 보기". */
function asList(resource) {
  return { status: resource.status, items: resource.data?.items ?? [], hasMore: false };
}

function LatestSection({ id, title, description, moreTo, moreLabel, resource, emptyText, linkOnly = false }) {
  return (
    <section aria-labelledby={id} className="mt-12">
      <div className="flex flex-wrap items-end justify-between gap-2 mb-4">
        <div>
          <h2 id={id} className="text-2xl font-bold">
            {title}
          </h2>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
        <Link to={moreTo} className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600 hover:underline">
          {moreLabel}
          <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </div>
      <FeedList list={asList(resource)} emptyText={emptyText} linkOnly={linkOnly} />
    </section>
  );
}

function CareerEntry() {
  return (
    <section aria-labelledby="home-career" className="mt-12">
      <h2 id="home-career" className="text-2xl font-bold mb-1">
        학습·진로 탐색
      </h2>
      <p className="text-sm text-slate-500 mb-4">읽은 기술을 Career에서 직접 배우거나, IT 직무가 쓰는 기술을 살펴보세요.</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        <Link
          to="/career"
          className="block rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition"
        >
          <p className="font-semibold text-slate-900">Career 학습 시작하기</p>
          <p className="text-sm text-slate-600 mt-1">원하는 트랙, 원하는 단원부터 자유롭게 시작하세요.</p>
        </Link>
        <Link
          to="/career/explore"
          className="block rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition"
        >
          <p className="font-semibold text-slate-900">진로 탐색</p>
          <p className="text-sm text-slate-600 mt-1">IT 직무가 하는 일과 쓰는 기술을 둘러보세요.</p>
        </Link>
      </div>
    </section>
  );
}

function HomeSections() {
  const news = useApiResource(() => fetchNews({ size: LATEST }), []);
  const dev = useApiResource(() => fetchDevArticles({ size: LATEST }), []);
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10 text-left">
      <header>
        <h1 className="text-3xl font-extrabold">오늘의 IT 탐색</h1>
        <p className="text-slate-500">
          최신 IT 뉴스와 개발 아티클을 함께 보고, 관심 있는 기술은 Career에서 이어서 배워 보세요.
        </p>
      </header>
      <LatestSection
        id="home-news"
        title="최신 IT 뉴스"
        description="국내외 IT 매체의 최근 기사입니다. 제목을 누르면 원문으로 이동합니다."
        moreTo="/news"
        moreLabel="전체 뉴스 보기"
        resource={news}
        emptyText="아직 수집된 기사가 없습니다."
      />
      <LatestSection
        id="home-dev"
        title="최신 개발 아티클"
        description="개발 블로그의 최근 글입니다. 커뮤니티와 Q&A는 Dev에서 볼 수 있습니다."
        moreTo="/dev"
        moreLabel="Dev 전체 보기"
        resource={dev}
        emptyText="아직 수집된 개발 아티클이 없습니다."
        linkOnly
      />
      <CareerEntry />
    </main>
  );
}

export default function HomePage() {
  const location = useLocation();
  // The news filter used to live on Home (/?tech=python); keep those links working.
  if (new URLSearchParams(location.search).has("tech")) {
    return <Navigate to={`/news${location.search}`} replace />;
  }
  return <HomeSections />;
}
