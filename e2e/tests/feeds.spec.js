// Phase 5: Home and Dev read collected content from the new API.
// Content comes from backend/tests/e2e_seed.py (stored sample responses).
import { expect, test } from "@playwright/test";

test("Home shows collected news, trends and the last update", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "IT 뉴스" })).toBeVisible();
  const article = page.getByRole("link", { name: /파이썬 3\.14 출시/ });
  await expect(article).toHaveAttribute("href", "https://news.example.com/articles/1");
  await expect(page.getByText(/마지막 갱신/)).toBeVisible();

  await page.getByRole("group", { name: "기술 필터" }).getByRole("button", { name: "보안" }).click();
  await expect(page.getByRole("link", { name: /랜섬웨어/ })).toBeVisible();
  await expect(article).toHaveCount(0);

  await expect(page.getByRole("heading", { name: "분야별 언급 기사 수" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "일별 기술 언급 기사 수" })).toBeVisible();
});

test("Dev switches sources and sorts by weekly popularity", async ({ page }) => {
  await page.goto("/dev");
  await expect(page.getByRole("tab", { name: "DEV Community" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("link", { name: /React Server Components/ })).toBeVisible();

  await page.getByRole("button", { name: "주간 인기" }).click();
  const titles = page.locator("article h3");
  await expect(titles.first()).toContainText("React Server Components"); // 250 reactions

  await page.getByRole("tab", { name: "Stack Overflow" }).click();
  const question = page.locator("article", { hasText: "asyncio.gather" });
  await expect(question).toContainText("답변 3");
  await expect(question).toContainText("조회 1,520");

  await page.getByRole("tab", { name: "국내 기술블로그" }).click();
  await expect(page.getByRole("link", { name: /쿠버네티스 위에서/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "주간 인기" })).toBeDisabled();
});
