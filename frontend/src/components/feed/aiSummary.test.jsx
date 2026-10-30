import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import ContentCard from "./ContentCard";

const BASE = {
  id: 1,
  title: "Sample article",
  url: "https://blog.example.com/a",
  excerpt: "Feed excerpt text",
  author: null,
  source: { slug: "s", name: "Sample" },
  published_at: "2026-10-30T00:00:00Z",
  collected_at: "2026-10-30T00:00:00Z",
  technologies: [{ slug: "java", name: "Java" }],
};

const NEWS = {
  kind: "news",
  partial_input: false,
  content: {
    headline: "데브클라우드, 벡터 DB 정식 출시",
    what_happened: "서울 리전에서 정식 출시했다.",
    key_changes: ["하이브리드 검색"],
    why_it_matters: null,
    caveats: [],
  },
};

const DEV = {
  kind: "dev",
  partial_input: true,
  content: {
    headline: "가상 스레드로 처리량 늘리기",
    key_concepts: [{ name: "가상 스레드", explanation: "생성 비용이 낮다." }],
    implementation: { approach: "설정으로 켠다.", steps: ["스레드 풀 제거"] },
    applicable_when: [],
    caveats: ["pinning 주의"],
  },
};

afterEach(cleanup);

describe("AI summary on cards", () => {
  it("shows the News headline folded and its fields when opened, skipping empty ones", () => {
    render(<ContentCard item={{ ...BASE, ai_summary: NEWS }} />);
    const box = screen.getByRole("region", { name: "AI 요약" });
    expect(within(box).getByText(NEWS.content.headline)).toBeTruthy();
    expect(screen.queryByText("Feed excerpt text")).toBeNull(); // the summary replaces the excerpt
    const toggle = within(box).getByRole("button", { name: "요약 펼치기" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(within(box).queryByText("핵심 사건")).toBeNull();

    fireEvent.click(toggle);
    expect(within(box).getByText("서울 리전에서 정식 출시했다.")).toBeTruthy();
    expect(within(box).getByText("하이브리드 검색")).toBeTruthy();
    expect(within(box).queryByText("원문이 밝힌 의미")).toBeNull(); // null field left out
    expect(within(box).queryByText("주의 사항")).toBeNull(); // empty list left out
    expect(within(box).getByText(/틀릴 수 있습니다/)).toBeTruthy();
    // Link, source and tags are unchanged.
    expect(screen.getByRole("link", { name: /Sample article/ }).getAttribute("href")).toBe(BASE.url);
    expect(screen.getByText("Java")).toBeTruthy();
  });

  it("shows the Dev fields and the partial-input label", () => {
    render(<ContentCard item={{ ...BASE, ai_summary: DEV }} />);
    const box = screen.getByRole("region", { name: "AI 요약" });
    expect(within(box).getByText("글 일부 기반")).toBeTruthy();
    fireEvent.click(within(box).getByRole("button", { name: "요약 펼치기" }));
    expect(within(box).getByText("가상 스레드: 생성 비용이 낮다.")).toBeTruthy();
    expect(within(box).getByText("설정으로 켠다.")).toBeTruthy();
    expect(within(box).getByText("스레드 풀 제거")).toBeTruthy();
    expect(within(box).getByText("pinning 주의")).toBeTruthy();
    expect(within(box).queryByText("활용 상황")).toBeNull();
  });

  it("keeps the plain card when there is no summary", () => {
    render(<ContentCard item={{ ...BASE, ai_summary: null }} />);
    expect(screen.queryByRole("region", { name: "AI 요약" })).toBeNull();
    expect(screen.getByText("Feed excerpt text")).toBeTruthy();
  });

  it("works next to a translation", () => {
    render(
      <ContentCard
        item={{ ...BASE, translation: { language: "ko", title: "번역된 제목", excerpt: "번역된 소개" }, ai_summary: NEWS }}
      />
    );
    expect(screen.getByRole("link", { name: /번역된 제목/ })).toBeTruthy();
    expect(screen.getByText("AI 번역")).toBeTruthy();
    expect(screen.getByRole("region", { name: "AI 요약" })).toBeTruthy();
  });
});
