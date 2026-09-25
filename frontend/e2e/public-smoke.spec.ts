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

    await expect(page.getByText("Отметьте согласие, чтобы продолжить")).toBeVisible()
    expect(registerCalled).toBe(false)
    await expect(page.getByRole("link", { name: "политикой конфиденциальности" })).toHaveAttribute("target", "_blank")
})
