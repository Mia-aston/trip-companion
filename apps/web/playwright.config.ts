import { defineConfig, devices } from "@playwright/test";

// Starts the API (needs DATABASE_URL pointing at a migrated PostGIS DB) and the built web app.
// Locally: `npm run build && npm run e2e`. CI sets E2E_API_CMD to the system uvicorn.
const apiCmd = process.env.E2E_API_CMD ?? ".venv/bin/uvicorn app.main:app --port 8000";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: { baseURL: "http://localhost:3000", trace: "off" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    { command: apiCmd, cwd: "../../services/api", url: "http://localhost:8000/health", reuseExistingServer: !process.env.CI },
    { command: "npx next start -p 3000", url: "http://localhost:3000", reuseExistingServer: !process.env.CI },
  ],
});
