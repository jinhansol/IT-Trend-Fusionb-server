import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthContext } from "../../auth/AuthContext";
import { installFakeServer } from "../../test/fakeServer";
import CareerHomePage from "./CareerHomePage";
import GoalsPage from "./GoalsPage";
import RolePage from "./RolePage";

const ROLE = {
  slug: "backend-dev",
  name: "백엔드 개발자",
  summary: "서버를 만듭니다.",
  description_md: "설명",
  tasks: ["API 설계"],
  references: [{ title: "근거", url: "https://example.com" }],
  technologies: [],
};

const goal = (id, overrides = {}) => ({
  id,
  title: `목표 ${id}`,
  status: "active",
  target_date: null,
  achieved_at: null,
  created_at: "2026-10-29T00:00:00Z",
  target: null,
  units: [],
  ...overrides,
});

const ROLE_GOAL = goal(1, {
  title: "백엔드 개발자 되기",
  target: { kind: "role", slug: "backend-dev", name: "백엔드 개발자", available: true },
  units: [
    { track: { slug: "python", title: "Python 기초" }, slug: "variables", position: 1, title: "변수", state: "completed" },
    { track: { slug: "python", title: "Python 기초" }, slug: "loops", position: 2, title: "반복문", state: "not_started" },
  ],
});

let restore;
afterEach(() => {
  cleanup();
  restore?.();
  vi.restoreAllMocks();
});

const MEMBER = { status: "authenticated", user: { id: 1, settings: { personalization_enabled: false, learner_type: null } } };
const ANONYMOUS = { status: "anonymous", user: null };

