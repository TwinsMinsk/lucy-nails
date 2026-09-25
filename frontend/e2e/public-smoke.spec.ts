import { expect, test } from "@playwright/test"

test("public landing and login remain usable", async ({ page }) => {
    await page.goto("/")
    await expect(page).toHaveTitle(/Nail Design PRO|Lucy Nails/i)

    await page.goto("/auth/login")
    await expect(page.getByRole("heading", { name: "Вход в аккаунт" })).toBeVisible()
    await expect(page.getByLabel("Email")).toBeVisible()
    await expect(page.getByLabel("Пароль")).toBeVisible()
})

test("registration requires personal-data consent", async ({ page }) => {
    let registerCalled = false
    await page.route("**/api/auth/register", async (route) => {
        registerCalled = true
        await route.abort()
    })

    await page.goto("/auth/register")
    // Wait for hydration so typed values are not reset by React.
    await page.waitForFunction(() => {
        const button = document.querySelector("button[type=submit]")
        return !!button && Object.keys(button).some((key) => key.startsWith("__reactProps"))
    })
    await page.getByLabel("Email").fill("new-student@example.com")
    await page.getByLabel("Пароль", { exact: true }).fill("secret123")
    await page.getByLabel("Подтвердите пароль").fill("secret123")
    await expect(page.getByRole("button", { name: "Зарегистрироваться" })).toHaveAttribute("aria-disabled", "true")
    await page.getByLabel("Подтвердите пароль").press("Enter")

    await expect(page.getByRole("alert").filter({ hasText: "Примите условия оферты" })).toBeVisible()
    await expect(page.getByRole("alert").filter({ hasText: "Дайте согласие на обработку персональных данных" })).toBeVisible()
    await expect(page.getByRole("checkbox", { name: "Я принимаю условия оферты" })).toBeFocused()
    expect(registerCalled).toBe(false)
    await expect(page.getByRole("link", { name: "оферты", exact: true })).toHaveAttribute("target", "_blank")
    await expect(page.getByRole("link", { name: "обработку персональных данных" })).toHaveAttribute("target", "_blank")
})

test("login posts credentials to the API and never into the page URL", async ({ page }) => {
    let loginPayload: Record<string, unknown> | undefined
    const corsHeaders = {
        "access-control-allow-origin": "http://127.0.0.1:3000",
        "access-control-allow-credentials": "true",
        "access-control-allow-methods": "POST,OPTIONS",
        "access-control-allow-headers": "content-type,x-csrf-token",
    }
    await page.route("**/api/auth/login", async (route) => {
        if (route.request().method() === "OPTIONS") {
            await route.fulfill({ status: 204, headers: corsHeaders })
            return
        }
        loginPayload = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({
            status: 401,
            contentType: "application/json",
            headers: corsHeaders,
            body: '{"detail":"Incorrect email or password"}',
        })
    })

    await page.goto("/auth/login")
    // Even a native pre-hydration submit must not use GET (password in the query string).
    await expect(page.locator("form").filter({ has: page.getByLabel("Пароль") })).toHaveAttribute("method", "post")
    await page.waitForFunction(() => {
        const button = document.querySelector("button[type=submit]")
        return !!button && Object.keys(button).some((key) => key.startsWith("__reactProps"))
    })
    await page.getByLabel("Email").fill("student@example.com")
    await page.getByLabel("Пароль").fill("secret123")
    await page.getByLabel("Пароль").press("Enter")

    await expect.poll(() => loginPayload).toMatchObject({ email: "student@example.com", password: "secret123" })
    expect(page.url()).not.toContain("secret123")
    await expect(page).toHaveURL(/\/auth\/login$/)
})
