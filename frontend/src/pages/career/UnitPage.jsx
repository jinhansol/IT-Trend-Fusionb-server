import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BookOpen, Check, Code, ExternalLink, PartyPopper, PlayCircle } from "lucide-react";
import { fetchUnit } from "../../api/learning";
import { confirmActivity, fetchMyUnitProgress } from "../../api/progress";
import { useAuth } from "../../auth/useAuth";
import { useApiResource } from "../../hooks/useApiResource";
import LoadState from "../../components/learn/LoadState";
import LoginPrompt from "../../components/learn/LoginPrompt";
import Markdown from "../../components/learn/Markdown";
import { StateBadge } from "../../components/learn/ProgressBits";
import QuizPanel from "../../components/learn/QuizPanel";

const KINDS = {
  reading: { label: "읽기", Icon: BookOpen },
  video: { label: "영상", Icon: PlayCircle },
  exercise: { label: "실습", Icon: Code },
  external: { label: "외부 자료", Icon: ExternalLink },
};

function ConfirmButton({ confirmed, busy, onConfirm }) {
  if (confirmed) {
    return (
      <span className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-50 text-emerald-700 text-sm font-semibold">
        <Check size={14} /> 학습 완료
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={onConfirm}
      disabled={busy}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-white text-sm font-semibold hover:bg-slate-700 disabled:opacity-50"
    >
      <Check size={14} /> {busy ? "저장 중..." : "학습 완료로 표시"}
    </button>
  );
}

function ActivityCard({ activity, confirm }) {
  const { label, Icon } = KINDS[activity.kind] ?? KINDS.reading;
  return (
    <article className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <header className="flex items-center gap-3 mb-3">
        <span className="w-9 h-9 rounded-lg bg-slate-800 text-white flex items-center justify-center">
          <Icon size={18} />
        </span>
        <div className="flex-1">
          <p className="text-xs text-slate-500">
            {activity.position}. {label}
          </p>
          <h2 className="font-bold text-lg">{activity.title}</h2>
        </div>
        <span
          className={`text-xs font-semibold px-2 py-1 rounded-md ${
            activity.is_required ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"
          }`}
        >
          {activity.is_required ? "필수" : "선택"}
        </span>
      </header>

      {activity.body_md && <Markdown>{activity.body_md}</Markdown>}

      {activity.url && (
        <a
          href={activity.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg border border-slate-200 text-sm font-semibold hover:bg-slate-50"
        >
          자료 열기 <ExternalLink size={14} />
        </a>
      )}

      {confirm && (
        <footer className="mt-5 pt-4 border-t border-slate-100">
          <ConfirmButton {...confirm} />
        </footer>
      )}
    </article>
  );
}

/** The learner's progress for this unit; null while unknown or when logged out. */
function useUnitProgress(trackSlug, unitSlug, authStatus) {
  const [detail, setDetail] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    setDetail(null);
    setFailed(false);
    if (authStatus !== "authenticated") return undefined;
    fetchMyUnitProgress(trackSlug, unitSlug)
      .then((data) => active && setDetail(data))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [trackSlug, unitSlug, authStatus]);

  return [detail, setDetail, failed];
}

function ProgressHeader({ progress }) {
  return (
    <div className="flex flex-wrap items-center gap-3 mt-4 text-sm text-slate-600">
      <StateBadge state={progress.state} />
      <span>
        필수 활동 {progress.activities_done}/{progress.activities_required}
      </span>
      {progress.has_quiz && <span>퀴즈 {progress.quiz_passed ? "통과" : "미통과"}</span>}
    </div>
  );
}

function RewardBanner({ reward }) {
  const gained = reward.granted_rewards.reduce((sum, r) => sum + r.amount, 0);
  return (
    <div role="status" className="mt-6 rounded-2xl bg-gradient-to-r from-indigo-500 to-emerald-500 text-white p-5">
      <p className="flex items-center gap-2 font-extrabold text-lg">
        <PartyPopper size={22} /> 단원 완료! +{gained} XP
      </p>
      <p className="text-sm opacity-90 mt-1">
        현재 Lv {reward.xp.level} · 다음 레벨까지 {reward.xp.xp_for_next_level - reward.xp.xp_into_level} XP
      </p>
    </div>
  );
}

export default function UnitPage() {
  const { trackSlug, unitSlug } = useParams();
  const { status: authStatus } = useAuth();
  const state = useApiResource(() => fetchUnit(trackSlug, unitSlug), [trackSlug, unitSlug]);
  const [detail, setDetail, progressFailed] = useUnitProgress(trackSlug, unitSlug, authStatus);
  const [busyId, setBusyId] = useState(null);
  const [actionError, setActionError] = useState("");
  const [reward, setReward] = useState(null);

  useEffect(() => setReward(null), [trackSlug, unitSlug]);

  if (state.status !== "ready") {
    return <LoadState state={state} notFoundText="찾을 수 없는 단원입니다." />;
  }
  const unit = state.data;
  const loggedIn = authStatus === "authenticated";
  const confirmedIds = new Set(detail?.confirmed_activity_ids ?? []);

  const applyResponse = (response) => {
    setDetail((prev) => prev && { ...prev, progress: response.progress });
    if (response.granted_rewards.length > 0) setReward(response);
  };

  const handleConfirm = async (activityId) => {
    setBusyId(activityId);
    setActionError("");
    try {
      const response = await confirmActivity(activityId);
      setDetail(
        (prev) =>
          prev && {
            ...prev,
            confirmed_activity_ids: [...new Set([...prev.confirmed_activity_ids, response.activity_id])],
          }
      );
      applyResponse(response);
    } catch {
      setActionError("학습 기록을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusyId(null);
    }
  };

  const handleQuizResult = (result) => {
    setDetail((prev) => prev && { ...prev, quiz: { ...prev.quiz, passed: result.progress.quiz_passed } });
    applyResponse(result);
  };

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 text-left">
      <Link to={`/career/${unit.track.slug}`} className="text-sm text-slate-500 hover:text-indigo-600">
        ← {unit.track.title}
      </Link>
      <h1 className="text-3xl font-extrabold mt-3 mb-2">
        {unit.position}. {unit.title}
      </h1>
      {unit.summary && <p className="text-slate-600">{unit.summary}</p>}
      {unit.estimated_minutes && (
        <p className="text-xs text-slate-500 mt-2">예상 학습 시간 약 {unit.estimated_minutes}분</p>
      )}
      {detail && <ProgressHeader progress={detail.progress} />}
      {progressFailed && <p className="text-sm text-rose-600 mt-4">내 학습 기록을 불러오지 못했습니다.</p>}
      {reward && <RewardBanner reward={reward} />}

      {authStatus === "anonymous" && (
        <div className="mt-8">
          <LoginPrompt message="로그인하면 학습 기록과 퀴즈 결과가 저장되고 XP를 받을 수 있어요." />
        </div>
      )}
      {actionError && <p className="text-sm text-rose-600 mt-4">{actionError}</p>}

      <section className="space-y-6 mt-8">
        {unit.activities.map((activity) => (
          <ActivityCard
            key={activity.slug}
            activity={activity}
            confirm={
              detail && {
                confirmed: confirmedIds.has(activity.id),
                busy: busyId === activity.id,
                onConfirm: () => handleConfirm(activity.id),
              }
            }
          />
        ))}
      </section>

      {unit.quiz && loggedIn && detail && (
        <div className="mt-8">
          <QuizPanel
            key={`${trackSlug}/${unitSlug}`}
            trackSlug={trackSlug}
            unitSlug={unitSlug}
            summary={unit.quiz}
            passed={detail.quiz.passed}
            onResult={handleQuizResult}
          />
        </div>
      )}

      <nav className="flex justify-between mt-10 text-sm font-semibold">
        {unit.prev ? (
          <Link to={`/career/${unit.track.slug}/${unit.prev.slug}`} className="text-indigo-600">
            ← {unit.prev.title}
          </Link>
        ) : (
          <span />
        )}
        {unit.next && (
          <Link to={`/career/${unit.track.slug}/${unit.next.slug}`} className="text-indigo-600">
            {unit.next.title} →
          </Link>
        )}
      </nav>
    </main>
  );
}
