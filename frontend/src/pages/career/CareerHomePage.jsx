import { Link } from "react-router-dom";
import { ArrowRight, Compass } from "lucide-react";
import { fetchTracks } from "../../api/learning";
import { fetchMyGoals } from "../../api/goals";
import { fetchMySummary, fetchMyTrackProgress } from "../../api/progress";
import { useAuth } from "../../auth/useAuth";
import { useApiResource } from "../../hooks/useApiResource";
import { useMyResource } from "../../hooks/useMyResource";
import GoalCard from "../../components/career/GoalCard";
import LoadState from "../../components/learn/LoadState";
import LoginPrompt from "../../components/learn/LoginPrompt";
import StartGuide from "../../components/learn/StartGuide";
import { ProgressBar, XpBar } from "../../components/learn/ProgressBits";

// Career hub. Phase 6 adds personalization and the AI career compass, Phase 7 the roadmap graph.

function Stat({ label, value }) {
  return (
    <div className="rounded-xl bg-slate-50 px-4 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-extrabold">{value}</p>
    </div>
  );
}

function ContinueCard({ unit }) {
  if (!unit) {
    return (
      <div className="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <h2 className="font-bold mb-2">이어서 학습하기</h2>
        <p className="text-sm text-slate-500">진행 중인 단원이 없습니다. 아래 트랙에서 새 단원을 시작해 보세요.</p>
      </div>
    );
  }
  return (
    <Link
      to={`/career/${unit.track_slug}/${unit.unit_slug}`}
      className="block rounded-2xl bg-indigo-600 text-white p-6 shadow-sm hover:bg-indigo-700 transition"
    >
      <h2 className="text-sm font-semibold opacity-80 mb-2">이어서 학습하기</h2>
      <p className="text-xs opacity-80">{unit.track_title}</p>
      <p className="text-xl font-extrabold mb-3">{unit.unit_title}</p>
      <p className="text-sm opacity-90">
        필수 활동 {unit.activities_done}/{unit.activities_required} · 퀴즈 {unit.quiz_passed ? "통과" : "미통과"}
      </p>
      <span className="inline-flex items-center gap-1 text-sm font-semibold mt-4">
        계속하기 <ArrowRight size={14} />
      </span>
    </Link>
  );
}

function MyStatus() {
  const state = useMyResource(fetchMySummary, []);
  if (state.status === "error") return <p className="text-rose-600 py-6">내 학습 현황을 불러오지 못했습니다.</p>;
  if (state.status !== "ready") return <p className="text-slate-400 py-6">내 학습 현황을 불러오는 중...</p>;
  const summary = state.data;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <section className="md:col-span-2 rounded-2xl border border-slate-100 bg-white p-6 shadow-sm" aria-label="내 학습 현황">
        <h2 className="font-bold mb-4">내 학습 현황</h2>
        <XpBar xp={summary.xp} />
        <div className="grid grid-cols-3 gap-3 mt-5">
          <Stat label="완료한 단원" value={summary.completed_units} />
          <Stat label="진행 중" value={summary.in_progress_units} />
          <Stat label="통과한 퀴즈" value={summary.passed_quizzes} />
        </div>
      </section>
      <ContinueCard unit={summary.continue_unit} />
    </div>
  );
}

// The user's own active goals (written by them; shown with personalization ON or OFF).
function MyGoals() {
  const state = useMyResource(() => fetchMyGoals("active"), []);
  if (state.status !== "ready") return null;
  const goals = state.data.items;
  return (
    <section className="mb-10" aria-labelledby="my-goals">
      <div className="flex items-baseline justify-between mb-3">
        <h2 id="my-goals" className="text-xl font-bold">
          내 학습 목표
        </h2>
        <Link to="/career/goals" className="text-sm font-semibold text-indigo-600">
          목표 관리
        </Link>
      </div>
      {goals.length === 0 ? (
        <p className="text-sm text-slate-500">
          아직 진행 중인 목표가 없습니다. 목표 관리에서 직접 추가하거나, 진로 탐색에서 직무를 목표로 삼을 수 있어요.
        </p>
      ) : (
        <div className="space-y-4">
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} />
          ))}
        </div>
      )}
    </section>
  );
}

function ExploreCard() {
  return (
    <Link
      to="/career/explore"
      className="flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition mb-10"
    >
      <span className="w-11 h-11 shrink-0 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
        <Compass size={22} aria-hidden="true" />
      </span>
      <span className="flex-1">
        <span className="block font-bold">진로 탐색</span>
        <span className="block text-sm text-slate-500">IT 직무가 하는 일과 쓰는 기술, 관련 학습을 둘러보세요.</span>
      </span>
      <ArrowRight size={18} className="text-indigo-600" aria-hidden="true" />
    </Link>
  );
}

function TrackCard({ track }) {
  const mine = useMyResource(() => fetchMyTrackProgress(track.slug), [track.slug]).data;
  return (
    <Link
      to={`/career/${track.slug}`}
      className="block bg-white rounded-2xl border border-slate-100 shadow-sm p-6 hover:shadow-md hover:border-indigo-200 transition"
    >
      <h3 className="text-xl font-bold mb-2">{track.title}</h3>
      {track.description && <p className="text-sm text-slate-600 mb-4">{track.description}</p>}
      <span className="text-xs font-semibold text-indigo-600">단원 {track.unit_count}개</span>
      {mine && (
        <div className="mt-4">
          <p className="text-xs text-slate-500 mb-1">
            완료 {mine.completed_units} / {mine.total_units}
          </p>
          <ProgressBar done={mine.completed_units} total={mine.total_units} label={`${track.title} 진행률`} />
        </div>
      )}
    </Link>
  );
}

export default function CareerHomePage() {
  const { status, user } = useAuth();
  const state = useApiResource(fetchTracks, []);

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 text-left">
      <h1 className="text-3xl font-extrabold mb-2">Career</h1>
      <p className="text-slate-500 mb-8">원하는 트랙, 원하는 단원부터 자유롭게 시작하세요.</p>

      {status !== "loading" && <StartGuide learnerType={user?.settings?.learner_type ?? null} />}

      <div className="mb-10">
        {status === "authenticated" && <MyStatus />}
        {status === "anonymous" && (
          <LoginPrompt message="로그인하면 내 학습 현황과 레벨, 이어서 학습할 단원을 볼 수 있어요." />
        )}
      </div>

      {status === "authenticated" && <MyGoals />}
      <ExploreCard />

      <h2 id="learning-tracks" className="text-xl font-bold mb-4 scroll-mt-24">학습 트랙</h2>

      {state.status !== "ready" ? (
        <LoadState state={state} />
      ) : state.data.length === 0 ? (
        <p className="text-slate-500">아직 공개된 학습 트랙이 없습니다.</p>
      ) : (
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {state.data.map((track) => (
            <li key={track.slug}>
              <TrackCard track={track} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
