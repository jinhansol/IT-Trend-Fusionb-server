// P3: career exploration, saved candidates and learning goals.
// Roles come from backend/tests/fixtures/careers/e2e-careers.yaml (test data only).
import { expect, test } from "@playwright/test";

const PASSWORD = "correct horse 1";
const email = (tag) => `e2e-${tag}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}@example.com`;
const ROLE_URL = "/career/roles/e2e-backend";

async function signUp(page, tag) {
  await page.goto("/career");
  await page.getByRole("button", { name: "Sign Up" }).click();
  await page.locator('input[name="email"]').fill(email(tag));
  await page.locator('input[name="password"]').fill(PASSWORD);
  await page.locator('input[name="displayName"]').fill("E2E Career");
  await page.getByRole("button", { name: "가입하기" }).click();
  await expect(page.getByText("Welcome,")).toBeVisible();
}

test("guests explore roles and their Career learning without saving anything", async ({ page }) => {
  await page.goto("/career");
  await page.getByRole("link", { name: /진로 탐색/ }).click();
  await expect(page).toHaveURL(/\/career\/explore$/);
  const cards = page.getByRole("link", { name: /자세히 보기/ });
  await expect(cards).toHaveCount(2);
  await expect(cards.first()).toContainText("테스트 직무 백엔드");

  await cards.first().click();
  await expect(page).toHaveURL(/\/career\/roles\/e2e-backend$/);
  const core = page.getByRole("region", { name: "핵심 기술" });
  await expect(core).toContainText("Python");
  await expect(core.getByRole("link", { name: /Python 기초 · 1\. 변수와 기본 자료형/ })).toHaveAttribute(
    "href",
    "/career/python/variables-and-types"
  );
  await expect(page.getByText(/진로 후보로 저장하거나 학습 목표로 삼을 수 있어요/)).toBeVisible();
  await expect(page.getByRole("button", { name: /진로 후보에 저장/ })).toHaveCount(0);
});

test("a member saves a candidate, adds a goal and follows it to learning", async ({ page }) => {
  await signUp(page, "career");
  const summaryBefore = await page.getByRole("region", { name: "내 학습 현황" }).textContent();

  await page.goto(ROLE_URL);
  await page.getByRole("button", { name: "진로 후보에 저장" }).click();
  await expect(page.getByRole("button", { name: "진로 후보에 저장됨" })).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: "학습 목표로 추가" }).click();
  const form = page.getByRole("form", { name: "학습 목표 추가" });
  await expect(form.getByLabel("목표", { exact: true })).toHaveValue("테스트 직무 백엔드 되기");
  await form.getByRole("button", { name: "목표 저장" }).click();
  await expect(page.getByRole("status")).toContainText("학습 목표에 추가했어요");

  // The goal appears on the Career home with its linked unit and my (empty) progress.
  await page.goto("/career");
  const goal = page.getByRole("article", { name: "목표: 테스트 직무 백엔드 되기" });
  await expect(goal).toContainText("연결된 Career 학습 0/1 완료");
  await expect(goal.getByRole("link", { name: "직무: 테스트 직무 백엔드" })).toBeVisible();
  // Saving a candidate and a goal changed nothing in the learning record.
  await expect(page.getByRole("region", { name: "내 학습 현황" })).toHaveText(summaryBefore);

  await goal.getByRole("link", { name: /변수와 기본 자료형/ }).click();
  await expect(page).toHaveURL(/\/career\/python\/variables-and-types$/);

  // Manage: achieve the goal by hand, then remove the candidate.
  await page.goto("/career/goals");
  const active = page.getByRole("region", { name: "진행 중인 목표" });
  await active.getByRole("button", { name: "달성으로 표시" }).click();
  await expect(page.getByRole("region", { name: "달성한 목표" })).toContainText("테스트 직무 백엔드 되기");
  await expect(page.getByRole("region", { name: "진행 중인 목표" })).toContainText("진행 중인 목표가 없습니다.");
  await page.getByRole("button", { name: "후보에서 삭제" }).click();
  await expect(page.getByText("아직 저장한 직무가 없습니다.")).toBeVisible();

  await page.goto("/career");
  await expect(page.getByRole("region", { name: "내 학습 현황" })).toHaveText(summaryBefore); // no XP for goals
});

test("career screens fit a phone screen", async ({ page }) => {
  await signUp(page, "mobile");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/career", "/career/explore", ROLE_URL, "/career/goals"]) {
    await page.goto(path);
    await expect(page.locator("main")).toBeVisible();
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    expect(overflow, path).toBe(false);
  }
});
