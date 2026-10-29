// P4: personalization switch, interests, self-rated skills and reset in Settings.
// OFF keeps the data; reset deletes interests and skills only and keeps the switch,
// goals and learning records.
import { expect, test } from "@playwright/test";

const PASSWORD = "correct horse 1";
const email = (tag) => `e2e-${tag}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}@example.com`;

async function signUp(page, tag) {
  await page.goto("/career");
  await page.getByRole("button", { name: "Sign Up" }).click();
  await page.locator('input[name="email"]').fill(email(tag));
  await page.locator('input[name="password"]').fill(PASSWORD);
  await page.locator('input[name="displayName"]').fill("E2E P4");
  await page.getByRole("button", { name: "가입하기" }).click();
  await expect(page.getByText("Welcome,")).toBeVisible();
}

const toggle = (page) => page.getByRole("switch", { name: "개인화" });
const section = (page, name) => page.getByRole("region", { name });

test("interests and skills are kept across OFF/ON and only they are reset", async ({ page }) => {
  await signUp(page, "p4");
  const summaryBefore = await page.getByRole("region", { name: "내 학습 현황" }).textContent();

  // A goal that a reset must keep.
  await page.goto("/career/goals");
  await page.getByRole("button", { name: "새 목표 추가" }).click();
  await page.getByLabel("목표", { exact: true }).fill("매일 30분 공부");
  await page.getByRole("button", { name: "목표 저장" }).click();
  await expect(page.getByRole("article", { name: "목표: 매일 30분 공부" })).toBeVisible();

  await page.getByRole("link", { name: "설정" }).click();
  await expect(toggle(page)).toHaveAttribute("aria-checked", "false");
  await expect(page.getByText(/관심 기술과 역량은 저장되지만 추천에 사용되지 않습니다/)).toBeVisible();

  // Editable while OFF.
  const interests = section(page, "관심 기술");
  await interests.getByRole("searchbox", { name: "관심 기술 검색" }).fill("python");
  await interests.getByRole("button", { name: "Python", exact: true }).click();
  await interests.getByRole("button", { name: "관심 기술 저장" }).click();
  await expect(interests.getByRole("status")).toHaveText("관심 기술을 저장했습니다.");

  const skills = section(page, "역량 자기 평가");
  await skills.getByRole("combobox", { name: "평가할 기술 추가" }).selectOption("docker");
  await skills.getByRole("combobox", { name: "Docker 역량" }).selectOption("used");
  await skills.getByRole("button", { name: "역량 저장" }).click();
  await expect(skills.getByRole("status")).toHaveText("역량 자기 평가를 저장했습니다.");

  // ON needs a confirmation that explains it; OFF keeps the data.
  await toggle(page).click();
  await expect(page.getByRole("dialog", { name: "개인화 켜기 안내" })).toContainText("현재는 개인화 추천 기능이 제공되지 않습니다");
  await page.getByRole("button", { name: "개인화 켜기" }).click();
  await expect(toggle(page)).toHaveAttribute("aria-checked", "true");
  await toggle(page).click();
  await expect(toggle(page)).toHaveAttribute("aria-checked", "false");
  await page.reload();
  await expect(section(page, "관심 기술").getByRole("button", { name: "Python", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(section(page, "역량 자기 평가").getByRole("combobox", { name: "Docker 역량" })).toHaveValue("used");

  // Reset with ON: interests and skills go, the switch stays ON.
  await toggle(page).click();
  await page.getByRole("button", { name: "개인화 켜기" }).click();
  await expect(toggle(page)).toHaveAttribute("aria-checked", "true");
  await page.getByRole("button", { name: "개인화 데이터 초기화" }).click();
  const dialog = page.getByRole("dialog", { name: "개인화 데이터 초기화 확인" });
  await expect(dialog.getByRole("list", { name: "유지되는 항목" })).toContainText("학습 목표");
  await dialog.getByRole("button", { name: "초기화" }).click();
  await expect(page.getByText(/초기화했습니다/)).toBeVisible();
  await page.reload();
  await expect(toggle(page)).toHaveAttribute("aria-checked", "true");
  await expect(section(page, "관심 기술").getByRole("button", { name: "Python", exact: true })).toHaveAttribute("aria-pressed", "false");
  await expect(section(page, "역량 자기 평가")).toContainText("아직 평가한 기술이 없습니다.");

  // Goals and learning records are untouched.
  await page.goto("/career");
  await expect(page.getByRole("article", { name: "목표: 매일 30분 공부" })).toBeVisible();
  await expect(page.getByRole("region", { name: "내 학습 현황" })).toHaveText(summaryBefore);
});

test("settings fit a phone screen", async ({ page }) => {
  await signUp(page, "p4-mobile");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/settings");
  await expect(toggle(page)).toBeVisible();
  await page.waitForLoadState("networkidle");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});
