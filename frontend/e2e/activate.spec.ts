import { expect, test, type Page } from "@playwright/test"

const corsHeaders = {
    "access-control-allow-origin": "http://127.0.0.1:3000",
    "access-control-allow-credentials": "true",
    "access-control-allow-methods": "POST,OPTIONS",
    "access-control-allow-headers": "content-type,x-csrf-token",
}

async function fillPasswords(page: Page) {
    // Wait for hydration: typing into SSR inputs before React attaches resets the controlled values.
    await page.waitForFunction(() => {
        const input = document.getElementById("confirm")
        return !!input && Object.keys(input).some((key) => key.startsWith("__reactProps"))
    })
    const password = page.getByLabel("Пароль", { exact: true })
    const confirm = page.getByLabel("Повторите пароль")
    await password.fill("secret123")
    await confirm.fill("secret123")
    await expect(password).toHaveValue("secret123")
    await expect(confirm).toHaveValue("secret123")
}

test("activation link sets the first password and leads to login", async ({ page }) => {
    let activatePayload: Record<string, unknown> | undefined
    await page.route("**/api/auth/activate", async (route) => {
        if (route.request().method() === "OPTIONS") {
            await route.fulfill({ status: 204, headers: corsHeaders })
            return
        }
        activatePayload = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({
            status: 200,
            contentType: "application/json",
            headers: corsHeaders,
            body: '{"message":"Account activated"}',
        })
    })

    await page.goto("/auth/activate?token=activation-test")
    await expect(page.getByText("Создайте пароль", { exact: true })).toBeVisible()
    await fillPasswords(page)
    // The token is kept in memory only; the address bar and history no longer carry it.
    await expect(page).toHaveURL(/\/auth\/activate$/)
    await page.getByRole("button", { name: "Сохранить пароль и продолжить" }).click()

    await expect(page).toHaveURL(/\/auth\/login$/)
    expect(activatePayload).toEqual({ token: "activation-test", new_password: "secret123" })
})

test("reloading the activation page after the token was hidden explains what to do", async ({ page }) => {
    await page.goto("/auth/activate?token=activation-test")
    await expect(page).toHaveURL(/\/auth\/activate$/)

    await page.reload()

    await expect(page.getByText("Код активации не найден", { exact: false })).toBeVisible()
    await expect(page.getByRole("link", { name: "Забыли пароль?" })).toBeVisible()
})

test("malformed activation token gets the friendly message, not validation details", async ({ page }) => {
    await page.route("**/api/auth/activate", async (route) => {
        if (route.request().method() === "OPTIONS") {
            await route.fulfill({ status: 204, headers: corsHeaders })
            return
        }
        await route.fulfill({
            status: 422,
            contentType: "application/json",
            headers: corsHeaders,
            body: JSON.stringify({
                detail: [{ type: "string_too_short", loc: ["body", "token"], msg: "String should have at least 10 characters" }],
            }),
        })
    })

    await page.goto("/auth/activate?token=short")
    await fillPasswords(page)
    await page.getByRole("button", { name: "Сохранить пароль и продолжить" }).click()

    await expect(page.getByRole("alert").filter({ hasText: "Ссылка недействительна или устарела" })).toBeVisible()
    await expect(page.getByText("String should have at least", { exact: false })).toHaveCount(0)
})

test("expired activation link explains how to get a new one", async ({ page }) => {
    await page.route("**/api/auth/activate", async (route) => {
        if (route.request().method() === "OPTIONS") {
            await route.fulfill({ status: 204, headers: corsHeaders })
            return
        }
        await route.fulfill({
            status: 400,
            contentType: "application/json",
            headers: corsHeaders,
            body: '{"detail":"Invalid or expired activation token"}',
        })
    })

    await page.goto("/auth/activate?token=stale-token")
    await fillPasswords(page)
    await page.getByRole("button", { name: "Сохранить пароль и продолжить" }).click()

    await expect(page.getByRole("alert").filter({ hasText: "Ссылка недействительна или устарела" })).toBeVisible()
    await expect(page.getByRole("link", { name: "Забыли пароль?" })).toBeVisible()
})

test("activation page without a token offers recovery links", async ({ page }) => {
    await page.goto("/auth/activate")
    await expect(page.getByText("Код активации не найден", { exact: false })).toBeVisible()
    await expect(page.getByRole("link", { name: "Забыли пароль?" })).toBeVisible()
})
