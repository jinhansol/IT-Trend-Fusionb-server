// The stored E1 AI summary of an article, folded under its headline.
// News and Dev have different fields; empty fields are left out, never filled in.
import { useId, useState } from "react";

const NOTICE = "AI가 원문을 바탕으로 정리한 내용으로, 틀릴 수 있습니다. 원문을 확인하세요.";

function List({ label, items }) {
  if (!items?.length) return null;
  return (
    <div>
      <dt className="font-semibold text-slate-700">{label}</dt>
      <dd>
        <ul className="list-disc pl-4">
          {items.map((text) => (
            <li key={text}>{text}</li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

function Text({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <dt className="font-semibold text-slate-700">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function NewsFields({ content }) {
  return (
    <>
      <Text label="핵심 사건" value={content.what_happened} />
      <List label="주요 변경 사항" items={content.key_changes} />
      <Text label="원문이 밝힌 의미" value={content.why_it_matters} />
      <List label="주의 사항" items={content.caveats} />
    </>
  );
}

function DevFields({ content }) {
  const concepts = (content.key_concepts ?? []).map((c) => `${c.name}: ${c.explanation}`);
  const impl = content.implementation;
  return (
    <>
      <List label="핵심 기술 개념" items={concepts} />
      {impl && (
        <div>
          <dt className="font-semibold text-slate-700">구현 접근 방식</dt>
          <dd>
            {impl.approach}
            {impl.steps?.length > 0 && (
              <ol className="list-decimal pl-4 mt-1">
                {impl.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            )}
          </dd>
        </div>
      )}
      <List label="활용 상황" items={content.applicable_when} />
      <List label="한계·주의 사항" items={content.caveats} />
    </>
  );
}

// Shown when the source's pages carry a license (e.g. CC BY 4.0): credit and a note that
// the summary changes the original.
function LicenseNote({ license }) {
  if (!license) return null;
  return (
    <p className="mt-1 text-[11px] text-slate-500">
      원문 라이선스{" "}
      <a href={license.url} target="_blank" rel="noopener noreferrer license" className="underline hover:text-indigo-600">
        {license.name}
      </a>{" "}
      · 이 요약은 AI가 원문을 요약·재구성한 것으로 원문과 다릅니다.
    </p>
  );
}

export default function AiSummary({ summary, license = null }) {
  const [open, setOpen] = useState(false);
  const panel = useId();
  const { content } = summary;
  return (
    <section aria-label="AI 요약" className="mb-3 rounded-xl bg-slate-50 border border-slate-100 p-3 text-sm text-slate-700">
      <p className="flex items-center gap-2 text-xs text-slate-500 mb-1">
        <span className="font-semibold text-indigo-700">AI 요약</span>
        {summary.partial_input && <span>글 일부 기반</span>}
      </p>
      <p className="font-medium text-slate-800">{content.headline}</p>
      <LicenseNote license={license} />
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panel}
        onClick={() => setOpen((v) => !v)}
        className="mt-1 text-xs font-semibold text-indigo-600 hover:underline"
      >
        {open ? "요약 접기" : "요약 펼치기"}
      </button>
      {open && (
        <div id={panel} className="mt-2 space-y-2">
          <dl className="space-y-2">
            {summary.kind === "news" ? <NewsFields content={content} /> : <DevFields content={content} />}
          </dl>
          <p className="text-[11px] text-slate-500">{NOTICE}</p>
        </div>
      )}
    </section>
  );
}
