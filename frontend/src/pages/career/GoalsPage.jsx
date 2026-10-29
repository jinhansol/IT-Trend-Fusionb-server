// My learning goals and saved career candidates (P3). Goals are Career growth data:
// available with personalization ON or OFF. Every change here is an explicit click.
import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchMyCandidates, removeCandidate } from "../../api/careers";
import { deleteGoal, fetchMyGoals, updateGoal } from "../../api/goals";
import { useAuth } from "../../auth/useAuth";
import { useMyResource } from "../../hooks/useMyResource";
import GoalCard from "../../components/career/GoalCard";
import GoalForm from "../../components/career/GoalForm";
import LoginPrompt from "../../components/learn/LoginPrompt";

const SECTIONS = [
  { status: "active", title: "진행 중인 목표", empty: "진행 중인 목표가 없습니다." },
  { status: "achieved", title: "달성한 목표", empty: null },
  { status: "archived", title: "보관한 목표", empty: null },
];

const ERRORS = {
  GOAL_LIMIT: "진행 중인 목표는 최대 5개까지 둘 수 있어요.",
};

const BUTTON = "px-3 py-1.5 rounded-lg border border-slate-300 text-sm font-semibold hover:bg-slate-50 disabled:opacity-50";

function GoalActions({ goal, busy, onChange, onDelete }) {
  return (
    <div className="flex flex-wrap gap-2 mt-4">
      {goal.status === "active" && (
        <button type="button" className={BUTTON} disabled={busy} onClick={() => onChange({ status: "achieved" })}>
          달성으로 표시
        </button>
      )}
      {goal.status !== "active" && (
        <button type="button" className={BUTTON} disabled={busy} onClick={() => onChange({ status: "active" })}>
          다시 진행
        </button>
      )}
      {goal.status !== "archived" && (
        <button type="button" className={BUTTON} disabled={busy} onClick={() => onChange({ status: "archived" })}>
          보관
        </button>
      )}
      <button
        type="button"
        className={`${BUTTON} text-rose-600 border-rose-200`}
        disabled={busy}
        onClick={() => window.confirm(`"${goal.title}" 목표를 삭제할까요? 되돌릴 수 없습니다.`) && onDelete()}
      >
        삭제
      </button>
    </div>
  );
}

function Candidates() {
  const [version, setVersion] = useState(0);
  const state = useMyResource(fetchMyCandidates, [version]);
  if (state.status !== "ready") return null;
  const { items, limit } = state.data;

  return (
    <section className="mt-12" aria-labelledby="my-candidates">
      <h2 id="my-candidates" className="text-xl font-bold mb-1">
        저장한 진로 후보 <span className="text-sm font-normal text-slate-500">{items.length}/{limit}</span>
      </h2>
      {items.length === 0 ? (
        <p className="text-slate-500 text-sm">
          아직 저장한 직무가 없습니다.{" "}
          <Link to="/career/explore" className="text-indigo-600 underline">
            진로 탐색
          </Link>
          에서 둘러보세요.
        </p>
      ) : (
        <ul className="space-y-2 mt-3">
          {items.map((item) => (
            <li key={item.role.slug} className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-100 bg-white px-4 py-3">
              {item.role.available ? (
                <Link to={`/career/roles/${item.role.slug}`} className="font-semibold text-indigo-700 hover:underline">
                  {item.role.name}
                </Link>
              ) : (
                <span className="font-semibold text-slate-500">{item.role.name} (더 이상 제공되지 않음)</span>
              )}
              {item.note && <span className="text-sm text-slate-500 flex-1">{item.note}</span>}
              <button
                type="button"
                className={`${BUTTON} ml-auto`}
                onClick={async () => {
                  await removeCandidate(item.role.slug);
                  setVersion((v) => v + 1);
                }}
              >
                후보에서 삭제
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function MyGoals() {
  const [version, setVersion] = useState(0);
  const state = useMyResource(() => fetchMyGoals(), [version]);
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");

  if (state.status === "error") return <p className="text-rose-600">목표를 불러오지 못했습니다.</p>;
  if (state.status !== "ready") return <p className="text-slate-400">불러오는 중...</p>;
  const { items, active_limit: limit } = state.data;
  const reload = () => setVersion((v) => v + 1);

  const run = async (goal, action) => {
    setBusyId(goal.id);
    setError("");
    try {
      await action();
      reload();
    } catch (err) {
      setError(ERRORS[err.code] ?? "변경하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <div className="mb-6">
        {adding ? (
          <GoalForm
            onSaved={() => {
              setAdding(false);
              reload();
            }}
            onCancel={() => setAdding(false)}
          />
        ) : (
          <button type="button" className={BUTTON} onClick={() => setAdding(true)}>
            새 목표 추가
          </button>
        )}
      </div>
      {error && (
        <p role="alert" className="text-sm text-rose-600 mb-4">
          {error}
        </p>
      )}
      {SECTIONS.map(({ status, title, empty }) => {
        const goals = items.filter((g) => g.status === status);
        if (goals.length === 0 && !empty) return null;
        return (
          <section key={status} className="mb-10" aria-label={title}>
            <h2 className="text-xl font-bold mb-3">
              {title}
              {status === "active" && (
                <span className="text-sm font-normal text-slate-500">
                  {" "}
                  {goals.length}/{limit}
                </span>
              )}
            </h2>
            {goals.length === 0 ? (
              <p className="text-slate-500 text-sm">{empty}</p>
            ) : (
              <div className="space-y-4">
                {goals.map((goal) => (
                  <GoalCard key={goal.id} goal={goal}>
                    <GoalActions
                      goal={goal}
                      busy={busyId === goal.id}
                      onChange={(changes) => run(goal, () => updateGoal(goal.id, changes))}
                      onDelete={() => run(goal, () => deleteGoal(goal.id))}
                    />
                  </GoalCard>
                ))}
              </div>
            )}
          </section>
        );
      })}
    </>
  );
}

export default function GoalsPage() {
  const { status } = useAuth();

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10 text-left">
      <Link to="/career" className="text-sm text-slate-500 hover:text-indigo-600">
        ← Career
      </Link>
      <h1 className="text-3xl font-extrabold mt-3 mb-2">내 학습 목표</h1>
      <p className="text-slate-500 mb-8">
        직접 정한 목표와 저장한 진로 후보를 관리합니다. 목표를 달성하거나 지워도 학습 기록과 XP는 그대로입니다.
      </p>
      {status === "anonymous" && <LoginPrompt message="로그인하면 학습 목표와 진로 후보를 저장하고 관리할 수 있어요." />}
      {status === "authenticated" && (
        <>
          <MyGoals />
          <Candidates />
        </>
      )}
    </main>
  );
}
