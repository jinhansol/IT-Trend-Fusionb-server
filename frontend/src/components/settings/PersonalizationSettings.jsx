// Personalization section of the settings page (P4): switch, interests, self-rated
// skills and reset. Data is shown and editable whether personalization is ON or OFF.
import { useState } from "react";
import { fetchMyPersonalization, fetchTechnologies } from "../../api/personalization";
import { useApiResource } from "../../hooks/useApiResource";
import { useMyResource } from "../../hooks/useMyResource";
import InterestPicker from "./InterestPicker";
import PersonalizationSwitch from "./PersonalizationSwitch";
import ResetPersonalization from "./ResetPersonalization";
import SkillEditor from "./SkillEditor";

const CARD = "bg-white border border-slate-100 rounded-2xl p-6 shadow-sm";

export default function PersonalizationSettings({ onSwitchChanged }) {
  const initial = useMyResource(fetchMyPersonalization, []);
  const catalog = useApiResource(fetchTechnologies, []);
  // Reloads replace the data in place (no loading state), so the editors and their
  // "저장했습니다." messages stay on screen. Only a reset rebuilds the editors.
  const [fresh, setFresh] = useState(null);
  const [resets, setResets] = useState(0);
  const reload = async () => {
    try {
      setFresh(await fetchMyPersonalization());
    } catch {
      // Keep showing the last data; the action itself already reported its result.
    }
  };

  if (initial.status === "error" || catalog.status === "error") {
    return <p className="text-rose-600 text-sm">개인화 설정을 불러오지 못했습니다.</p>;
  }
  if (initial.status !== "ready" || catalog.status !== "ready") {
    return <p className="text-slate-400 text-sm">개인화 설정을 불러오는 중...</p>;
  }
  const data = fresh ?? initial.data;
  const notUsed = !data.enabled && <p className="text-xs text-slate-500 mb-3">개인화가 꺼져 있어 추천에 사용되지 않습니다.</p>;

  return (
    <div className="space-y-6">
      <section className={CARD} aria-labelledby="personalization-switch">
        <h2 id="personalization-switch" className="font-bold mb-3">
          개인화
        </h2>
        <PersonalizationSwitch
          enabled={data.enabled}
          onChanged={async () => {
            await onSwitchChanged?.();
            await reload();
          }}
        />
      </section>

      <section className={CARD} aria-labelledby="personalization-interests">
        <h2 id="personalization-interests" className="font-bold mb-1">
          관심 기술
        </h2>
        {notUsed}
        <InterestPicker
          key={`i-${resets}`}
          technologies={catalog.data}
          saved={data.interests}
          limit={data.limits.interests}
          onSaved={reload}
        />
      </section>

      <section className={CARD} aria-labelledby="personalization-skills">
        <h2 id="personalization-skills" className="font-bold mb-1">
          역량 자기 평가
        </h2>
        <p className="text-xs text-slate-500 mb-3">스스로 평가한 수준이며, 검증된 숙련도가 아닙니다.</p>
        {notUsed}
        <SkillEditor
          key={`s-${resets}`}
          technologies={catalog.data}
          saved={data.skills}
          limit={data.limits.skills}
          onSaved={reload}
        />
      </section>

      <section className={CARD} aria-labelledby="personalization-reset">
        <h2 id="personalization-reset" className="font-bold mb-3">
          초기화
        </h2>
        <ResetPersonalization
          onReset={async () => {
            await reload();
            setResets((n) => n + 1);
          }}
        />
      </section>
    </div>
  );
}
