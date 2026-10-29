// What a visitor can do with a role. Guests can read everything; saving needs login.
// "학습 목표로 추가" only opens a pre-filled form: the goal exists once the user saves it.
import { useState } from "react";
import { Link } from "react-router-dom";
import { Target } from "lucide-react";
import { useAuth } from "../../auth/useAuth";
import LoginPrompt from "../learn/LoginPrompt";
import CandidateButton from "./CandidateButton";
import GoalForm from "./GoalForm";

function AddGoal({ role }) {
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState(false);

  if (saved) {
    return (
      <p role="status" className="text-sm text-emerald-700 py-2">
        학습 목표에 추가했어요.{" "}
        <Link to="/career/goals" className="underline font-semibold">
          내 학습 목표 보기
        </Link>
      </p>
    );
  }
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
      >
        <Target size={16} aria-hidden="true" /> 학습 목표로 추가
      </button>
    );
  }
  return (
    <div className="w-full">
      <GoalForm
        target={{ role: role.slug }}
        targetLabel={`직무 · ${role.name}`}
        initialTitle={`${role.name} 되기`}
        onSaved={() => setSaved(true)}
        onCancel={() => setOpen(false)}
      />
    </div>
  );
}

export default function RoleActions({ role }) {
  const { status } = useAuth();
  if (status === "loading") return null;
  if (status !== "authenticated") {
    return (
      <div className="mt-6">
        <LoginPrompt message="로그인하면 이 직무를 진로 후보로 저장하거나 학습 목표로 삼을 수 있어요." />
      </div>
    );
  }
  return (
    <div className="mt-6 flex flex-wrap items-start gap-3">
      <CandidateButton role={role} />
      <AddGoal role={role} />
    </div>
  );
}
