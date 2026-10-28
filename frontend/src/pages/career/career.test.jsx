import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthContext } from "../../auth/AuthContext";
import { installFakeServer } from "../../test/fakeServer";
import CareerHomePage from "./CareerHomePage";
import TrackPage from "./TrackPage";
import UnitPage from "./UnitPage";

const UNIT = {
  slug: "variables",
  position: 1,
  title: "변수",
  summary: "요약",
  estimated_minutes: 40,
  track: { slug: "python", title: "Python 기초" },
  activities: [
    {
      id: 1,
      slug: "read",
      position: 1,
      kind: "reading",
      title: "읽을거리",
      url: null,
      body_md: "| 자료형 | 예 |\n|---|---|\n| `int` | 42 |\n\n<script>window.injected = true</script><img src=x onerror=\"window.injected=true\">",
      is_required: true,
    },
    {
      id: 2,
      slug: "docs",
      position: 2,
      kind: "external",
      title: "공식 문서",
      url: "https://example.com/docs",
      body_md: null,
      is_required: false,
    },
  ],
  prev: null,
  next: { slug: "loops", title: "반복문" },
};

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

const ANONYMOUS = { status: "anonymous", user: null };

function renderAt(path, auth = ANONYMOUS) {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/career" element={<CareerHomePage />} />
          <Route path="/career/:trackSlug" element={<TrackPage />} />
          <Route path="/career/:trackSlug/:unitSlug" element={<UnitPage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("career learning pages", () => {
  it("lists tracks with links", async () => {
    restore = installFakeServer({
      "GET /tracks": () => [200, { items: [{ slug: "python", title: "Python 기초", description: "d", unit_count: 1 }] }],
    });
    renderAt("/career");
    const link = await screen.findByRole("link", { name: /Python 기초/ });
    expect(link.getAttribute("href")).toBe("/career/python");
    expect(screen.getByText("단원 1개")).toBeTruthy();
  });

  it("lists the units of a track in order", async () => {
    restore = installFakeServer({
      "GET /tracks/python": () => [
        200,
        {
          slug: "python",
          title: "Python 기초",
          description: null,
          units: [
            { slug: "a", position: 1, title: "첫 단원", summary: null, estimated_minutes: 10, activity_count: 2 },
            { slug: "b", position: 2, title: "둘째 단원", summary: null, estimated_minutes: null, activity_count: 1 },
          ],
        },
      ],
    });
    renderAt("/career/python");
    const links = await screen.findAllByRole("link", { name: /단원/ });
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["/career/python/a", "/career/python/b"]);
  });

  it("renders activities with markdown tables and drops raw HTML", async () => {
    restore = installFakeServer({ "GET /tracks/python/units/variables": () => [200, UNIT] });
    const { container } = renderAt("/career/python/variables");

    await screen.findByText("읽을거리");
    expect(container.querySelector("table")).not.toBeNull();
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(window.injected).toBeUndefined();

    const docsLink = screen.getByRole("link", { name: /자료 열기/ });
    expect(docsLink.getAttribute("href")).toBe("https://example.com/docs");
    expect(docsLink.getAttribute("rel")).toContain("noopener");
    expect(screen.getByText("필수")).toBeTruthy();
    expect(screen.getByText("선택")).toBeTruthy();
    expect(screen.getByRole("link", { name: /반복문/ }).getAttribute("href")).toBe("/career/python/loops");
  });

  it("shows a not-found message for unknown units", async () => {
    restore = installFakeServer({
      "GET /tracks/python/units/nope": () => [404, { error: { code: "UNIT_NOT_FOUND", message: "x" } }],
    });
    renderAt("/career/python/nope");
    expect(await screen.findByText("찾을 수 없는 단원입니다.")).toBeTruthy();
  });

  it("shows a generic error when the server fails", async () => {
    restore = installFakeServer({ "GET /tracks": () => [500, { error: { code: "INTERNAL_ERROR" } }] });
    renderAt("/career");
    expect(await screen.findByText(/불러오지 못했습니다/)).toBeTruthy();
  });
});
