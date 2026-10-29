import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthContext } from "../../auth/AuthContext";
import { installFakeServer } from "../../test/fakeServer";
import ExplorePage from "./ExplorePage";
import RolePage from "./RolePage";

const ROLES = [
  {
    slug: "backend-dev",
    name: "백엔드 개발자",
    summary: "서버를 만듭니다.",
    core_technologies: [{ slug: "python", name: "Python" }],
    technology_count: 2,
  },
  { slug: "frontend-dev", name: "프론트엔드 개발자", summary: "화면을 만듭니다.", core_technologies: [], technology_count: 0 },
];

const ROLE = {
  slug: "backend-dev",
  name: "백엔드 개발자",
  summary: "서버를 만듭니다.",
  description_md: "**API**를 만듭니다.",
  tasks: ["API 설계", "장애 대응"],
  references: [{ title: "근거 자료", url: "https://example.com/source" }],
  technologies: [
    {
      slug: "python",
      name: "Python",
      importance: "core",
      units: [
        {
          track: { slug: "python", title: "Python 기초" },
          slug: "variables",
          position: 1,
          title: "변수",
          summary: null,
          estimated_minutes: 40,
        },
      ],
    },
    { slug: "docker", name: "Docker", importance: "related", units: [] },
  ],
};

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

const ANONYMOUS = { status: "anonymous", user: null };
const MEMBER = { status: "authenticated", user: { id: 1, settings: { personalization_enabled: false, learner_type: null } } };

function renderAt(path, auth = ANONYMOUS) {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/career/explore" element={<ExplorePage />} />
          <Route path="/career/roles/:roleSlug" element={<RolePage />} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>
  );
}

describe("career exploration", () => {
  it("lists roles in the order the server gives, with links to each role", async () => {
    restore = installFakeServer({ "GET /careers/roles": () => [200, { items: ROLES }] });
    renderAt("/career/explore");
    const links = await screen.findAllByRole("link", { name: /자세히 보기/ });
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["/career/roles/backend-dev", "/career/roles/frontend-dev"]);
    expect(within(screen.getByRole("list", { name: "백엔드 개발자 핵심 기술" })).getByText("Python")).toBeTruthy();
  });

  it("shows an empty state when no role is published", async () => {
    restore = installFakeServer({ "GET /careers/roles": () => [200, { items: [] }] });
    renderAt("/career/explore");
    expect(await screen.findByText("아직 공개된 직무 정보가 없습니다.")).toBeTruthy();
  });

  it("shows what the role does, its technologies and the Career units for each", async () => {
    restore = installFakeServer({ "GET /careers/roles/backend-dev": () => [200, ROLE] });
    renderAt("/career/roles/backend-dev");

    expect(await screen.findByRole("heading", { name: "백엔드 개발자" })).toBeTruthy();
    expect(screen.getByText("API 설계")).toBeTruthy();
    const core = screen.getByRole("region", { name: "핵심 기술" });
    expect(within(core).getByRole("link", { name: "Python 기초 · 1. 변수" }).getAttribute("href")).toBe(
      "/career/python/variables"
    );
    expect(within(core).getByRole("link", { name: "IT 뉴스" }).getAttribute("href")).toBe("/?tech=python");
    expect(within(core).getByRole("link", { name: "Dev 글" }).getAttribute("href")).toBe("/dev?tech=python");
    const related = screen.getByRole("region", { name: "함께 쓰는 기술" });
    expect(within(related).getByText("아직 이 기술을 다루는 Career 학습이 없습니다.")).toBeTruthy();

    const source = screen.getByRole("link", { name: /근거 자료/ });
    expect(source.getAttribute("href")).toBe("https://example.com/source");
    expect(source.getAttribute("rel")).toContain("noopener");
  });

  it("shows a not-found message for unknown roles", async () => {
    restore = installFakeServer({
      "GET /careers/roles/nope": () => [404, { error: { code: "CAREER_ROLE_NOT_FOUND", message: "x" } }],
    });
    renderAt("/career/roles/nope");
    expect(await screen.findByText("찾을 수 없는 직무입니다.")).toBeTruthy();
  });
});

describe("saving a role as a career candidate", () => {
  it("asks guests to log in and sends nothing", async () => {
    const writes = [];
    restore = installFakeServer({
      "GET /careers/roles/backend-dev": () => [200, ROLE],
      "PUT /me/career-candidates/backend-dev": () => writes.push("put") && [200, {}],
    });
    renderAt("/career/roles/backend-dev");
    expect(await screen.findByText(/진로 후보로 저장하거나 학습 목표로 삼을 수 있어요/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /진로 후보에 저장/ })).toBeNull();
    expect(writes).toEqual([]);
  });

  it("saves and removes the role for a member", async () => {
    const calls = [];
    restore = installFakeServer({
      "GET /careers/roles/backend-dev": () => [200, ROLE],
      "GET /me/career-candidates": () => [200, { items: [], limit: 10 }],
      "PUT /me/career-candidates/backend-dev": (config) => {
        calls.push(["PUT", JSON.parse(config.data)]);
        return [200, {}];
      },
      "DELETE /me/career-candidates/backend-dev": () => {
        calls.push(["DELETE"]);
        return [204, null];
      },
    });
    renderAt("/career/roles/backend-dev", MEMBER);

    fireEvent.click(await screen.findByRole("button", { name: "진로 후보에 저장" }));
    const saved = await screen.findByRole("button", { name: "진로 후보에 저장됨" });
    expect(saved.getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(saved);
    await screen.findByRole("button", { name: "진로 후보에 저장" });
    expect(calls).toEqual([["PUT", { note: null }], ["DELETE"]]);
  });

  it("shows an already saved role as saved and explains the limit", async () => {
    restore = installFakeServer({
      "GET /careers/roles/frontend-dev": () => [200, { ...ROLE, slug: "frontend-dev" }],
      "GET /careers/roles/backend-dev": () => [200, ROLE],
      "GET /me/career-candidates": () => [
        200,
        { items: [{ role: { slug: "backend-dev", name: "백엔드 개발자", available: true }, note: null, saved_at: "2026-10-29T00:00:00Z" }], limit: 10 },
      ],
      "PUT /me/career-candidates/frontend-dev": () => [409, { error: { code: "CANDIDATE_LIMIT", message: "x" } }],
    });
    renderAt("/career/roles/backend-dev", MEMBER);
    expect((await screen.findByRole("button", { name: "진로 후보에 저장됨" })).getAttribute("aria-pressed")).toBe("true");
    cleanup();

    renderAt("/career/roles/frontend-dev", MEMBER);
    fireEvent.click(await screen.findByRole("button", { name: "진로 후보에 저장" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("최대 10개"));
  });
});
