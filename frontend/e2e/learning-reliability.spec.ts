import { expect, test, type Page } from "@playwright/test"

async function student(page: Page) {
    const origin = new URL(test.info().project.use.baseURL!).origin
    await page.context().addCookies([{ name: "auth_session", value: "1", url: origin }])
    const fulfill = (body: unknown, status = 200) => ({ status, contentType: "application/json", headers: { "access-control-allow-origin": origin, "access-control-allow-credentials": "true" }, body: JSON.stringify(body) })
    await page.route("**/api/auth/me", (route) => route.fulfill(fulfill({ id: "student", email: "student@example.test", role: "student", email_verified_at: "2026-10-07T00:00:00", created_at: "2026-10-07T00:00:00" })))
    return fulfill
}

test("dashboard API failure is retryable and not an empty account", async ({ page }) => {
    const json = await student(page)
    let requests = 0
    await page.route("**/api/purchases/my", (route) => route.fulfill(++requests === 1 ? json({ detail: "Temporary unavailable" }, 503) : json([])))
    await page.route("**/api/purchases/my/expired", (route) => route.fulfill(json([])))
    await page.goto("/dashboard")
    await expect(page.getByText("Не удалось загрузить ваши курсы")).toBeVisible()
    await expect(page.getByText("У вас пока нет открытого курса")).toHaveCount(0)
    await page.getByRole("button", { name: "Повторить", exact: true }).click()
    await expect(page.getByText("У вас пока нет открытого курса")).toBeVisible()
})

test("preview survives progress 403 and refresh fails closed after 300 seconds", async ({ page }) => {
    const json = await student(page)
    const lesson = { id: "preview", module_id: "module", title: "Preview lesson", duration_seconds: 60, order_index: 1, is_preview: true }
    await page.route("**/api/lessons/preview", (route) => route.fulfill(json(lesson)))
    await page.route("**/api/courses/course/modules", (route) => route.fulfill(json([{ id: "module", title: "Module", order_index: 1, lessons: [lesson] }])))
    await page.route("**/api/courses/course/my-progress", (route) => route.fulfill(json({ detail: "Access required" }, 403)))
    let playRequests = 0
    let revoked = false
    await page.route("**/api/lessons/preview/play", (route) => { playRequests += 1; return route.fulfill(revoked ? json({ detail: "Access revoked" }, 403) : json({ video_url: "https://player.example.test/video/preview", title: "Preview lesson", expires_in_seconds: 300 })) })
    await page.route("https://player.example.test/**", (route) => route.fulfill({ contentType: "text/html", body: "<html><body>Preview iframe</body></html>" }))
    await page.goto("/courses/course/lessons/preview")
    const iframe = page.locator('iframe[title="Preview lesson"]')
    await expect(iframe).toBeVisible()
    await expect(page.getByText("Предпросмотр: прогресс курса недоступен без доступа")).toBeVisible()
    await expect(page.getByRole("button", { name: "Отметить просмотренным" })).toHaveCount(0)
    const initialRequests = playRequests
    revoked = true
    await page.evaluate(() => {
        const now = Date.now
        Date.now = () => now() + 301_000
        window.dispatchEvent(new Event("focus"))
    })
    await expect(page.getByRole("heading", { name: "Доступ ограничен" })).toBeVisible()
    await expect(iframe).toHaveCount(0)
    await page.evaluate(() => { window.dispatchEvent(new Event("focus")); window.dispatchEvent(new Event("pageshow")) })
    expect(playRequests).toBe(initialRequests + 1)
})
