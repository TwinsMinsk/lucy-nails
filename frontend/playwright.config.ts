import { defineConfig, devices } from "@playwright/test"

export default defineConfig({
    testDir: "./e2e",
    fullyParallel: true,
    workers: 2,
    retries: process.env.CI ? 2 : 0,
    reporter: process.env.CI ? "github" : "list",
    use: {
        baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3015",
        trace: "on-first-retry",
    },
    webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : [
        {
            command: "node e2e/fixtures/api-server.mjs",
            url: "http://127.0.0.1:3016/health",
            reuseExistingServer: false,
        },
        {
            command: "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3015",
            url: "http://127.0.0.1:3015",
            env: { NEXT_PUBLIC_API_URL: "http://127.0.0.1:3016/api", NEXT_PUBLIC_SITE_URL: "http://127.0.0.1:3015", NEXT_PUBLIC_YANDEX_METRIKA_ID: "" },
            reuseExistingServer: false,
            timeout: 120_000,
        },
    ],
    projects: [
        { name: "chromium", use: { ...devices["Desktop Chrome"] } },
        { name: "mobile", use: { ...devices["iPhone 13"] } },
    ],
})
