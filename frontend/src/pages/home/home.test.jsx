import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { installFakeServer } from "../../test/fakeServer";
import HomePage from "./HomePage";

const hoursAgo = (h) => new Date(Date.now() - h * 3600_000).toISOString();

const item = (id, title, source, overrides = {}) => ({
  id,
  title,
  url: `https://example.com/${id}`,
  excerpt: `${title} 소개`,
  author: null,
  source,
  published_at: hoursAgo(id),
  collected_at: hoursAgo(id),
  score: null,
  comment_count: null,
  view_count: null,
  technologies: [],
  ...overrides,
});

const NEWS_SOURCE = { slug: "techcrunch", name: "TechCrunch", license: null };
const DEV_SOURCE = {
  slug: "webdev",
  name: "web.dev",
  license: { name: "CC BY 4.0", url: "https://creativecommons.org/licenses/by/4.0/" },
};
const news = (id, overrides) => item(id, `뉴스 ${id}`, NEWS_SOURCE, overrides);
const dev = (id, overrides) => item(100 + id, `아티클 ${id}`, DEV_SOURCE, overrides);
const page = (items, total = items.length) => ({ items, page: 1, size: 3, total });

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

function server(store, requests = []) {
  return installFakeServer({
    "GET /news": (config) => {
      requests.push(["news", config.params]);
      return [200, page(store.news.slice(0, config.params.size), store.news.length)];
    },
    "GET /dev/articles": (config) => {
      requests.push(["dev", config.params]);
      return [200, page(store.dev.slice(0, config.params.size), store.dev.length)];
    },
  });
}

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

const renderHome = (path = "/") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/news" element={<p>News 화면</p>} />
      </Routes>
      <Location />
    </MemoryRouter>
  );

const region = (name) => screen.getByRole("region", { name });

