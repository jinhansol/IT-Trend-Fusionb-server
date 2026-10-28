// "마지막 갱신" line. Data comes from the collector's run history, not the browser clock.
import { AlertTriangle, RefreshCw } from "lucide-react";
import { fetchFeedStatus } from "../../api/content";
import { useApiResource } from "../../hooks/useApiResource";
import { relativeTime } from "../../utils/relativeTime";

export default function FeedUpdated({ scope }) {
  const state = useApiResource(() => fetchFeedStatus(scope), [scope]);
  if (state.status !== "ready") return null;
  const { last_updated_at: updated, stale } = state.data;

  if (!updated) {
    return (
      <p className="text-xs text-slate-500 flex items-center gap-1">
        <AlertTriangle size={12} aria-hidden="true" /> 아직 수집된 기록이 없습니다.
      </p>
    );
  }
  return (
    <p className={`text-xs flex items-center gap-1 ${stale ? "text-amber-700" : "text-slate-500"}`}>
      {stale ? <AlertTriangle size={12} aria-hidden="true" /> : <RefreshCw size={12} aria-hidden="true" />}
      마지막 갱신 {relativeTime(updated)}
      {stale && " · 수집이 지연되고 있습니다"}
    </p>
  );
}
