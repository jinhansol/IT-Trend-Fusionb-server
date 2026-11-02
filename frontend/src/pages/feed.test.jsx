import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { installFakeServer } from "../test/fakeServer";
import { relativeTime } from "../utils/relativeTime";
import DevPage from "./dev/DevPage";
import NewsPage from "./news/NewsPage";

// jsdom has no ResizeObserver; recharts' ResponsiveContainer needs one.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const hoursAgo = (h) => new Date(Date.now() - h * 3600_000).toISOString();

const item = (id, overrides = {}) => ({
  id,
  title: `글 ${id}`,
  url: `https://example.com/${id}`,
  excerpt: "요약",
  author: null,
  source: { slug: "src", name: "출처" },
  published_at: hoursAgo(2),
  collected_at: hoursAgo(1),
  score: null,
  comment_count: null,
  view_count: null,
  technologies: [],
  ...overrides,
});

const TRENDS = {
  scope: "news",
  days: 7,
  total: 3,
  fields: [{ slug: "security", name: "보안", count: 1 }],
  technologies: [{ slug: "python", name: "Python", count: 2 }],
  daily: [{ date: "2026-10-28", total: 3, counts: { python: 2 } }],
  daily_technologies: [{ slug: "python", name: "Python" }],
};

const STATUS = { scope: "news", last_updated_at: hoursAgo(0.5), stale: false, sources: [] };

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

const renderPage = (page) => render(<MemoryRouter>{page}</MemoryRouter>);

describe("relativeTime", () => {
  const now = new Date("2026-10-28T12:00:00Z");
  it.each([
    ["2026-10-28T11:59:40Z", "방금 전"],
    ["2026-10-28T11:15:00Z", "45분 전"],
    ["2026-10-28T09:00:00Z", "3시간 전"],
    ["2026-10-27T10:00:00Z", "어제"],
    ["2026-10-25T12:00:00Z", "3일 전"],
  ])("%s -> %s", (iso, text) => expect(relativeTime(iso, now)).toBe(text));
});

