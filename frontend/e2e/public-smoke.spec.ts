import { expect, test } from "@playwright/test"

test("public landing and login remain usable", async ({ page }) => {
    await page.goto("/")
    await expect(page).toHaveTitle(/Lucy Nails/i)

    await page.goto("/auth/login")
    await expect(page.getByRole("heading", { name: "Вход в аккаунт" })).toBeVisible()
    await expect(page.getByLabel("Email")).toBeVisible()
    await expect(page.getByLabel("Пароль")).toBeVisible()
})
