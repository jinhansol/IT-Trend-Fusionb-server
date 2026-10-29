// The explicit personalization ON/OFF switch. Turning it ON first shows what it means;
// turning it OFF keeps the saved interests and skills.
// Keyboard: the ON confirmation takes focus, Escape closes it, focus goes back to the switch.
import { useEffect, useRef, useState } from "react";
import { setPersonalizationEnabled } from "../../api/personalization";
import { OFF_NOTICE, ON_NOTICE, ON_STATUS } from "./personalizationText";

export default function PersonalizationSwitch({ enabled, onChanged }) {
  const [confirming, setConfirming] = useState(false);
  const [state, setState] = useState({ status: "idle", message: "" });
  const switchRef = useRef(null);
  const confirmRef = useRef(null);
  const opened = useRef(false);

  useEffect(() => {
    if (confirming) confirmRef.current?.focus();
    else if (opened.current) switchRef.current?.focus();
    opened.current = opened.current || confirming;
  }, [confirming]);

  const change = async (next) => {
    setState({ status: "saving", message: "" });
    try {
      await setPersonalizationEnabled(next);
      setConfirming(false);
      await onChanged();
      setState({ status: "saved", message: next ? "개인화를 켰습니다." : "개인화를 껐습니다. 저장한 데이터는 그대로 있어요." });
    } catch {
      setState({ status: "error", message: "변경하지 못했습니다. 잠시 후 다시 시도해 주세요." });
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3">
        <button
          ref={switchRef}
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label="개인화"
          disabled={state.status === "saving"}
          onClick={() => (enabled ? change(false) : setConfirming(true))}
          className={`relative w-12 h-7 rounded-full transition disabled:opacity-50 ${enabled ? "bg-indigo-600" : "bg-slate-300"}`}
        >
          <span
            className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow transition-all ${enabled ? "left-6" : "left-1"}`}
          />
        </button>
        <span className="font-semibold">{enabled ? "켜짐" : "꺼짐"}</span>
      </div>

      {confirming && (
        <div
          role="dialog"
          aria-label="개인화 켜기 안내"
          onKeyDown={(e) => e.key === "Escape" && state.status !== "saving" && setConfirming(false)}
          className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50 p-4"
        >
          <p className="text-sm text-slate-700">{ON_NOTICE}</p>
          <div className="flex gap-2 mt-3">
            <button
              ref={confirmRef}
              type="button"
              onClick={() => change(true)}
              disabled={state.status === "saving"}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold disabled:opacity-50"
            >
              개인화 켜기
            </button>
            <button type="button" onClick={() => setConfirming(false)} className="px-4 py-2 rounded-lg border border-slate-300 text-sm font-semibold">
              취소
            </button>
          </div>
        </div>
      )}

      <p className="text-sm text-slate-500 mt-3">{enabled ? ON_STATUS : OFF_NOTICE}</p>
      {state.message && (
        <p role="status" className={`text-sm mt-2 ${state.status === "error" ? "text-rose-600" : "text-emerald-700"}`}>
          {state.message}
        </p>
      )}
    </div>
  );
}
