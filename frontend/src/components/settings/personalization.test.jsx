import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthContext } from "../../auth/AuthContext";
import SettingsPage from "../../pages/settings/SettingsPage";
import { installFakeServer } from "../../test/fakeServer";

const TECHNOLOGIES = [
  { slug: "backend", name: "백엔드", kind: "field" },
  { slug: "python", name: "Python", kind: "language" },
  { slug: "java", name: "Java", kind: "language" },
  { slug: "docker", name: "Docker", kind: "tool" },
];

const mine = (overrides = {}) => ({
  enabled: false,
  profile_status: "off",
  interests: [],
  skills: [],
  limits: { interests: 20, skills: 30 },
  ...overrides,
});

const MEMBER = {
  status: "authenticated",
  user: { id: 1, settings: { personalization_enabled: false, learner_type: null } },
  reloadUser: async () => {},
};

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

/** A small fake backend that remembers what was saved. */
function backend(initial = mine()) {
  let current = initial;
  const calls = [];
  const technology = (slug) => TECHNOLOGIES.find((t) => t.slug === slug);
  restore = installFakeServer({
    "GET /technologies": () => [200, { items: TECHNOLOGIES }],
    "GET /me/personalization": () => [200, current],
    "PATCH /me/settings": (config) => {
      const body = JSON.parse(config.data);
      calls.push(["PATCH", body]);
      current = { ...current, enabled: body.personalization_enabled, profile_status: body.personalization_enabled ? "empty" : "off" };
      return [200, { personalization_enabled: current.enabled, learner_type: null }];
    },
    "PUT /me/personalization/interests": (config) => {
      const body = JSON.parse(config.data);
      calls.push(["PUT interests", body]);
      current = { ...current, interests: body.technologies.map((s) => ({ ...technology(s), available: true })) };
      return [200, current];
    },
    "PUT /me/personalization/skills": (config) => {
      const body = JSON.parse(config.data);
      calls.push(["PUT skills", body]);
      current = {
        ...current,
        skills: body.skills.map((s) => ({ ...technology(s.technology), level: s.level, available: true })),
      };
      return [200, current];
    },
    "POST /me/personalization/reset": () => {
      calls.push(["RESET"]);
      current = { ...current, interests: [], skills: [] };
      return [204, null];
    },
  });
  return calls;
}

const renderSettings = () =>
  render(
    <AuthContext.Provider value={MEMBER}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );

const region = (name) => screen.getByRole("region", { name });

describe("personalization switch", () => {
  it("is OFF by default and says the data is not used", async () => {
    backend();
    renderSettings();
    const toggle = await screen.findByRole("switch", { name: "개인화" });
    expect(toggle.getAttribute("aria-checked")).toBe("false");
    expect(screen.getByText(/관심 기술과 역량은 저장되지만 추천에 사용되지 않습니다/)).toBeTruthy();
    expect(within(region("관심 기술")).getByText("개인화가 꺼져 있어 추천에 사용되지 않습니다.")).toBeTruthy();
  });

  it("explains what turning it ON means and changes nothing until confirmed", async () => {
    const calls = backend();
    renderSettings();
    fireEvent.click(await screen.findByRole("switch", { name: "개인화" }));
    const dialog = screen.getByRole("dialog", { name: "개인화 켜기 안내" });
    expect(dialog.textContent).toContain("향후 맞춤 추천에 사용할 수 있습니다");
    expect(dialog.textContent).toContain("현재는 개인화 추천 기능이 제공되지 않습니다");
    fireEvent.click(within(dialog).getByRole("button", { name: "취소" }));
    expect(calls).toEqual([]);

    fireEvent.click(screen.getByRole("switch", { name: "개인화" }));
    fireEvent.click(screen.getByRole("button", { name: "개인화 켜기" }));
    await waitFor(() => expect(screen.getByRole("switch", { name: "개인화" }).getAttribute("aria-checked")).toBe("true"));
    expect(calls).toEqual([["PATCH", { personalization_enabled: true }]]);
    expect(screen.getByText("개인화를 켰습니다.")).toBeTruthy();

    fireEvent.click(screen.getByRole("switch", { name: "개인화" })); // OFF needs no confirmation
    await waitFor(() => expect(screen.getByText(/개인화를 껐습니다. 저장한 데이터는 그대로/)).toBeTruthy());
    expect(calls.at(-1)).toEqual(["PATCH", { personalization_enabled: false }]);
  });
});

