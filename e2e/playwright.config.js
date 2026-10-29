// End-to-end tests: real browser -> Vite dev server -> FastAPI -> MariaDB.
// They run against the *test* database (APP_ENV=test only accepts names ending in
// _test); global-setup.js checks the connected database name before writing to it.
// Do not run them at the same time as the backend pytest suite, which resets that DB.
import { defineConfig, devices } from "@playwright/test";

const API_PORT = 8100;
const WEB_PORT = 5180;

export const backendEnv = {
  APP_ENV: "test",
  DATABASE_URL:
    process.env.E2E_DATABASE_URL ??
    "mysql+pymysql://devhub_test:devhub_local_test@127.0.0.1:3307/devhub_test",
  // Throwaway secret for this local test server only.
  JWT_SECRET: "e2e-only-secret-not-used-anywhere-else-0123456789",
  LOG_LEVEL: "WARNING",
  // Every spec signs up its own users from one IP; the production default (5 per hour)
  // is checked by the backend tests, so the E2E server only needs a higher ceiling.
  REGISTER_RATE_LIMIT_ATTEMPTS: "100",
};

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.js",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port ${API_PORT}`,
      cwd: "../backend",
      env: backendEnv,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      cwd: "../frontend",
      env: { VITE_DEV_API_PROXY_TARGET: `http://127.0.0.1:${API_PORT}` },
      url: `http://127.0.0.1:${WEB_PORT}`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
