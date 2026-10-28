// Phase 4 learning flow: sign up, study unit 1, fail and pass the quiz, earn XP,
// and find the progress again after a reload and after logging in again.
import { expect, test } from "@playwright/test";

const UNIT_URL = "/career/python/variables-and-types";
const PASSWORD = "correct horse 1";

// Answers to backend/content/python/units/01-variables-and-types.yaml
const ANSWERS = [
  ["3.5"],
  ["2nd_place"],
  ["7 // 2", 'int("42")'],
  ["TypeError가 발생한다"],
  ["<class 'bool'>"],
];

async function answerQuiz(page, answers) {
  for (const [index, labels] of answers.entries()) {
    await expect(page.getByText(`Q${index + 1} / ${answers.length}`)).toBeVisible();
    for (const label of labels) {
      await page.getByRole(labels.length > 1 ? "checkbox" : "radio", { name: label, exact: true }).click();
    }
    const last = index === answers.length - 1;
    await page.getByRole("button", { name: last ? "제출하기" : "다음" }).click();
  }
}

test("learner completes unit 1 and keeps the progress", async ({ page }) => {
  const email = `e2e-${Date.now()}-${Math.random().toString(16).slice(2, 8)}@example.com`;
  const welcome = page.getByText("Welcome,");

  // Anonymous visitors see the catalog and a login prompt instead of progress.
  await page.goto("/career");
  await expect(page.getByText(/로그인하면 내 학습 현황/)).toBeVisible();

  await page.getByRole("button", { name: "Sign Up" }).click();
  await page.locator('input[name="email"]').fill(email);
  await page.locator('input[name="password"]').fill(PASSWORD);
  await page.locator('input[name="displayName"]').fill("E2E Learner");
  await page.getByRole("button", { name: "가입하기" }).click();
  await expect(welcome).toBeVisible();

  const status = page.getByRole("region", { name: "내 학습 현황" });
  await expect(status.getByText("Lv 1")).toBeVisible();
  await expect(page.getByText("진행 중인 단원이 없습니다")).toBeVisible();

  // Study unit 1: confirm every required activity.
  await page.goto(UNIT_URL);
  const confirmButtons = page.getByRole("button", { name: "학습 완료로 표시" });
  await expect(confirmButtons.first()).toBeVisible();
  const total = await confirmButtons.count();
  for (let i = 0; i < total; i += 1) {
    await confirmButtons.first().click();
    await expect(page.getByText("학습 완료", { exact: true })).toHaveCount(i + 1);
  }
  await expect(page.getByText("필수 활동 3/3")).toBeVisible();

  // First attempt with two wrong answers (3/5 = 60%, below the 80% pass mark).
  await page.getByRole("button", { name: "퀴즈 풀기" }).click();
  await answerQuiz(page, [["3"], ["user_name"], ...ANSWERS.slice(2)]);
  await expect(page.getByText("아쉽게도 통과하지 못했습니다")).toBeVisible();
  await expect(page.getByText("틀린 문항: Q1, Q2")).toBeVisible();
  await expect(page.getByText("정답과 해설은 퀴즈를 통과하면 공개됩니다.")).toBeVisible();

  // Retry and pass: answers, explanations and the reward appear.
  await page.getByRole("button", { name: "다시 풀기" }).click();
  await answerQuiz(page, ANSWERS);
  await expect(page.getByText("통과했습니다!")).toBeVisible();
  await expect(page.getByText(/정수 몫이 필요하면/)).toBeVisible();
  await expect(page.getByRole("status")).toContainText("단원 완료! +100 XP");
  await expect(page.getByRole("status")).toContainText("Lv 2");

  // Progress survives a reload (session restored from the refresh cookie).
  await page.reload();
  await expect(welcome).toBeVisible();
  await expect(page.getByText("필수 활동 3/3")).toBeVisible();
  await expect(page.getByText("통과", { exact: true })).toBeVisible();

  // ...and a fresh login.
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page.getByRole("button", { name: "Login" })).toBeVisible();
  await page.goto("/career");
  await page.getByRole("button", { name: "Login" }).click();
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.locator("form").getByRole("button", { name: "로그인" }).click();
  await expect(welcome).toBeVisible();

  await expect(status.getByText("Lv 2")).toBeVisible();
  await expect(status.getByText("0 / 150 XP · 누적 100 XP")).toBeVisible();
  await expect(status.getByText("완료한 단원").locator("..")).toContainText("1");
  await expect(page.getByRole("link", { name: /Python/ })).toContainText("완료 1 /");
});
