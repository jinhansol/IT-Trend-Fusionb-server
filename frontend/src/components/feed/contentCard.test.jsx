import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import ContentCard from "./ContentCard";

const ITEM = {
  id: 1,
  title: "Nimbus delays its N3 accelerator to 2027",
  url: "https://news.example.com/n3",
  excerpt: "The chip will ship in the second quarter of 2027.",
  author: null,
  source: { slug: "sample-en", name: "Sample EN" },
  published_at: "2026-10-30T00:00:00Z",
  collected_at: "2026-10-30T00:00:00Z",
  technologies: [{ slug: "ai", name: "AI" }],
};

afterEach(cleanup);

describe("ContentCard translation", () => {
  it("shows the Korean translation, labelled, with the same link and tags", () => {
    render(
      <ContentCard
        item={{ ...ITEM, translation: { language: "ko", title: "Nimbus, N3 가속기 출시를 2027년으로 연기", excerpt: "칩은 2027년 2분기에 출시된다." } }}
      />
    );
    const link = screen.getByRole("link", { name: /N3 가속기 출시를 2027년으로 연기/ });
    expect(link.getAttribute("href")).toBe(ITEM.url);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("title")).toBe(`원문 제목: ${ITEM.title}`);
    expect(screen.getByText("AI 번역")).toBeTruthy();
    expect(screen.getByText("칩은 2027년 2분기에 출시된다.")).toBeTruthy();
    expect(screen.queryByText(ITEM.excerpt)).toBeNull();
    expect(screen.getByText("AI")).toBeTruthy();
  });

  it("shows the original when there is no translation", () => {
    render(<ContentCard item={{ ...ITEM, translation: null }} />);
    expect(screen.getByRole("link", { name: new RegExp(ITEM.title) }).getAttribute("title")).toBeNull();
    expect(screen.getByText(ITEM.excerpt)).toBeTruthy();
    expect(screen.queryByText("AI 번역")).toBeNull();
  });
});
