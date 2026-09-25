import { expect, test } from "@playwright/test"

const corsHeaders = {
    "access-control-allow-origin": "http://127.0.0.1:3000",
    "access-control-allow-credentials": "true",
}

const json = (body: unknown, status = 200) => ({
    status,
    contentType: "application/json",
    headers: corsHeaders,
    body: JSON.stringify(body),
})

test.beforeEach(async ({ context, page }) => {
    await context.addCookies([{ name: "auth_session", value: "1", domain: "127.0.0.1", path: "/" }])
    await page.route("**/api/auth/me", (route) =>
        route.fulfill(json({
            id: "00000000-0000-0000-0000-000000000321",
            email: "student@example.test",
            role: "student",
            created_at: "2026-08-01T00:00:00Z",
        })),
    )
})

test("dashboard offers renewal for expired access", async ({ page }) => {
    await page.route("**/api/purchases/my", (route) => route.fulfill(json([])))
    await page.route("**/api/purchases/my/expired", (route) =>
        route.fulfill(json([
            {
                course_id: "11111111-1111-1111-1111-111111111111",
                course_title: "Nail Design PRO",
                cover_image_url: null,
                price_self: 5900,
                expired_at: "2026-09-20T10:00:00",
            },
        ])),
    )

    await page.goto("/dashboard")

    await expect(page.getByRole("heading", { name: "Доступ закончился" })).toBeVisible()
    await expect(page.getByText("Nail Design PRO", { exact: true })).toBeVisible()
    await expect(page.getByText("20.09.2026")).toBeVisible()
    await expect(page.getByRole("button", { name: /Продлить доступ — 5\s900 ₽/ })).toBeVisible()
    await expect(page.getByText("У вас пока нет открытого курса")).toHaveCount(0)
})

test("lesson page explains missing access instead of 'not found'", async ({ page }) => {
    const courseId = "22222222-2222-2222-2222-222222222222"
    const lessonId = "33333333-3333-3333-3333-333333333333"
    await page.route(`**/api/lessons/${lessonId}`, (route) =>
        route.fulfill(json({ id: lessonId, module_id: "m", title: "Урок", duration_seconds: 60, order_index: 1 })),
    )
    await page.route(`**/api/courses/${courseId}/modules`, (route) => route.fulfill(json([])))
    await page.route(`**/api/courses/${courseId}/my-progress`, (route) =>
        route.fulfill(json({ detail: "Access denied" }, 403)),
    )

    await page.goto(`/courses/${courseId}/lessons/${lessonId}`)

    await expect(page.getByText("Доступ к курсу закончился или ещё не открыт")).toBeVisible()
    await expect(page.getByRole("link", { name: "Перейти в кабинет" })).toBeVisible()
})
