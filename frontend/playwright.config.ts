import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.FRONTEND_PORT ?? "3000");
const frontendHost = process.env.FRONTEND_HOST ?? "127.0.0.1";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: `http://${frontendHost}:${frontendPort}`,
    headless: true,
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  webServer: {
    command: `npx vite --host ${frontendHost} --port ${frontendPort}`,
    port: frontendPort,
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
