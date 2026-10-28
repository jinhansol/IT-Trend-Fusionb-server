import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthContext } from "../../auth/AuthContext";
import { installFakeServer } from "../../test/fakeServer";
import CareerHomePage from "./CareerHomePage";
import TrackPage from "./TrackPage";
import UnitPage from "./UnitPage";

const ANONYMOUS = { status: "anonymous", user: null };
const ALICE = { status: "authenticated", user: { id: 1, display_name: "Alice" } };

const XP_ZERO = { total: 0, level: 1, xp_into_level: 0, xp_for_next_level: 100 };
const XP_AFTER = { total: 100, level: 2, xp_into_level: 0, xp_for_next_level: 150 };

const UNIT = {
  slug: "variables",
  position: 1,
  title: "변수",
  summary: null,
  estimated_minutes: null,
  track: { slug: "python", title: "Python 기초" },
  activities: [
    { id: 11, slug: "read", position: 1, kind: "reading", title: "읽을거리", url: null, body_md: "본문", is_required: true },
  ],
  prev: null,
  next: null,
  quiz: { id: 7, question_count: 2, pass_score_percent: 80 },
};

const QUIZ = {
  id: 7,
  version: 1,
  pass_score_percent: 80,
  questions: [
    { id: 101, position: 1, type: "single", prompt: "첫 문제", choices: [{ id: 1, label: "정답A" }, { id: 2, label: "오답A" }] },
    {
      id: 102,
      position: 2,
      type: "multiple",
      prompt: "둘째 문제",
      choices: [{ id: 3, label: "정답B" }, { id: 4, label: "정답C" }, { id: 5, label: "오답B" }],
    },
  ],
};

const progress = (overrides = {}) => ({
  unit_slug: "variables",
  state: "in_progress",
  activities_done: 0,
  activities_required: 1,
  quiz_passed: false,
  has_quiz: true,
  completed_at: null,
  ...overrides,
});

let restore;
afterEach(() => {
  cleanup();
  restore?.();
});

