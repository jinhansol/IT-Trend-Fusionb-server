// P1: optional learner type at sign-up, changeable in settings, used only for the
// static start guide on the Career home.
import { expect, test } from "@playwright/test";

const PASSWORD = "correct horse 1";
const email = (tag) => `e2e-${tag}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}@example.com`;

async function signUp(page, tag, typeLabel) {
  await page.goto("/career");
  await page.getByRole("button", { name: "Sign Up" }).click();
  await page.locator('input[name="email"]').fill(email(tag));
  await page.locator('input[name="password"]').fill(PASSWORD);
  await page.locator('input[name="displayName"]').fill("E2E Type");
  if (typeLabel) await page.getByRole("radio", { name: new RegExp(typeLabel) }).click();
  await page.getByRole("button", { name: "가입하기" }).click();
  await expect(page.getByText("Welcome,")).toBeVisible();
}

const guide = (page) => page.getByRole("region", { name: "시작 안내" });

test("guests and members without a type see the common guide", async ({ page }) => {
  await page.goto("/career");
  await expect(guide(page)).toContainText("DevHub를 이렇게 시작해 보세요");

  await signUp(page, "none");
  await expect(guide(page)).toContainText("DevHub를 이렇게 시작해 보세요");
});

test("the chosen type changes only the guide, and can be changed in settings", async ({ page }) => {
  await signUp(page, "typed", "입문자");
  await expect(guide(page)).toContainText("처음이라면 학습 트랙부터");
  const trackTitles = page.locator("#learning-tracks + ul h3");
  await expect(trackTitles.first()).toBeVisible();
  const tracks = await trackTitles.allTextContents();

  await page.getByRole("link", { name: "설정" }).click();
  await expect(page.getByRole("radio", { name: /입문자/ })).toBeChecked();
  await page.getByRole("radio", { name: /탐색 중/ }).click();
  await page.getByRole("button", { name: "저장", exact: true }).click(); // the learner type form
  await expect(page.getByRole("status")).toHaveText("저장했습니다.");

  await page.getByRole("link", { name: "Career" }).click();
  await expect(guide(page)).toContainText("IT 분야를 넓게 둘러보세요");
  await expect(trackTitles).toHaveText(tracks); // same tracks, same order

  // Still saved after a reload (server value, not browser state).
  await page.reload();
  await expect(guide(page)).toContainText("IT 분야를 넓게 둘러보세요");
});
