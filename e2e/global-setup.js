// Prepare the E2E database: verify which database we are connected to, apply
// migrations, and load the learning content. Nothing is dropped or truncated.
import { execFileSync } from "node:child_process";
import { backendEnv } from "./playwright.config.js";

const backend = new URL("../backend", import.meta.url).pathname;

function run(args) {
  return execFileSync("uv", ["run", ...args], {
    cwd: backend,
    env: { ...process.env, ...backendEnv },
    encoding: "utf8",
  });
}

const CHECK_DATABASE = `
from sqlalchemy import text
from app.core.config import get_settings
from app.db.session import create_db_engine
with create_db_engine(get_settings()).connect() as connection:
    print(connection.execute(text("SELECT DATABASE()")).scalar_one())
`;

export default function globalSetup() {
  const name = run(["python", "-c", CHECK_DATABASE]).trim().split("\n").pop();
  if (!name.endsWith("_test")) {
    throw new Error(`Refusing to run E2E tests against database "${name}" (expected *_test)`);
  }
  run(["alembic", "upgrade", "head"]);
  // Technologies before tracks: units reference technology slugs.
  run(["python", "-m", "app.content_loader", "technologies", "content/technologies.yaml"]);
  run(["python", "-m", "app.content_loader", "load", "content/python"]);
  // Home/Dev content from stored sample responses (no external sites).
  run(["python", "-m", "tests.e2e_seed"]);
}