describe("News", () => {
  it("lists news without metrics, filters by technology and loads more", async () => {
    const requests = [];
    restore = installFakeServer({
      "GET /trends": () => [200, TRENDS],
      "GET /feed-status": () => [200, STATUS],
      "GET /news": (config) => {
        requests.push(config.params);
        if (config.params.tech === "python") return [200, { items: [item(9, { title: "파이썬 기사" })], page: 1, size: 12, total: 1 }];
        const page = config.params.page;
        return [200, { items: page === 1 ? [item(1), item(2)] : [item(3)], page, size: 12, total: 3 }];
      },
    });
    renderPage(<NewsPage />);

    const link = await screen.findByRole("link", { name: /글 1/ });
    expect(link.getAttribute("href")).toBe("https://example.com/1");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(screen.getAllByText("2시간 전")).toHaveLength(2);
    expect(screen.queryByText(/반응|댓글/)).toBeNull();
    expect(await screen.findByText(/마지막 갱신 30분 전/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "더 보기 (2/3)" }));
    expect(await screen.findByText("글 3")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /더 보기/ })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Python" }));
    expect(await screen.findByText("파이썬 기사")).toBeTruthy();
    expect(screen.queryByText("글 1")).toBeNull();
    expect(requests.at(-1)).toEqual({ page: 1, size: 12, tech: "python" });
    expect(screen.getByRole("button", { name: "Python" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("warns when collection is delayed or has never run", async () => {
    restore = installFakeServer({
      "GET /trends": () => [200, { ...TRENDS, total: 0, fields: [], technologies: [], daily: [], daily_technologies: [] }],
      "GET /feed-status": () => [200, { ...STATUS, last_updated_at: null, stale: true }],
      "GET /news": () => [200, { items: [], page: 1, size: 12, total: 0 }],
    });
    renderPage(<NewsPage />);
    expect(await screen.findByText("아직 수집된 기사가 없습니다.")).toBeTruthy();
    expect(await screen.findByText(/아직 수집된 기록이 없습니다/)).toBeTruthy();
    expect(screen.getAllByText("이 기간에 집계할 데이터가 없습니다.").length).toBeGreaterThan(0);
  });
});

describe("Dev", () => {
  const CHANNELS = {
    items: [
      { slug: "devto", name: "DEV Community", kind: "blog", has_metrics: true, sources: [{ slug: "devto", name: "DEV" }] },
      { slug: "stackoverflow", name: "Stack Overflow", kind: "qna", has_metrics: true, sources: [{ slug: "so", name: "SO" }] },
      { slug: "kr-techblog", name: "국내 기술블로그", kind: "blog", has_metrics: false, sources: [{ slug: "toss", name: "토스" }] },
    ],
  };

  it("switches channels, shows the right metric names and sorts by popularity", async () => {
    const calls = [];
    restore = installFakeServer({
      "GET /dev/channels": () => [200, CHANNELS],
      "GET /trends": () => [200, { ...TRENDS, scope: "dev" }],
      "GET /feed-status": () => [200, { ...STATUS, scope: "dev" }],
      "GET /dev/channels/devto/posts": (config) => {
        calls.push(["devto", config.params.sort]);
        return [200, { items: [item(1, { score: 42, comment_count: 0 })], page: 1, size: 12, total: 1 }];
      },
      "GET /dev/channels/stackoverflow/posts": () => [
        200,
        { items: [item(2, { score: 27, comment_count: 3, view_count: 1520 })], page: 1, size: 12, total: 1 },
      ],
      "GET /dev/channels/kr-techblog/posts": (config) => {
        calls.push(["kr-techblog", config.params.sort]);
        return [200, { items: [item(3)], page: 1, size: 12, total: 1 }];
      },
    });
    renderPage(<DevPage />);

    const card = (await screen.findByText("글 1")).closest("article");
    expect(within(card).getByText(/반응/).textContent).toContain("42");
    expect(within(card).getByText(/댓글/).textContent).toContain("0"); // a real zero is shown

    fireEvent.click(screen.getByRole("button", { name: "주간 인기" }));
    await waitFor(() => expect(calls).toContainEqual(["devto", "popular"]));

    fireEvent.click(screen.getByRole("tab", { name: "Stack Overflow" }));
    const question = (await screen.findByText("글 2")).closest("article");
    expect(within(question).getByText(/답변/).textContent).toContain("3");
    expect(within(question).getByText(/조회/).textContent).toContain("1,520");

    fireEvent.click(screen.getByRole("tab", { name: "국내 기술블로그" }));
    expect(await screen.findByText("글 3")).toBeTruthy();
    expect(screen.getByRole("button", { name: "주간 인기" }).disabled).toBe(true);
    expect(calls.at(-1)).toEqual(["kr-techblog", "latest"]);
  });

  const SUMMARY = {
    kind: "dev",
    partial_input: false,
    content: { headline: "요약 헤드라인", key_concepts: [], implementation: null, applicable_when: [], caveats: [] },
  };
  const LICENSE = { name: "CC BY 4.0", url: "https://creativecommons.org/licenses/by/4.0/" };
  const featured = (id) =>
    item(id, { title: `요약 글 ${id}`, ai_summary: SUMMARY, source: { slug: "webdev", name: "web.dev", license: LICENSE } });

  function devServer(featuredItems, boardRequests = []) {
    return installFakeServer({
      "GET /dev/channels": () => [200, CHANNELS],
      "GET /trends": () => [200, { ...TRENDS, scope: "dev" }],
      "GET /feed-status": () => [200, { ...STATUS, scope: "dev" }],
      "GET /dev/featured": () => [200, { items: featuredItems, page: 1, size: 2, total: featuredItems.length }],
      "GET /dev/channels/devto/posts": (config) => {
        boardRequests.push(config.params);
        const board = item(1, { excerpt: "게시판 소개문", ai_summary: SUMMARY });
        return [200, { items: [board], page: 1, size: 12, total: 1 }];
      },
    });
  }

  it.each([
    [0, []],
    [1, [featured(11)]],
    [2, [featured(11), featured(12)]],
  ])("shows %i AI-summarized article(s) on top and a link-only board below", async (count, items) => {
    const boardRequests = [];
    restore = devServer(items, boardRequests);
    renderPage(<DevPage />);

    const row = (await screen.findByText("글 1")).closest("article");
    // The board: title, source, date and link; never the excerpt or a summary.
    expect(within(row).queryByText("게시판 소개문")).toBeNull();
    expect(within(row).queryByRole("region", { name: "AI 요약" })).toBeNull();
    const link = within(row).getByRole("link", { name: /글 1/ });
    expect(link.getAttribute("href")).toBe("https://example.com/1");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(within(row).getByText("출처")).toBeTruthy();
    expect(within(row).getByRole("time")).toBeTruthy();
    // The board asks the API to leave the featured articles out (no duplicates).
    expect(boardRequests[0].exclude_featured).toBe(true);

    const top = screen.queryByRole("region", { name: "AI 요약 아티클" });
    if (count === 0) {
      expect(top).toBeNull();
      return;
    }
    await waitFor(() => expect(within(top).getAllByRole("article")).toHaveLength(count));
    expect(within(top).getAllByText("요약 헤드라인")).toHaveLength(count);
    expect(within(top).getAllByRole("link", { name: "CC BY 4.0" })).toHaveLength(count);
  });

  it("hides the top section when the featured list fails to load", async () => {
    restore = installFakeServer({
      "GET /dev/channels": () => [200, CHANNELS],
      "GET /dev/featured": () => [500, {}],
      "GET /dev/channels/devto/posts": () => [200, { items: [item(1)], page: 1, size: 12, total: 1 }],
    });
    renderPage(<DevPage />);
    expect(await screen.findByText("글 1")).toBeTruthy();
    expect(screen.queryByRole("region", { name: "AI 요약 아티클" })).toBeNull();
  });
});