describe("interests", () => {
  it("groups technologies, searches and saves the whole selection", async () => {
    const calls = backend(mine({ interests: [{ slug: "java", name: "Java", kind: "language", available: true }] }));
    renderSettings();
    const section = await screen.findByRole("region", { name: "관심 기술" });
    expect(within(section).getByRole("group", { name: "언어" })).toBeTruthy();
    expect(within(section).getByRole("button", { name: "Java" }).getAttribute("aria-pressed")).toBe("true");

    fireEvent.change(within(section).getByRole("searchbox", { name: "관심 기술 검색" }), { target: { value: "pyth" } });
    expect(within(section).queryByRole("button", { name: "Java" })).toBeNull();
    fireEvent.click(within(section).getByRole("button", { name: "Python" }));
    fireEvent.click(within(section).getByRole("button", { name: "관심 기술 저장" }));
    expect(await within(section).findByText("관심 기술을 저장했습니다.")).toBeTruthy();
    expect(calls).toEqual([["PUT interests", { technologies: ["java", "python"] }]]);
  });

  it("stops at the limit and shows retired picks so they can be removed", async () => {
    backend(
      mine({
        limits: { interests: 2, skills: 30 },
        interests: [
          { slug: "python", name: "Python", kind: "language", available: true },
          { slug: "old-tech", name: "옛 기술", kind: "tool", available: false },
        ],
      })
    );
    renderSettings();
    const section = await screen.findByRole("region", { name: "관심 기술" });
    expect(within(section).getByRole("button", { name: "Java" }).disabled).toBe(true);
    expect(within(section).getByText("2/2")).toBeTruthy();
    fireEvent.click(within(section).getByRole("button", { name: /옛 기술 \(제공 중단\)/ }));
    expect(within(section).getByRole("button", { name: "Java" }).disabled).toBe(false);
  });
});

describe("skills", () => {
  it("adds a technology, rates it in three levels and saves", async () => {
    const calls = backend();
    renderSettings();
    const section = await screen.findByRole("region", { name: "역량 자기 평가" });
    expect(within(section).getByText("스스로 평가한 수준이며, 검증된 숙련도가 아닙니다.")).toBeTruthy();

    fireEvent.change(within(section).getByRole("combobox", { name: "평가할 기술 추가" }), { target: { value: "docker" } });
    const level = within(section).getByRole("combobox", { name: "Docker 역량" });
    expect([...level.options].map((o) => o.textContent)).toEqual(["배우는 중", "써 본 적 있음", "자신 있음"]);
    fireEvent.change(level, { target: { value: "used" } });
    fireEvent.click(within(section).getByRole("button", { name: "역량 저장" }));
    expect(await within(section).findByText("역량 자기 평가를 저장했습니다.")).toBeTruthy();
    expect(calls).toEqual([["PUT skills", { skills: [{ technology: "docker", level: "used" }] }]]);
  });
});

