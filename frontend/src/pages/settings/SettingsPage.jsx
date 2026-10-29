import { useState } from "react";
import { updateLearnerType } from "../../api/settings";
import { useAuth } from "../../auth/useAuth";
import LearnerTypePicker from "../../components/learn/LearnerTypePicker";
import LoginPrompt from "../../components/learn/LoginPrompt";
import PersonalizationSettings from "../../components/settings/PersonalizationSettings";

function LearnerTypeForm({ current, onSaved }) {
  const [value, setValue] = useState(current);
  const [state, setState] = useState({ status: "idle", message: "" });

  const save = async (event) => {
    event.preventDefault();
    setState({ status: "saving", message: "" });
    try {
      await updateLearnerType(value);
      await onSaved();
      setState({ status: "saved", message: "저장했습니다." });
    } catch {
      setState({ status: "error", message: "저장하지 못했습니다. 잠시 후 다시 시도해 주세요." });
    }
  };

  return (
    <form onSubmit={save} className="space-y-4">
      <LearnerTypePicker value={value} onChange={setValue} name="settings_learner_type" />
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={state.status === "saving" || value === current}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-50"
        >
          {state.status === "saving" ? "저장 중..." : "저장"}
        </button>
        {state.message && (
          <p role="status" className={`text-sm ${state.status === "error" ? "text-rose-600" : "text-emerald-700"}`}>
            {state.message}
          </p>
        )}
      </div>
    </form>
  );
}

export default function SettingsPage() {
  const { status, user, reloadUser } = useAuth();

  return (
    <main className="max-w-2xl mx-auto px-4 sm:px-6 py-10 text-left">
      <h1 className="text-3xl font-extrabold mb-6">설정</h1>
      {status === "loading" && <p className="text-slate-400">불러오는 중...</p>}
      {status === "anonymous" && <LoginPrompt message="설정은 로그인한 뒤 바꿀 수 있어요." />}
      {status === "authenticated" && (
        <div className="space-y-6">
          <section className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm">
            <h2 className="font-bold mb-1">학습자 유형</h2>
            <p className="text-sm text-slate-500 mb-4">Career 첫 화면의 시작 안내가 바뀝니다. 학습 기록과 XP에는 영향이 없어요.</p>
            {/* Not keyed by the saved value: reloading the user after a save must keep
                the form (and its "저장했습니다." message) on screen. */}
            <LearnerTypeForm current={user.settings?.learner_type ?? null} onSaved={reloadUser} />
          </section>
          <PersonalizationSettings onSwitchChanged={reloadUser} />
        </div>
      )}
    </main>
  );
}