function renderAt(path, auth = MEMBER) {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/career" element={<CareerHomePage />} />
          <Route path="/career/goals" element={<GoalsPage />} />
          <Route path="/career/roles/:roleSlug" element={<RolePage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("adding a goal from a role", () => {
  it("only pre-fills a form; the goal is created when the user saves it", async () => {
    const posts = [];
    restore = installFakeServer({
      "GET /careers/roles/backend-dev": () => [200, ROLE],
      "GET /me/career-candidates": () => [200, { items: [], limit: 10 }],
      "POST /me/goals": (config) => {
        posts.push(JSON.parse(config.data));
        return [201, ROLE_GOAL];
      },
    });
    renderAt("/career/roles/backend-dev");

    fireEvent.click(await screen.findByRole("button", { name: "학습 목표로 추가" }));
    const form = screen.getByRole("form", { name: "학습 목표 추가" });
    expect(within(form).getByLabelText("목표").value).toBe("백엔드 개발자 되기");
    expect(posts).toEqual([]); // nothing is saved by opening the form

    fireEvent.click(within(form).getByRole("button", { name: "목표 저장" }));
    expect(await screen.findByRole("status")).toBeTruthy();
    expect(posts).toEqual([{ title: "백엔드 개발자 되기", role: "backend-dev", target_date: null }]);
  });

  it("explains the active goal limit", async () => {
    restore = installFakeServer({
      "GET /careers/roles/backend-dev": () => [200, ROLE],
      "GET /me/career-candidates": () => [200, { items: [], limit: 10 }],
      "POST /me/goals": () => [409, { error: { code: "GOAL_LIMIT", message: "x" } }],
    });
    renderAt("/career/roles/backend-dev");
    fireEvent.click(await screen.findByRole("button", { name: "학습 목표로 추가" }));
    fireEvent.click(screen.getByRole("button", { name: "목표 저장" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("최대 5개"));
  });
});

describe("goals page", () => {
  it("asks guests to log in and loads nothing personal", async () => {
    const requests = [];
    restore = installFakeServer({ "GET /me/goals": () => requests.push("goals") && [200, {}] });
    renderAt("/career/goals", ANONYMOUS);
    expect(await screen.findByText(/학습 목표와 진로 후보를 저장하고 관리할 수 있어요/)).toBeTruthy();
    expect(requests).toEqual([]);
  });

  it("groups goals, shows linked learning with my progress and changes status on click", async () => {
    const patches = [];
    let items = [ROLE_GOAL, goal(2, { status: "achieved", achieved_at: "2026-10-29T01:00:00Z" }), goal(3, {
      status: "archived",
      target: { kind: "technology", slug: "rust", name: "Rust", available: false },
    })];
    restore = installFakeServer({
      "GET /me/goals": () => [200, { items, active_limit: 5 }],
      "PATCH /me/goals/1": (config) => {
        patches.push(JSON.parse(config.data));
        items = items.map((g) => (g.id === 1 ? { ...g, status: "achieved" } : g));
        return [200, items[0]];
      },
      "DELETE /me/goals/3": () => {
        items = items.filter((g) => g.id !== 3);
        return [204, null];
      },
      "GET /me/career-candidates": () => [
        200,
        { items: [{ role: { slug: "old-role", name: "옛 직무", available: false }, note: "메모", saved_at: "2026-10-29T00:00:00Z" }], limit: 10 },
      ],
    });
    renderAt("/career/goals");

    const active = await screen.findByRole("region", { name: "진행 중인 목표" });
    const card = within(active).getByRole("article", { name: "목표: 백엔드 개발자 되기" });
    expect(within(card).getByRole("link", { name: "직무: 백엔드 개발자" }).getAttribute("href")).toBe("/career/roles/backend-dev");
    expect(within(card).getByText("연결된 Career 학습 1/2 완료")).toBeTruthy();
    expect(within(card).getByRole("link", { name: /Python 기초 · 2. 반복문/ }).getAttribute("href")).toBe("/career/python/loops");
    expect(screen.getByText("Rust", { exact: false }).textContent).toContain("더 이상 제공되지 않음");
    expect(await screen.findByText("옛 직무 (더 이상 제공되지 않음)")).toBeTruthy();

    fireEvent.click(within(card).getByRole("button", { name: "달성으로 표시" }));
    await waitFor(() => expect(screen.getByRole("region", { name: "달성한 목표" }).textContent).toContain("백엔드 개발자 되기"));
    expect(patches).toEqual([{ status: "achieved" }]);

    vi.spyOn(window, "confirm").mockReturnValue(true);
    const archived = screen.getByRole("region", { name: "보관한 목표" });
    fireEvent.click(within(archived).getByRole("button", { name: "삭제" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "보관한 목표" })).toBeNull());
  });

  it("does not delete when the user cancels the confirmation", async () => {
    const deletes = [];
    restore = installFakeServer({
      "GET /me/goals": () => [200, { items: [goal(4)], active_limit: 5 }],
      "DELETE /me/goals/4": () => deletes.push(4) && [204, null],
      "GET /me/career-candidates": () => [200, { items: [], limit: 10 }],
    });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderAt("/career/goals");
    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));
    expect(deletes).toEqual([]);
  });
});

describe("Career home", () => {
  it("shows my active goals to members only", async () => {
    const requests = [];
    restore = installFakeServer({
      "GET /tracks": () => [200, { items: [] }],
      "GET /me/summary": () => [500, {}],
      "GET /me/goals": (config) => {
        requests.push(config.params);
        return [200, { items: [ROLE_GOAL], active_limit: 5 }];
      },
    });
    renderAt("/career");
    expect(await screen.findByRole("article", { name: "목표: 백엔드 개발자 되기" })).toBeTruthy();
    expect(requests).toEqual([{ status: "active" }]);
    expect(screen.getByRole("link", { name: /진로 탐색/ }).getAttribute("href")).toBe("/career/explore");
    cleanup();

    requests.length = 0;
    renderAt("/career", ANONYMOUS);
    await screen.findByText("아직 공개된 학습 트랙이 없습니다.");
    expect(screen.queryByRole("heading", { name: "내 학습 목표" })).toBeNull();
    expect(requests).toEqual([]);
  });
});
