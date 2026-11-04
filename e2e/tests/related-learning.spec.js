// P2: technology-level links between Home, Career and Dev.
// Home filter -> related Career unit -> the unit's technology -> filtered Dev posts.
import { expect, test } from "@playwright/test";

test("News technology filter leads to Career learning and on to Dev posts", async ({ page }) => {
  await page.goto("/news");
  await expect(page.getByRole("region", { name: "관련 학습" })).toHaveCount(0);

  await page.getByRole("group", { name: "기술 필터" }).getByRole("button", { name: "Python", exact: true }).click();
  await expect(page).toHaveURL(/\/news\?tech=python$/);
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
  await expect(page.getByRole("link", { name: /Building a REST API with FastAPI and PostgreSQL/ })).toBeVisible();
});

// Strategy B: one technology from a Home news card through News and Dev to its Career unit.
// Seed: news.rss.xml (Python news), devto_latest.json (Python and Kotlin posts),
// so_hot.json (Python and React questions); the Python unit comes from content/python.
test("Home news tag → News → Dev → Career by one technology, with the expected items", async ({ page }) => {
  await page.goto("/");
  const newsCard = page
    .getByRole("region", { name: "최신 IT 뉴스" })
    .locator("article")
    .filter({ has: page.getByRole("link", { name: /파이썬 3\.14 출시/ }) });
  await newsCard.getByRole("link", { name: "Python 기술 기사 보기" }).click();

  await expect(page).toHaveURL(/\/news\?tech=python$/);
  await expect(page.getByRole("link", { name: /파이썬 3\.14 출시/ })).toHaveAttribute("href", "https://news.example.com/articles/1");
  await expect(page.getByRole("link", { name: /JavaScript 런타임/ })).toHaveCount(0);

  await page.getByRole("link", { name: "같은 기술의 Dev 글 보기" }).click();
  await expect(page).toHaveURL(/\/dev\?tech=python$/);
  await expect(page.getByRole("tab", { name: "DEV Community" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("link", { name: /Building a REST API with FastAPI and PostgreSQL/ })).toHaveAttribute(
    "href",
    "https://dev.to/alice/building-a-rest-api-1001"
  );
  await expect(page.getByRole("link", { name: /Why I moved from Java to Kotlin/ })).toHaveCount(0);

  // Another channel, chosen by the user, keeps the same technology.
  await page.getByRole("tab", { name: "Stack Overflow" }).click();
  await expect(page.getByRole("link", { name: /asyncio\.gather/ })).toHaveAttribute(
    "href",
    "https://stackoverflow.com/questions/79000001/why-does-asyncio-gather-hang"
  );
  await expect(page.getByRole("link", { name: /useState not updating/ })).toHaveCount(0);
  await expect(page).toHaveURL(/\/dev\?tech=python$/);

  await page.getByRole("region", { name: "관련 학습" }).getByRole("link", { name: /변수와 기본 자료형/ }).click();
  await expect(page).toHaveURL(/\/career\/python\/variables-and-types$/);
  await expect(page.getByRole("region", { name: "관련 기술" })).toContainText("Python");
});

test("a unit's IT 뉴스 link opens News filtered by that technology", async ({ page }) => {
  await page.goto("/career/python/variables-and-types");
  await page.getByRole("region", { name: "관련 기술" }).getByRole("link", { name: "IT 뉴스" }).click();
  await expect(page).toHaveURL(/\/news\?tech=python$/);
  await expect(page.getByRole("link", { name: /파이썬 3\.14 출시/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /랜섬웨어/ })).toHaveCount(0);
});