function renderAt(path, auth) {
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

const choose = (label) => fireEvent.click(screen.getByRole("radio", { name: label }));
const check = (label) => fireEvent.click(screen.getByRole("checkbox", { name: label }));
const click = (name) => fireEvent.click(screen.getByRole("button", { name }));

describe("career hub progress", () => {
  it("asks anonymous visitors to log in and never calls /me", async () => {
    const calls = [];
    restore = installFakeServer({
      "GET /tracks": () => [200, { items: [{ slug: "python", title: "Python 기초", description: null, unit_count: 1 }] }],
      "GET /me/summary": () => calls.push("summary") && [401, {}],
    });
    renderAt("/career", ANONYMOUS);
    await screen.findByText("Python 기초");
    expect(screen.getByText(/로그인하면 내 학습 현황/)).toBeTruthy();
    expect(calls).toEqual([]);
  });

  it("shows level, counts and the unit to continue", async () => {
    restore = installFakeServer({
      "GET /tracks": () => [200, { items: [{ slug: "python", title: "Python 기초", description: null, unit_count: 2 }] }],
      "GET /me/summary": () => [
        200,
        {
          xp: { total: 130, level: 2, xp_into_level: 30, xp_for_next_level: 150 },
          completed_units: 1,
          in_progress_units: 1,
          passed_quizzes: 1,
          continue_unit: {
            track_slug: "python",
            track_title: "Python 기초",
            unit_slug: "loops",
            unit_title: "반복문",
            activities_done: 1,
            activities_required: 3,
            quiz_passed: false,
          },
        },
      ],
      "GET /me/tracks/python/progress": () => [
        200,
        { track_slug: "python", completed_units: 1, total_units: 2, units: [] },
      ],
    });
    renderAt("/career", ALICE);

    expect(await screen.findByText("Lv 2")).toBeTruthy();
    expect(screen.getByText(/30 \/ 150 XP · 누적 130 XP/)).toBeTruthy();
    const continueLink = screen.getByRole("link", { name: /이어서 학습하기/ });
    expect(continueLink.getAttribute("href")).toBe("/career/python/loops");
    expect(continueLink.textContent).toContain("필수 활동 1/3");
    expect(await screen.findByText("완료 1 / 2")).toBeTruthy();
  });

  it("marks each unit with the learner's state on the track page", async () => {
    restore = installFakeServer({
      "GET /tracks/python": () => [
        200,
        {
          slug: "python",
          title: "Python 기초",
          description: null,
          units: [
            { slug: "a", position: 1, title: "첫 단원", summary: null, estimated_minutes: null, activity_count: 1 },
            { slug: "b", position: 2, title: "둘째 단원", summary: null, estimated_minutes: null, activity_count: 1 },
          ],
        },
      ],
      "GET /me/tracks/python/progress": () => [
        200,
        {
          track_slug: "python",
          completed_units: 1,
          total_units: 2,
          units: [progress({ unit_slug: "a", state: "completed" }), progress({ unit_slug: "b", state: "not_started" })],
        },
      ],
    });
    renderAt("/career/python", ALICE);
    expect(await screen.findByText("완료")).toBeTruthy();
    expect(screen.getByText("시작 전")).toBeTruthy();
    expect(screen.getByText("완료한 단원 1 / 2")).toBeTruthy();
  });
});

describe("unit progress", () => {
  it("shows no confirm buttons or quiz to anonymous visitors", async () => {
    restore = installFakeServer({ "GET /tracks/python/units/variables": () => [200, UNIT] });
    renderAt("/career/python/variables", ANONYMOUS);
    await screen.findByText("읽을거리");
    expect(screen.getByText(/로그인하면 학습 기록과 퀴즈 결과가 저장/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /학습 완료로 표시/ })).toBeNull();
    expect(screen.queryByText("단원 퀴즈")).toBeNull();
  });

  it("confirms an activity and shows the server's progress", async () => {
    const posted = [];
    restore = installFakeServer({
      "GET /tracks/python/units/variables": () => [200, UNIT],
      "GET /me/tracks/python/units/variables/progress": () => [
        200,
        { progress: progress({ state: "not_started" }), confirmed_activity_ids: [], quiz: { passed: false, attempts: 0, best_score_percent: null } },
      ],
      "POST /me/activities/11/confirm": (config) => {
        posted.push(config.url);
        return [
          200,
          { activity_id: 11, confirmed_at: "2026-10-28T00:00:00", progress: progress({ activities_done: 1 }), granted_rewards: [], xp: XP_ZERO },
        ];
      },
    });
    renderAt("/career/python/variables", ALICE);

    fireEvent.click(await screen.findByRole("button", { name: /학습 완료로 표시/ }));
    expect(await screen.findByText("학습 완료")).toBeTruthy();
    expect(screen.getByText("필수 활동 1/1")).toBeTruthy();
    expect(screen.getByText("진행 중")).toBeTruthy();
    expect(posted).toEqual(["/me/activities/11/confirm"]);
  });

  it("hides answers until passing, then reveals them and celebrates the reward", async () => {
    const submissions = [];
    restore = installFakeServer({
      "GET /tracks/python/units/variables": () => [200, UNIT],
      "GET /me/tracks/python/units/variables/progress": () => [
        200,
        { progress: progress({ activities_done: 1 }), confirmed_activity_ids: [11], quiz: { passed: false, attempts: 0, best_score_percent: null } },
      ],
      "GET /tracks/python/units/variables/quiz": () => [200, QUIZ],
      "POST /me/quizzes/7/attempts": (config) => {
        const body = JSON.parse(config.data);
        submissions.push(body);
        const second = body.answers.find((a) => a.question_id === 102).choice_ids.sort();
        const passed = second.join() === "3,4";
        return [
          200,
          {
            attempt_id: submissions.length,
            score: passed ? 2 : 1,
            max_score: 2,
            score_percent: passed ? 100 : 50,
            passed,
            pass_score_percent: 80,
            answers_revealed: passed,
            feedback: [
              { question_id: 101, correct: true, correct_choice_ids: passed ? [1] : null, explanation: passed ? "첫 해설" : null },
              { question_id: 102, correct: passed, correct_choice_ids: passed ? [3, 4] : null, explanation: passed ? "둘째 해설" : null },
            ],
            progress: passed ? progress({ state: "completed", activities_done: 1, quiz_passed: true }) : progress({ activities_done: 1 }),
            granted_rewards: passed ? [{ amount: 100, reason: "unit_completed" }] : [],
            xp: passed ? XP_AFTER : XP_ZERO,
          },
        ];
      },
    });
    renderAt("/career/python/variables", ALICE);

    fireEvent.click(await screen.findByRole("button", { name: "퀴즈 풀기" }));
    await screen.findByText("첫 문제");
    expect(screen.getByRole("button", { name: "다음" }).disabled).toBe(true);
    choose("정답A");
    click("다음");
    check("정답B");
    click("제출하기");

    expect(await screen.findByText("아쉽게도 통과하지 못했습니다")).toBeTruthy();
    expect(screen.getByText("틀린 문항: Q2")).toBeTruthy();
    expect(screen.getByText(/정답과 해설은 퀴즈를 통과하면 공개됩니다/)).toBeTruthy();
    expect(screen.queryByText("둘째 해설")).toBeNull();

    click(/다시 풀기/);
    choose("정답A");
    click("다음");
    check("정답B");
    check("정답C");
    click("제출하기");

    expect(await screen.findByText("통과했습니다!")).toBeTruthy();
    expect(screen.getByText("둘째 해설")).toBeTruthy();
    expect(screen.getByText(/^(정답B, 정답C|정답C, 정답B)$/)).toBeTruthy(); // choices are shuffled
    expect(screen.getByRole("status").textContent).toContain("단원 완료! +100 XP");
    expect(screen.getByRole("status").textContent).toContain("Lv 2");
    expect(screen.getByText("완료")).toBeTruthy();

    expect(submissions).toHaveLength(2);
    expect(submissions[0].client_submission_id).not.toBe(submissions[1].client_submission_id);
    expect(submissions[1].answers).toEqual([
      { question_id: 101, choice_ids: [1] },
      { question_id: 102, choice_ids: expect.arrayContaining([3, 4]) },
    ]);
  });

  it("retries a submission after a network error with the same submission id", async () => {
    const ids = [];
    let fail = true;
    restore = installFakeServer({
      "GET /tracks/python/units/variables": () => [200, { ...UNIT, quiz: { id: 7, question_count: 1, pass_score_percent: 80 } }],
      "GET /me/tracks/python/units/variables/progress": () => [
        200,
        { progress: progress(), confirmed_activity_ids: [], quiz: { passed: false, attempts: 0, best_score_percent: null } },
      ],
      "GET /tracks/python/units/variables/quiz": () => [200, { ...QUIZ, questions: [QUIZ.questions[0]] }],
      "POST /me/quizzes/7/attempts": (config) => {
        ids.push(JSON.parse(config.data).client_submission_id);
        if (fail) {
          fail = false;
          throw new Error("network down");
        }
        return [
          200,
          {
            attempt_id: 1, score: 1, max_score: 1, score_percent: 100, passed: true, pass_score_percent: 80,
            answers_revealed: true, feedback: [{ question_id: 101, correct: true, correct_choice_ids: [1], explanation: null }],
            progress: progress({ quiz_passed: true }), granted_rewards: [], xp: XP_ZERO,
          },
        ];
      },
    });
    renderAt("/career/python/variables", ALICE);

    fireEvent.click(await screen.findByRole("button", { name: "퀴즈 풀기" }));
    await screen.findByText("첫 문제");
    choose("정답A");
    click("제출하기");
    expect(await screen.findByText(/네트워크 오류로 제출을 확인하지 못했습니다/)).toBeTruthy();
    click("제출하기");
    expect(await screen.findByText("통과했습니다!")).toBeTruthy();
    await waitFor(() => expect(ids).toHaveLength(2));
    expect(ids[0]).toBe(ids[1]);
  });
});
