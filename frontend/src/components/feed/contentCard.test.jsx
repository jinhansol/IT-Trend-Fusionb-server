import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import ContentCard from "./ContentCard";

const ITEM = {
  id: 1,
  title: "국내 클라우드 사업자, 서울 리전 GPU 서버 확대",
  url: "https://news.example.com/n3",
  excerpt: "서울 리전에 GPU 서버를 추가한다.",
  author: "홍길동",
  source: { slug: "sample-news", name: "Sample News" },
  published_at: "2026-10-30T00:00:00Z",
  collected_at: "2026-10-30T00:00:00Z",
  technologies: [{ slug: "cloud", name: "클라우드" }],
};

afterEach(cleanup);

describe("ContentCard", () => {
  it("shows the original Korean title, source, author, excerpt and tags with a safe link", () => {
    render(<ContentCard item={ITEM} />);
    const link = screen.getByRole("link", { name: new RegExp(ITEM.title) });
    expect(link.getAttribute("href")).toBe(ITEM.url);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByText("Sample News")).toBeTruthy();
    expect(screen.getByText(/홍길동/)).toBeTruthy();
    expect(screen.getByText(ITEM.excerpt)).toBeTruthy();
    expect(screen.getByText("클라우드")).toBeTruthy();
  });

  it("shows tags as plain labels unless a techHref is given", () => {
    render(<ContentCard item={ITEM} />);
    expect(screen.getAllByRole("link")).toHaveLength(1); // the title only
  });

  it("links each tag in the app when techHref is given, apart from the original link", () => {
    render(
      <MemoryRouter>
        <ContentCard item={ITEM} techHref={(slug) => `/news?tech=${slug}`} />
      </MemoryRouter>
    );
    const tag = screen.getByRole("link", { name: "클라우드 기술 기사 보기" });
    expect(tag.getAttribute("href")).toBe("/news?tech=cloud");
    expect(tag.getAttribute("target")).toBeNull();
    const title = screen.getByRole("link", { name: new RegExp(ITEM.title) });
    expect(title.getAttribute("href")).toBe(ITEM.url);
    expect(title.contains(tag)).toBe(false); // never nested in the original link
  });

  it("never shows a translation, even if one is sent (translation was dropped)", () => {
    render(<ContentCard item={{ ...ITEM, translation: { language: "ko", title: "다른 제목", excerpt: "x" } }} />);
    expect(screen.getByRole("link", { name: new RegExp(ITEM.title) })).toBeTruthy();
    expect(screen.queryByText("다른 제목")).toBeNull();
    expect(screen.queryByText("AI 번역")).toBeNull();
  });
});
