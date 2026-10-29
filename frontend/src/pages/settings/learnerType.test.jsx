import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setAccessToken } from "../../api/client";
import { AuthContext } from "../../auth/AuthContext";
import { AuthProvider } from "../../auth/AuthProvider";
import SignupPopup from "../../modals/SignupPopup";
import { installFakeServer } from "../../test/fakeServer";
import { START_GUIDES } from "../../learner/learnerTypes";
import CareerHomePage from "../career/CareerHomePage";
import SettingsPage from "./SettingsPage";

const user = (learnerType) => ({
  id: 1,
  email: "a@example.com",
  display_name: "A",
  role: "user",
  created_at: "2026-10-28T00:00:00",
  settings: { personalization_enabled: false, learner_type: learnerType },
});

let restore;
beforeEach(() => setAccessToken(null));
afterEach(() => {
  cleanup();
  restore?.();
});

describe("sign-up learner type", () => {
  function signUp(choose) {
    const bodies = [];
    restore = installFakeServer({
      "POST /auth/refresh": () => [401, { error: { code: "REFRESH_TOKEN_INVALID" } }],
      "POST /auth/register": (config) => {
        bodies.push(JSON.parse(config.data));
        return [201, { access_token: "t", token_type: "bearer", expires_in: 900, user: user(null) }];
      },
      "GET /me": () => [200, user(null)],
    });
    const onClose = vi.fn();
    render(
      <AuthProvider>
        <SignupPopup onClose={onClose} onSwitch={() => {}} />
      </AuthProvider>
    );
    fireEvent.change(document.querySelector('input[name="email"]'), { target: { value: "a@example.com" } });
    fireEvent.change(document.querySelector('input[name="password"]'), { target: { value: "correct horse 1" } });
    fireEvent.change(document.querySelector('input[name="displayName"]'), { target: { value: "A" } });
    choose?.();
    fireEvent.click(screen.getByRole("button", { name: "가입하기" }));
    return { bodies, onClose };
  }

  it("signs up without a type, exactly like before", async () => {
    const { bodies, onClose } = signUp();
    expect(screen.getByRole("radio", { name: /선택 안 함/ }).checked).toBe(true);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodies).toEqual([{ email: "a@example.com", password: "correct horse 1", display_name: "A" }]);
  });

  it("sends the chosen type", async () => {
    const { bodies, onClose } = signUp(() => fireEvent.click(screen.getByRole("radio", { name: /입문자/ })));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(bodies[0].learner_type).toBe("beginner");
  });
});

describe("settings page", () => {
  it("changes and clears the learner type, then reloads the user", async () => {
    const patches = [];
    restore = installFakeServer({
      "PATCH /me/settings": (config) => {
        patches.push(JSON.parse(config.data));
        return [200, { personalization_enabled: false, learner_type: patches.at(-1).learner_type }];
      },
    });
    // Like AuthProvider: reloading replaces the user object with the saved value.
    let rerenderWith;
    const reloadUser = vi.fn(async () => rerenderWith(user(patches.at(-1).learner_type)));
    const view = (current) => (
      <AuthContext.Provider value={{ status: "authenticated", user: current, reloadUser }}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </AuthContext.Provider>
    );
    const { rerender } = render(view(user("beginner")));
    rerenderWith = (current) => rerender(view(current));

    expect(screen.getByRole("radio", { name: /입문자/ }).checked).toBe(true);
    expect(screen.getByRole("button", { name: "저장" }).disabled).toBe(true); // nothing changed yet

    fireEvent.click(screen.getByRole("radio", { name: /개발자/ }));
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    expect(await screen.findByText("저장했습니다.")).toBeTruthy();

    fireEvent.click(screen.getByRole("radio", { name: /선택 안 함/ }));
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() => expect(patches).toHaveLength(2));
    expect(patches).toEqual([{ learner_type: "developer" }, { learner_type: null }]);
    expect(reloadUser).toHaveBeenCalledTimes(2);
  });

  it("asks guests to log in", () => {
    render(
      <AuthContext.Provider value={{ status: "anonymous", user: null }}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </AuthContext.Provider>
    );
    expect(screen.getByText("설정은 로그인한 뒤 바꿀 수 있어요.")).toBeTruthy();
  });
});

describe("Career start guide", () => {
  const SUMMARY = {
    xp: { total: 0, level: 1, xp_into_level: 0, xp_for_next_level: 100 },
    completed_units: 0,
    in_progress_units: 0,
    passed_quizzes: 0,
    continue_unit: null,
  };

  function renderCareer(auth) {
    const calls = [];
    restore = installFakeServer({
      "GET /tracks": (config) => {
        calls.push(config.url);
        return [200, { items: [{ slug: "python", title: "Python 기초", description: null, unit_count: 1 }] }];
      },
      "GET /me/summary": () => [200, SUMMARY],
      "GET /me/tracks/python/progress": () => [200, { track_slug: "python", completed_units: 0, total_units: 1, units: [] }],
    });
    render(
      <AuthContext.Provider value={auth}>
        <MemoryRouter>
          <CareerHomePage />
        </MemoryRouter>
      </AuthContext.Provider>
    );
    return calls;
  }

  it.each([
    ["guest", { status: "anonymous", user: null }, START_GUIDES.common],
    ["member without a type", { status: "authenticated", user: user(null) }, START_GUIDES.common],
    ["beginner", { status: "authenticated", user: user("beginner") }, START_GUIDES.beginner],
    ["developer", { status: "authenticated", user: user("developer") }, START_GUIDES.developer],
    ["exploring", { status: "authenticated", user: user("exploring") }, START_GUIDES.exploring],
  ])("%s sees the matching static guide", async (_label, auth, guide) => {
    renderCareer(auth);
    const section = await screen.findByRole("region", { name: "시작 안내" });
    expect(section.textContent).toContain(guide.title);
    expect(await screen.findByRole("link", { name: /Python 기초/ })).toBeTruthy();
  });

  it("does not change the track list or its requests", async () => {
    const guestCalls = renderCareer({ status: "anonymous", user: null });
    await screen.findByRole("link", { name: /Python 기초/ });
    const guestTracks = screen.getAllByRole("listitem").map((li) => li.textContent);
    cleanup();
    restore();
    const memberCalls = renderCareer({ status: "authenticated", user: user("developer") });
    await screen.findByRole("link", { name: /Python 기초/ });
    const memberTracks = screen.getAllByRole("listitem").map((li) => li.textContent.replace(/완료 \d+ \/ \d+/, ""));
    expect(memberCalls).toEqual(guestCalls); // same public request, no type parameter
    expect(memberTracks.map((t) => t.slice(0, 20))).toEqual(guestTracks.map((t) => t.slice(0, 20)));
  });
});