describe("Home", () => {
  it("shows the newest three news and three Dev articles, each from its own API", async () => {
    const requests = [];
    restore = server({ news: [1, 2, 3, 4, 5].map(news), dev: [1, 2, 3, 4].map((i) => dev(i)) }, requests);
    renderHome();

    expect(screen.getByRole("heading", { level: 1, name: "오늘의 IT 탐색" })).toBeTruthy();
    await screen.findByText("뉴스 1");
    const newsBox = region("최신 IT 뉴스");
    const devBox = region("최신 개발 아티클");
    expect(within(newsBox).getAllByRole("article")).toHaveLength(3);
    expect(within(devBox).getAllByRole("article")).toHaveLength(3);
    // Newest first, as the API orders them; the two lists never mix.
    expect(within(newsBox).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "뉴스 1",
      "뉴스 2",
      "뉴스 3",
    ]);
    expect(within(devBox).queryByText(/뉴스/)).toBeNull();
    expect(within(newsBox).queryByText(/아티클/)).toBeNull();
    expect(requests).toEqual([
      ["news", { page: 1, size: 3 }],
      ["dev", { page: 1, size: 3 }],
    ]);
    // Original links; no "더 보기" on Home.
    expect(within(newsBox).getByRole("link", { name: /뉴스 1/ }).getAttribute("href")).toBe("https://example.com/1");
    expect(screen.queryByRole("button", { name: /더 보기/ })).toBeNull();
  });

  it("links to the full News, Dev and Career screens", async () => {
    restore = server({ news: [news(1)], dev: [dev(1)] });
    renderHome();
    await screen.findByText("뉴스 1");
    expect(within(region("최신 IT 뉴스")).getByRole("link", { name: "전체 뉴스 보기" }).getAttribute("href")).toBe("/news");
    expect(within(region("최신 개발 아티클")).getByRole("link", { name: "Dev 전체 보기" }).getAttribute("href")).toBe("/dev");
    const career = region("학습·진로 탐색");
    expect(within(career).getByRole("link", { name: /Career 학습 시작하기/ }).getAttribute("href")).toBe("/career");
    expect(within(career).getByRole("link", { name: /진로 탐색/ }).getAttribute("href")).toBe("/career/explore");
  });

  it("shows Dev articles as title rows: no excerpt and no AI summary, news unchanged", async () => {
    const summary = {
      kind: "dev",
      partial_input: false,
      content: { headline: "요약 제목", key_concepts: [], implementation: null, applicable_when: [], caveats: [] },
    };
    restore = server({ news: [news(1)], dev: [dev(1, { ai_summary: summary }), dev(2)] });
    renderHome();
    const devBox = region("최신 개발 아티클");
    const link = await within(devBox).findByRole("link", { name: /아티클 1/ });
    expect(link.getAttribute("href")).toBe("https://example.com/101");
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(within(devBox).getAllByText("web.dev")).toHaveLength(2);
    expect(within(devBox).queryByText("요약 제목")).toBeNull();
    expect(within(devBox).queryByText("아티클 2 소개")).toBeNull();
    expect(within(devBox).queryByRole("region", { name: "AI 요약" })).toBeNull();
    expect(within(region("최신 IT 뉴스")).getByText("뉴스 1 소개")).toBeTruthy();
  });

  it("shows only what exists: none, one, or a short list", async () => {
    restore = server({ news: [], dev: [dev(1)] });
    renderHome();
    expect(await screen.findByText("아직 수집된 기사가 없습니다.")).toBeTruthy();
    expect(within(region("최신 개발 아티클")).getAllByRole("article")).toHaveLength(1);
  });

  it("shows new items on the next visit (the page only reads the API)", async () => {
    const store = { news: [1, 2, 3].map(news), dev: [1, 2, 3].map((i) => dev(i)) };
    restore = server(store);
    renderHome();
    await screen.findByText("뉴스 1");
    cleanup();

    store.news = [news(0), ...store.news]; // a new article was collected
    renderHome();
    await screen.findByText("뉴스 0");
    const titles = within(region("최신 IT 뉴스")).getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titles).toEqual(["뉴스 0", "뉴스 1", "뉴스 2"]);
  });

  it("keeps a section's error to that section", async () => {
    restore = installFakeServer({
      "GET /news": () => [500, {}],
      "GET /dev/articles": () => [200, page([dev(1)])],
    });
    renderHome();
    expect(await within(region("최신 IT 뉴스")).findByText(/불러오지 못했습니다/)).toBeTruthy();
    expect(await within(region("최신 개발 아티클")).findByText("아티클 1")).toBeTruthy();
  });

  it("sends old filtered Home links (/?tech=) to News", () => {
    restore = server({ news: [], dev: [] });
    renderHome("/?tech=python");
    expect(screen.getByText("News 화면")).toBeTruthy();
    expect(screen.getByTestId("location").textContent).toBe("/news?tech=python");
  });

  it("shows Korean titles first on news and Dev cards, and the original when there is none", async () => {
    const ko = (title, excerpt = null) => ({ language: "ko", title, excerpt });
    restore = server({
      news: [news(1, { translation: ko("번역된 뉴스", "번역된 소개") }), news(2)],
      dev: [dev(1, { translation: ko("번역된 아티클", "번역된 아티클 소개") }), dev(2)],
    });
    renderHome();
    const newsBox = region("최신 IT 뉴스");
    const devBox = region("최신 개발 아티클");
    const newsLink = await within(newsBox).findByRole("link", { name: /번역된 뉴스/ });
    expect(newsLink.getAttribute("title")).toBe("원문 제목: 뉴스 1");
    expect(within(newsBox).getByText("번역된 소개")).toBeTruthy();
    expect(within(newsBox).getByRole("link", { name: /뉴스 2/ })).toBeTruthy(); // fallback
    const devLink = within(devBox).getByRole("link", { name: /번역된 아티클/ });
    expect(devLink.getAttribute("title")).toBe("원문 제목: 아티클 1");
    expect(within(devBox).getAllByText("AI 번역")).toHaveLength(1);
    expect(within(devBox).queryByText("번역된 아티클 소개")).toBeNull(); // still title rows
    expect(within(devBox).getByRole("link", { name: /아티클 2/ })).toBeTruthy(); // fallback
  });
});
