// Labels shared by the personalization settings (P4).

export const KIND_LABELS = {
  field: "분야",
  language: "언어",
  framework: "프레임워크",
  library: "라이브러리",
  platform: "플랫폼",
  tool: "도구",
};

export const KIND_ORDER = ["field", "language", "framework", "library", "platform", "tool"];

// Self-ratings, not verified proficiency.
export const SKILL_LEVELS = [
  { value: "learning", label: "배우는 중" },
  { value: "used", label: "써 본 적 있음" },
  { value: "confident", label: "자신 있음" },
];

export const ON_NOTICE =
  "개인화를 켜면 저장한 관심 기술과 역량 정보를 향후 맞춤 추천에 사용할 수 있습니다. 현재는 개인화 추천 기능이 제공되지 않습니다.";
export const ON_STATUS = "개인화가 켜져 있어요. 현재는 개인화 추천 기능이 제공되지 않습니다.";
export const OFF_NOTICE = "개인화가 꺼져 있어요. 관심 기술과 역량은 저장되지만 추천에 사용되지 않습니다.";

/** Group technologies by kind, in KIND_ORDER, keeping the server order inside a group. */
export function groupByKind(technologies) {
  return KIND_ORDER.map((kind) => ({
    kind,
    label: KIND_LABELS[kind],
    items: technologies.filter((t) => t.kind === kind),
  })).filter((group) => group.items.length > 0);
}

export function matches(tech, query) {
  const q = query.trim().toLowerCase();
  return !q || tech.name.toLowerCase().includes(q) || tech.slug.includes(q);
}
