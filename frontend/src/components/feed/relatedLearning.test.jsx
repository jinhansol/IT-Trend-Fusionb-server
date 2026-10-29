import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { installFakeServer } from "../../test/fakeServer";
import DevPage from "../../pages/dev/DevPage";
import HomePage from "../../pages/home/HomePage";

// jsdom has no ResizeObserver; recharts' ResponsiveContainer needs one.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const TRENDS = {
  scope: "news",
  days: 7,
  total: 1,
  fields: [],
  technologies: [{ slug: "python", name: "Python", count: 1 }],
  daily: [],
  daily_technologies: [],
};
const STATUS = { scope: "news", last_updated_at: null, stale: false, sources: [] };
const EMPTY = { items: [], page: 1, size: 12, total: 0 };
const PYTHON_UNITS = {
  technology: { slug: "python", name: "Python" },
  units: [
    {
      track: { slug: "python", title: "Python 기초" },
      slug: "variables-and-types",
      position: 1,
      title: "변수와 자료형",
      summary: null,
      estimated_minutes: 40,
    },
  ],
};

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

const renderAt = (path, page) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      {page}
      <Location />
    </MemoryRouter>
  );

function homeServer({ newsRequests = [], unitRequests = [] } = {}) {
  return installFakeServer({
    "GET /trends": () => [200, TRENDS],
    "GET /feed-status": () => [200, STATUS],
    "GET /news": (config) => {
      newsRequests.push(config.params);
      return [200, EMPTY];
    },
    "GET /technologies/python/units": () => {
      unitRequests.push("python");
      return [200, PYTHON_UNITS];
    },
    "GET /technologies/rust/units": () => {
      unitRequests.push("rust");
      return [200, { technology: { slug: "rust", name: "Rust" }, units: [] }];
    },
  });
}

describe("technology filter in the URL and related learning", () => {
  it("shows no related learning without a selected technology", async () => {
    const unitRequests = [];
    restore = homeServer({ unitRequests });
    renderAt("/", <HomePage />);
    await screen.findByRole("button", { name: "Python" });
    expect(screen.queryByRole("region", { name: "관련 학습" })).toBeNull();
    expect(unitRequests).toEqual([]);
  });

  it("reads ?tech= from the URL, filters the news and links the units of that technology", async () => {
    const newsRequests = [];
    restore = homeServer({ newsRequests });
    renderAt("/?tech=python", <HomePage />);

    const card = await screen.findByRole("region", { name: "관련 학습" });
    expect(card.textContent).toContain("Python을(를) 다루는 Career 학습");
    const link = screen.getByRole("link", { name: "Python 기초 · 1. 변수와 자료형" });
    expect(link.getAttribute("href")).toBe("/career/python/variables-and-types");
    expect(newsRequests.at(-1)).toEqual({ page: 1, size: 12, tech: "python" });
    expect((await screen.findByRole("button", { name: "Python" })).getAttribute("aria-pressed")).toBe("true");
  });

  it("writes the chosen filter to the URL and clears it again", async () => {
    restore = homeServer();
    renderAt("/", <HomePage />);

    fireEvent.click(await screen.findByRole("button", { name: "Python" }));
    expect(screen.getByTestId("location").textContent).toBe("/?tech=python");
    expect(await screen.findByRole("region", { name: "관련 학습" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "전체" }));
    expect(screen.getByTestId("location").textContent).toBe("/");
    await waitFor(() => expect(screen.queryByRole("region", { name: "관련 학습" })).toBeNull());
  });

  it("keeps a linked technology outside the top list selectable, and hides the card when it has no units", async () => {
    const unitRequests = [];
    restore = homeServer({ unitRequests });
    renderAt("/?tech=rust", <HomePage />);

    const chip = await screen.findByRole("button", { name: "rust" });
    expect(chip.getAttribute("aria-pressed")).toBe("true");
    await waitFor(() => expect(unitRequests).toEqual(["rust"]));
    expect(screen.queryByRole("region", { name: "관련 학습" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "전체" }));
    expect(screen.getByTestId("location").textContent).toBe("/");
  });

  it("hides the card when the technology is unknown (404)", async () => {
    restore = homeServer();
    renderAt("/?tech=unknown-tech", <HomePage />);
    await screen.findByRole("button", { name: "unknown-tech" });
    expect(await screen.findByText("이 기술에 관한 기사가 아직 없습니다.")).toBeTruthy();
    expect(screen.queryByRole("region", { name: "관련 학습" })).toBeNull();
  });

  it("ignores a malformed ?tech= value", async () => {
    const newsRequests = [];
    const unitRequests = [];
    restore = homeServer({ newsRequests, unitRequests });
    renderAt("/?tech=..%2Fadmin", <HomePage />);
    await screen.findByText("아직 수집된 기사가 없습니다.");
    expect(newsRequests.at(-1)).toEqual({ page: 1, size: 12 });
    expect(unitRequests).toEqual([]);
    expect(screen.getByRole("button", { name: "전체" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("shows the same related learning on Dev for ?tech=", async () => {
    const postRequests = [];
    restore = installFakeServer({
      "GET /dev/channels": () => [
        200,
        { items: [{ slug: "devto", name: "DEV Community", kind: "blog", has_metrics: true, sources: [] }] },
      ],
      "GET /trends": () => [200, { ...TRENDS, scope: "dev" }],
      "GET /feed-status": () => [200, { ...STATUS, scope: "dev" }],
      "GET /dev/channels/devto/posts": (config) => {
        postRequests.push(config.params);
        return [200, EMPTY];
      },
      "GET /technologies/python/units": () => [200, PYTHON_UNITS],
    });
    renderAt("/dev?tech=python", <DevPage />);

    expect(await screen.findByRole("region", { name: "관련 학습" })).toBeTruthy();
    await waitFor(() => expect(postRequests.at(-1)?.tech).toBe("python"));
  });
});
