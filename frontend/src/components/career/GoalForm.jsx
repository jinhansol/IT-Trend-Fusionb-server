// Form to write a learning goal. A goal is created only when the user presses save:
// opening the form from a role page just pre-fills it (career exploration never
// creates or changes goals by itself).
import { useState } from "react";
import { createGoal } from "../../api/goals";

const MESSAGES = {
  GOAL_LIMIT: "진행 중인 목표는 최대 5개까지 둘 수 있어요. 목표를 달성 처리하거나 보관한 뒤 다시 시도해 주세요.",
  CAREER_ROLE_NOT_FOUND: "더 이상 제공되지 않는 직무입니다.",
  TECHNOLOGY_NOT_FOUND: "더 이상 제공되지 않는 기술입니다.",
  TRACK_NOT_FOUND: "더 이상 제공되지 않는 트랙입니다.",
};

/** target: { role } | { technology } | { track } | null (free-form goal). */
export default function GoalForm({ target = null, targetLabel = null, initialTitle = "", onSaved, onCancel }) {
  const [title, setTitle] = useState(initialTitle);
  const [targetDate, setTargetDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const goal = await createGoal({ title, ...(target ?? {}), target_date: targetDate || null });
      onSaved?.(goal);
    } catch (err) {
      setError(MESSAGES[err.code] ?? "목표를 저장하지 못했습니다. 입력을 확인하고 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} aria-label="학습 목표 추가" className="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">
      {targetLabel && <p className="text-sm text-slate-500">연결: {targetLabel}</p>}
      <label className="block text-sm font-semibold">
        목표
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={100}
          required
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 font-normal"
          placeholder="예: 백엔드 개발자 되기"
        />
      </label>
      <label className="block text-sm font-semibold">
        목표일 (선택)
        <input
          type="date"
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
          className="mt-1 block rounded-lg border border-slate-300 px-3 py-2 font-normal"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-rose-600">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy || !title.trim()}
          className="px-4 py-2 rounded-lg bg-slate-800 text-white text-sm font-semibold disabled:opacity-50"
        >
          {busy ? "저장 중..." : "목표 저장"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-semibold">
            취소
          </button>
        )}
      </div>
    </form>
  );
}