describe("reset", () => {
  const SAVED = mine({
    enabled: true,
    profile_status: "ready",
    interests: [{ slug: "python", name: "Python", kind: "language", available: true }],
    skills: [{ slug: "java", name: "Java", kind: "language", level: "used", available: true }],
  });

  it("lists what is deleted and kept, and does nothing on cancel", async () => {
    const calls = backend(SAVED);
    renderSettings();
    fireEvent.click(await screen.findByRole("button", { name: "개인화 데이터 초기화" }));
    const dialog = screen.getByRole("dialog", { name: "개인화 데이터 초기화 확인" });
    const deleted = within(dialog).getByRole("list", { name: "삭제되는 항목" });
    const kept = within(dialog).getByRole("list", { name: "유지되는 항목" });
    expect([...deleted.children].map((li) => li.textContent)).toEqual(["관심 기술", "역량 자기 평가"]);
    expect([...kept.children].map((li) => li.textContent)).toEqual([
      "개인화 켜짐/꺼짐 상태",
      "학습 목표",
      "진로 후보",
      "학습 진행률",
      "XP",
      "학습자 유형",
    ]);
    fireEvent.click(within(dialog).getByRole("button", { name: "취소" }));
    expect(calls).toEqual([]);
  });

  it("clears interests and skills after confirmation and keeps the switch", async () => {
    const calls = backend(SAVED);
    renderSettings();
    fireEvent.click(await screen.findByRole("button", { name: "개인화 데이터 초기화" }));
    fireEvent.click(screen.getByRole("button", { name: "초기화" }));
    expect(await screen.findByText(/초기화했습니다/)).toBeTruthy();
    expect(calls).toEqual([["RESET"]]);
    expect(within(region("관심 기술")).getByRole("button", { name: "Python" }).getAttribute("aria-pressed")).toBe("false");
    expect(within(region("역량 자기 평가")).getByText("아직 평가한 기술이 없습니다.")).toBeTruthy();
    expect(screen.getByRole("switch", { name: "개인화" }).getAttribute("aria-checked")).toBe("true");
  });

  it("reports a failed reset", async () => {
    backend(SAVED);
    restore();
    restore = installFakeServer({
      "GET /technologies": () => [200, { items: TECHNOLOGIES }],
      "GET /me/personalization": () => [200, SAVED],
      "POST /me/personalization/reset": () => [500, { error: { code: "INTERNAL_ERROR" } }],
    });
    renderSettings();
    fireEvent.click(await screen.findByRole("button", { name: "개인화 데이터 초기화" }));
    fireEvent.click(screen.getByRole("button", { name: "초기화" }));
    expect(await screen.findByText(/초기화하지 못했습니다. 아무것도 삭제되지 않았어요/)).toBeTruthy();
  });
});

it("shows a load error without breaking the rest of the settings page", async () => {
  restore = installFakeServer({ "GET /technologies": () => [200, { items: TECHNOLOGIES }] });
  renderSettings();
  expect(await screen.findByText("개인화 설정을 불러오지 못했습니다.")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "학습자 유형" })).toBeTruthy();
});

describe("keyboard use of the confirmation panels", () => {
  it("moves focus into the reset confirmation, closes on Escape and returns focus", async () => {
    const calls = backend(mine({ interests: [{ slug: "python", name: "Python", kind: "language", available: true }] }));
    renderSettings();
    fireEvent.click(await screen.findByRole("button", { name: "개인화 데이터 초기화" }));
    const dialog = screen.getByRole("dialog", { name: "개인화 데이터 초기화 확인" });
    await waitFor(() => expect(document.activeElement).toBe(within(dialog).getByRole("button", { name: "취소" })));

    fireEvent.keyDown(document.activeElement, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "개인화 데이터 초기화 확인" })).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("button", { name: "개인화 데이터 초기화" })));
    expect(calls).toEqual([]);
  });

  it("moves focus into the ON confirmation and back to the switch on Escape", async () => {
    const calls = backend();
    renderSettings();
    fireEvent.click(await screen.findByRole("switch", { name: "개인화" }));
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("button", { name: "개인화 켜기" })));
    fireEvent.keyDown(document.activeElement, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "개인화 켜기 안내" })).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("switch", { name: "개인화" })));
    expect(calls).toEqual([]);
  });
});
