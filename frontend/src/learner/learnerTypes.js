// Learner types (A-plan v0.2, P1). Used ONLY for static start guidance and menu links.
// Never use them to sort, rank, filter or recommend content (policy C-2).
// Values match backend app/models/user.py LEARNER_TYPES.

export const LEARNER_TYPES = [
  { value: "beginner", label: "입문자", description: "개발을 처음 배우기 시작했어요" },
  { value: "developer", label: "개발자", description: "개발 경험이 있고 기술을 넓히고 싶어요" },
  { value: "exploring", label: "탐색 중", description: "IT 분야와 진로를 둘러보는 중이에요" },
];

export const learnerTypeLabel = (value) => LEARNER_TYPES.find((t) => t.value === value)?.label ?? null;

// The guide is shown on the Career home, so the track list is an in-page anchor.
const TRACKS = { href: "#learning-tracks", label: "학습 트랙 보기" };
const DEV = { to: "/dev", label: "Dev 둘러보기" };
const HOME = { to: "/", label: "IT 뉴스 보기" };

// Static copy: identical for everyone with the same type, never based on records.
export const START_GUIDES = {
  common: {
    title: "DevHub를 이렇게 시작해 보세요",
    body: "Home에서 IT 소식을, Dev에서 개발 글을, Career에서 체계적인 학습을 할 수 있어요. 원하는 곳부터 자유롭게 시작하세요.",
    links: [HOME, DEV, TRACKS],
  },
  beginner: {
    title: "처음이라면 학습 트랙부터 시작해 보세요",
    body: "단원마다 읽을거리와 퀴즈가 있어 순서대로 따라가기 좋아요. 막히는 개념은 Dev에서 관련 글을 찾아볼 수 있어요.",
    links: [TRACKS, DEV],
  },
  developer: {
    title: "관심 기술의 최신 글을 살펴보세요",
    body: "Dev에서 커뮤니티와 기술 블로그 글을, Home에서 IT 소식을 볼 수 있어요. 기초를 다지고 싶다면 학습 트랙도 있어요.",
    links: [DEV, HOME, TRACKS],
  },
  exploring: {
    title: "IT 분야를 넓게 둘러보세요",
    body: "Home의 IT 소식과 Dev의 개발 이야기를 둘러보며 관심 분야를 찾아보세요. 마음에 드는 분야가 생기면 학습 트랙으로 시작할 수 있어요.",
    links: [HOME, DEV, TRACKS],
  },
};

export const startGuideFor = (learnerType) => START_GUIDES[learnerType] ?? START_GUIDES.common;
