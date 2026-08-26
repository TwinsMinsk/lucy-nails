import { expect, test } from "@playwright/test"

test("content manager enters only permitted admin sections without legacy admin role", async ({ page, context }) => {
    const corsHeaders = {
        "access-control-allow-origin": "http://127.0.0.1:3000",
        "access-control-allow-credentials": "true",
    }
    await context.addCookies([{ name: "auth_session", value: "1", domain: "127.0.0.1", path: "/" }])
    await page.route("**/api/auth/me", async (route) => {
        await route.fulfill({
            status: 200,
            contentType: "application/json",
            headers: corsHeaders,
            body: JSON.stringify({
                id: "00000000-0000-0000-0000-000000000123",
                email: "content@example.test",
                role: "student",
                created_at: "2026-08-26T00:00:00Z",
            }),
        })
    })
    await page.route("**/api/admin/team/me", async (route) => {
        await route.fulfill({
            status: 200,
            contentType: "application/json",
            headers: corsHeaders,
            body: JSON.stringify({
                roles: ["content_manager"],
                permissions: ["content.manage"],
            }),
        })
    })
    await page.route("**/api/admin/courses", async (route) => {
        await route.fulfill({ status: 200, contentType: "application/json", headers: corsHeaders, body: "[]" })
    })

    await page.goto("/admin/courses")

    await expect(page.getByRole("heading", { name: "Управление курсами", exact: true })).toBeVisible()
    await expect(page.getByRole("link", { name: "Курсы и контент" })).toBeVisible()
    await expect(page.getByRole("link", { name: "Ученики" })).toHaveCount(0)
    await expect(page.getByRole("link", { name: "Аудит и система" })).toHaveCount(0)
})
