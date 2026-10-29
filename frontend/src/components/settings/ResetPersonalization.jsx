// Reset after an explicit confirmation that lists what is deleted and what is kept.
// Keyboard: opening moves focus to "취소" (the safe choice), Escape closes, and
// focus returns to the reset button when the panel closes.
import { useEffect, useRef, useState } from "react";
import { resetPersonalization } from "../../api/personalization";

const DELETED = ["관심 기술", "역량 자기 평가"];
const KEPT = ["개인화 켜짐/꺼짐 상태", "학습 목표", "진로 후보", "학습 진행률", "XP", "학습자 유형"];

export default function ResetPersonalization({ onReset }) {
  const [confirming, setConfirming] = useState(false);
  const [state, setState] = useState({ status: "idle", message: "" });
  const triggerRef = useRef(null);
  const cancelRef = useRef(null);
  const opened = useRef(false);

  useEffect(() => {
    if (confirming) cancelRef.current?.focus();
    else if (opened.current) triggerRef.current?.focus();
    opened.current = opened.current || confirming;
  }, [confirming]);

  const reset = async () => {
    setState({ status: "saving", message: "" });
    try {
      await resetPersonalization();
      setConfirming(false);
      await onReset();
      setState({ status: "done", message: "초기화했습니다. 관심 기술과 역량 자기 평가가 삭제되었습니다." });
    } catch {
      setState({ status: "error", message: "초기화하지 못했습니다. 아무것도 삭제되지 않았어요. 잠시 후 다시 시도해 주세요." });
    }
  };

  return (
    <div>
      {!confirming ? (
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setConfirming(true)}
          className="px-4 py-2 rounded-lg border border-rose-200 text-rose-600 text-sm font-semibold hover:bg-rose-50"
        >
          개인화 데이터 초기화
        </button>
      ) : (
        <div
          role="dialog"
          aria-label="개인화 데이터 초기화 확인"
          onKeyDown={(e) => e.key === "Escape" && state.status !== "saving" && setConfirming(false)}
          className="rounded-xl border border-rose-200 bg-rose-50 p-4"
        >
          <p className="font-semibold mb-3">개인화 데이터를 초기화할까요? 되돌릴 수 없습니다.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-semibold text-rose-700 mb-1">삭제</p>
              <ul aria-label="삭제되는 항목" className="list-disc pl-5 space-y-0.5">
                {DELETED.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-semibold text-emerald-700 mb-1">유지</p>
              <ul aria-label="유지되는 항목" className="list-disc pl-5 space-y-0.5">
                {KEPT.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              onClick={reset}
              disabled={state.status === "saving"}
              className="px-4 py-2 rounded-lg bg-rose-600 text-white text-sm font-semibold disabled:opacity-50"
            >
              {state.status === "saving" ? "초기화 중..." : "초기화"}
            </button>
            <button
              ref={cancelRef}
              type="button"
              onClick={() => setConfirming(false)}
              className="px-4 py-2 rounded-lg border border-slate-300 bg-white text-sm font-semibold"
            >
              취소
            </button>
          </div>
        </div>
      )}
      {state.message && (
        <p role="status" className={`text-sm mt-3 ${state.status === "error" ? "text-rose-600" : "text-emerald-700"}`}>
          {state.message}
        </p>
      )}
    </div>
  );
}
