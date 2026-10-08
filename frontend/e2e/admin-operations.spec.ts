import { expect, test, type Page } from "@playwright/test"

async function staff(page: Page, role: string, permissions: string[]) {
    const origin = new URL(test.info().project.use.baseURL!).origin
    await page.context().addCookies([{ name: "auth_session", value: "1", url: origin }])
    const requests: URL[] = []
    await page.route("**/api/**", async (route) => {
        const url = new URL(route.request().url())
        requests.push(url)
        const path = url.pathname
        let body: unknown = []
        let status = 200
        if (path === "/api/auth/me") body = { id: "staff", email: "staff@example.test", role: "student", email_verified_at: "2026-10-07T00:00:00", created_at: "2026-10-07T00:00:00" }
        else if (path === "/api/admin/team/me") body = { roles: [role], permissions }
        else if (path === "/api/admin/refunds") { status = 403; body = { detail: "Permission required: refunds.manage" } }
        else if (path === "/api/admin/reconciliation") body = { stale_pending_orders: 0, successful_purchases_without_active_entitlement: 0, processed_payment_errors: 0, dead_letter_notifications: 0 }
        else if (path === "/api/admin/orders") {
            const offset = Number(url.searchParams.get("offset") || 0)
            body = { items: [{ id: `order-${offset}`, customer_email: `buyer-${offset}@example.test`, course_title: "Course", tariff: "self", amount_kopecks: 10000, currency: "RUB", access_days: 30, status: "paid", purchase_id: "purchase-1", created_at: "2026-10-07T22:30:00" }], total: 201, limit: 50, offset }
        } else if (path === "/api/admin/notifications") {
            const offset = Number(url.searchParams.get("offset") || 0)
            body = { items: [{ id: `message-${offset}`, kind: "activation", channel: "email", recipient: `target-${offset}@example.test`, status: "dead_letter", attempts: 5, max_attempts: 5, created_at: "2026-10-07T22:30:00" }], total: 201, limit: 50, offset }
        } else if (path === "/api/admin/students") {
            const offset = Number(url.searchParams.get("offset") || 0)
            body = { items: [{ id: "student-1", email: offset ? `student-${offset}@example.test` : "student@example.test", role: "student", created_at: "2026-10-07T22:30:00", active_entitlements: 1 }], total: 205, limit: 50, offset }
        } else if (path === "/api/admin/entitlements") {
            const offset = Number(url.searchParams.get("offset") || 0)
            body = { items: [{ id: "access-1", user_email: `student-${offset}@example.test`, course_title: "Course", source: "manual", status: "revoked", starts_at: "2026-10-07T22:30:00", expires_at: "2026-10-07T22:30:00" }], total: 205, limit: 50, offset }
        }
        else if (path === "/api/admin/students/student-1") body = { id: "student-1", email: "student@example.test", created_at: "2026-10-07T22:30:00", completed_lessons: 0, tracked_lessons: 0, entitlements: [], purchases: [], certificates: [], notes: [], tags: [], lesson_progress: [] }
        else if (path === "/api/admin/access-courses") body = [{ id: "course-1", title: "Hidden course", access_days: 45 }]
        else if (path === "/api/admin/payment-events") body = { items: [], total: 0, limit: 100, offset: 0 }
        else if (path === "/api/admin/courses") { status = 403; body = { detail: "Permission required: content.manage" } }
        await route.fulfill({ status, contentType: "application/json", headers: { "access-control-allow-origin": origin, "access-control-allow-credentials": "true" }, body: JSON.stringify(body) })
    })
    return requests
}

test("analyst can search and page orders past 200 while refunds are forbidden", async ({ page }) => {
    const requests = await staff(page, "analyst", ["analytics.read", "commerce.read", "audit.read"])
    await page.goto("/admin/orders?search=buyer&status=paid&offset=200")
    await expect(page.getByText("buyer-200@example.test", { exact: true })).toBeVisible()
    await expect(page.getByText("08.10.2026, 01:30:00")).toBeVisible()
    await expect(page.getByText("Заказы (201)")).toBeVisible()
    await expect(page.getByRole("button", { name: "Возврат", exact: true })).toHaveCount(0)
    await expect(page.getByPlaceholder("Email клиента")).toHaveValue("buyer")
    expect(requests.some((url) => url.pathname === "/api/admin/refunds")).toBe(false)
    await page.getByRole("button", { name: "Назад", exact: true }).click()
    await expect(page).toHaveURL(/search=buyer&status=paid&offset=150/)
    await expect(page.getByText("buyer-150@example.test", { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.getByPlaceholder("Email клиента")).toHaveValue("buyer")
})

test("curator selects access courses without users.manage mutations", async ({ page }) => {
    const requests = await staff(page, "curator", ["users.read", "access.manage", "notifications.manage", "certificates.manage"])
    await page.goto("/admin/users")
    await page.getByRole("button", { name: /student@example.test/ }).click()
    await expect(page.getByRole("heading", { name: "Выдать доступ" })).toBeVisible()
    await page.getByRole("combobox").click()
    await expect(page.getByRole("option", { name: "Hidden course" })).toBeVisible()
    await page.keyboard.press("Escape")
    await expect(page.getByRole("button", { name: "Добавить заметку" })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Сохранить теги" })).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Отправить ссылку для входа" })).toHaveCount(0)
    expect(requests.some((url) => url.pathname === "/api/admin/courses")).toBe(false)
})

test("notifications retain search status channel and pages past 200", async ({ page }) => {
    await staff(page, "curator", ["notifications.manage"])
    await page.goto("/admin/notifications?search=target&status=dead_letter&channel=email&offset=200")
    await expect(page.getByText("target-200@example.test", { exact: true })).toBeVisible()
    await expect(page.getByText("Очередь (201)")).toBeVisible()
    await page.getByRole("button", { name: "Назад", exact: true }).click()
    await expect(page).toHaveURL(/search=target&status=dead_letter&channel=email&offset=150/)
    await expect(page.getByText("target-150@example.test", { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.getByPlaceholder("Получатель или тип сообщения")).toHaveValue("target")
})

test("students and access retain search and pages past 200 on reload", async ({ page }) => {
    await staff(page, "curator", ["users.read"])
    await page.goto("/admin/users?search=student&offset=200")
    await expect(page.getByRole("button", { name: /student-200@example.test/ })).toBeVisible()
    await page.getByRole("button", { name: "Назад", exact: true }).click()
    await expect(page).toHaveURL(/search=student&offset=150/)
    await page.reload()
    await expect(page.getByPlaceholder("Email, имя или телефон")).toHaveValue("student")
    await expect(page.getByRole("button", { name: /student-150@example.test/ })).toBeVisible()
    await page.goto("/admin/access?search=student&status=revoked&offset=200")
    await expect(page.getByText("student-200@example.test", { exact: true })).toBeVisible()
    await page.getByRole("button", { name: "Назад", exact: true }).click()
    await expect(page).toHaveURL(/search=student&status=revoked&offset=150/)
    await page.reload()
    await expect(page.getByPlaceholder("Email ученика")).toHaveValue("student")
    await expect(page.getByText("student-150@example.test", { exact: true })).toBeVisible()
})
