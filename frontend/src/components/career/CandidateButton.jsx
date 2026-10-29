// Save or remove a role as one of my career candidates. Only this button writes
// candidates; it never creates a learning goal or changes settings (P3).
import { useState } from "react";
import { Bookmark, BookmarkCheck } from "lucide-react";
import { fetchMyCandidates, removeCandidate, saveCandidate } from "../../api/careers";
import { useMyResource } from "../../hooks/useMyResource";

const MESSAGES = {
  CANDIDATE_LIMIT: "진로 후보는 최대 10개까지 저장할 수 있어요. 목표 관리에서 정리한 뒤 다시 시도해 주세요.",
};

export default function CandidateButton({ role }) {
  const list = useMyResource(fetchMyCandidates, []);
  const [override, setOverride] = useState(null); // true/false after a click
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (list.status !== "ready") return null;
  const saved = override ?? list.data.items.some((item) => item.role.slug === role.slug);

  const toggle = async () => {
    setBusy(true);
    setError("");
    try {
      if (saved) await removeCandidate(role.slug);
      else await saveCandidate(role.slug);
      setOverride(!saved);
    } catch (err) {
      setError(MESSAGES[err.code] ?? "저장하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBusy(false);
    }
  };

  const Icon = saved ? BookmarkCheck : Bookmark;
  return (
    <div>
      <button
        type="button"
        onClick={toggle}
        disabled={busy}
        aria-pressed={saved}
        className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border disabled:opacity-50 ${
          saved ? "bg-indigo-50 border-indigo-200 text-indigo-700" : "bg-white border-slate-300 text-slate-700 hover:bg-slate-50"
        }`}
      >
        <Icon size={16} aria-hidden="true" /> {saved ? "진로 후보에 저장됨" : "진로 후보에 저장"}
      </button>
      {error && (
        <p role="alert" className="text-sm text-rose-600 mt-2">
          {error}
        </p>
      )}
    </div>
  );
}
