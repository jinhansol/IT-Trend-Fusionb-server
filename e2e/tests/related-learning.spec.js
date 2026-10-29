// P2: technology-level links between Home, Career and Dev.
// Home filter -> related Career unit -> the unit's technology -> filtered Dev posts.
import { expect, test } from "@playwright/test";

test("Home technology filter leads to Career learning and on to Dev posts", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("region", { name: "관련 학습" })).toHaveCount(0);

  await page.getByRole("group", { name: "기술 필터" }).getByRole("button", { name: "Python", exact: true }).click();
  await expect(page).toHaveURL(/\/\?tech=python$/);
  await expect(page.getByRole("link", { name: /파이썬 3\.14 출시/ })).toBeVisible();

  const related = page.getByRole("region", { name: "관련 학습" });
  await expect(related).toContainText("Python을(를) 다루는 Career 학습");
  await related.getByRole("link", { name: /변수와 기본 자료형/ }).click();

  await expect(page).toHaveURL(/\/career\/python\/variables-and-types$/);
  const technologies = page.getByRole("region", { name: "관련 기술" });
  await expect(technologies).toContainText("Python");
  await technologies.getByRole("link", { name: "Dev 글" }).click();

  await expect(page).toHaveURL(/\/dev\?tech=python$/);
  await expect(page.getByRole("group", { name: "기술 필터" }).getByRole("button", { name: "Python", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true"
  );
  await expect(page.getByRole("region", { name: "관련 학습" })).toBeVisible();
  await expect(page.locator("article").first()).toBeVisible();
});

test("a unit's IT 뉴스 link opens Home filtered by that technology", async ({ page }) => {
  await page.goto("/career/python/variables-and-types");
  await page.getByRole("region", { name: "관련 기술" }).getByRole("link", { name: "IT 뉴스" }).click();
  await expect(page).toHaveURL(/\/\?tech=python$/);
  await expect(page.getByRole("link", { name: /파이썬 3\.14 출시/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /랜섬웨어/ })).toHaveCount(0);
});
