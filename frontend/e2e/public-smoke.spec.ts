import { expect, test } from "@playwright/test"

test("public landing and login remain usable", async ({ page }) => {
    await page.goto("/")
    await expect(page).toHaveTitle(/Онлайн-курс дизайна ногтей.*Люся Смирнова/)

    await page.goto("/auth/login")
    await expect(page.getByRole("heading", { name: "Вход в аккаунт" })).toBeVisible()
    await expect(page.getByLabel("Email")).toBeVisible()
    await expect(page.getByLabel("Пароль")).toBeVisible()
})

test.describe("mobile menu", () => {
    // The burger button only exists below the lg breakpoint.
    test.use({ viewport: { width: 390, height: 844 } })

    test("a link closes the menu", async ({ page }) => {
        await page.goto("/")
        await page.getByRole("button", { name: "Меню" }).click()
        const menu = page.getByRole("dialog")
        await expect(menu).toBeVisible()

        await menu.getByRole("link", { name: "Войти" }).click()

        await expect(page).toHaveURL(/\/auth\/login$/)
        await expect(page.getByRole("dialog")).toHaveCount(0)
    })

    test("Back with the menu open leaves no dialog on the previous page", async ({ page }) => {
        await page.goto("/")
        // Client-side navigation through a Next Link keeps one document, as for a real visitor.
        await page.evaluate(() => { (window as unknown as { sameDocument: boolean }).sameDocument = true })
        await page.getByRole("button", { name: "Меню" }).click()
        await page.getByRole("dialog").getByRole("link", { name: "Войти" }).click()
        await expect(page.getByRole("heading", { name: "Вход в аккаунт" })).toBeVisible()
        await page.getByRole("button", { name: "Меню" }).click()
        await expect(page.getByRole("dialog")).toBeVisible()

        await page.goBack()

        await expect(page).toHaveURL(/:\d+\/$/)
        await expect(page.getByRole("dialog")).toHaveCount(0)
        expect(await page.evaluate(() => (window as unknown as { sameDocument?: boolean }).sameDocument)).toBe(true)
    })

    test("Back right after choosing an anchor cancels the pending scroll", async ({ page }) => {
        await page.goto("/")
        await page.getByRole("button", { name: "Меню" }).click()
        await page.getByRole("dialog").getByRole("link", { name: "Программа" }).click()
        await expect(page).toHaveURL(/#program$/)
        const historyLength = await page.evaluate(() => history.length)

        await page.getByRole("button", { name: "Меню" }).click()
        await page.getByRole("dialog").getByRole("link", { name: "Галерея" }).click()
        // Back while the menu is still closing: the scroll to #gallery must not happen afterwards.
        await page.goBack()
        await page.waitForTimeout(1_000)

        await expect(page.getByRole("dialog")).toHaveCount(0)
        await expect(page).toHaveURL(/:\d+\/$/)
        expect(await page.evaluate(() => history.length)).toBe(historyLength)
    })

    test("an anchor link closes the menu and scrolls to the gallery", async ({ page }) => {
        await page.goto("/")
        await page.getByRole("button", { name: "Меню" }).click()

        await page.getByRole("dialog").getByRole("link", { name: "Галерея" }).click()

        await expect(page.getByRole("dialog")).toHaveCount(0)
        await expect(page).toHaveURL(/#gallery$/)
        await expect.poll(async () => page.evaluate(() => Math.abs(document.getElementById("gallery")!.getBoundingClientRect().top)), { timeout: 5_000 }).toBeLessThan(2)
    })
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
    await page.getByLabel("Email").pressSequentially("new-student@example.com")
    await page.getByLabel("Пароль", { exact: true }).fill("secret123")
    await page.getByLabel("Подтвердите пароль").fill("secret123")
    await expect(page.getByLabel("Email")).toHaveValue("new-student@example.com")
    await expect(page.getByRole("button", { name: "Зарегистрироваться" })).toHaveAttribute("aria-disabled", "true")
    await page.getByLabel("Подтвердите пароль").press("Enter")

    await expect(page.getByRole("alert").filter({ hasText: "Примите условия оферты" })).toBeVisible()
    await expect(page.getByRole("alert").filter({ hasText: "Дайте согласие на обработку персональных данных" })).toBeVisible()
    await expect(page.getByRole("checkbox", { name: "Я принимаю условия оферты" })).toBeFocused()
    expect(registerCalled).toBe(false)
    await expect(page.getByRole("link", { name: "оферты", exact: true })).toHaveAttribute("target", "_blank")
    await expect(page.getByRole("link", { name: "обработку персональных данных" })).toHaveAttribute("target", "_blank")
})

test("login posts credentials to the API and never into the page URL", async ({ page, baseURL }) => {
    let loginPayload: Record<string, unknown> | undefined
    const corsHeaders = {
        "access-control-allow-origin": new URL(baseURL!).origin,
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
    await page.getByLabel("Email").pressSequentially("student@example.com")
    await page.getByLabel("Пароль").fill("secret123")
    await expect(page.getByLabel("Email")).toHaveValue("student@example.com")
    await expect(page.getByLabel("Пароль")).toHaveValue("secret123")
    await page.getByLabel("Пароль").press("Enter")

    await expect.poll(() => loginPayload).toMatchObject({ email: "student@example.com", password: "secret123" })
    expect(page.url()).not.toContain("secret123")
    await expect(page).toHaveURL(/\/auth\/login$/)
})
