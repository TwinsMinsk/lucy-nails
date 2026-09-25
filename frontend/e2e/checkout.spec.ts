import { expect, test } from "@playwright/test"

test("guest checkout reaches confirmed access state", async ({ page }) => {
    let checkoutPayload: Record<string, unknown> | undefined
    const corsHeaders = {
        "access-control-allow-origin": "http://127.0.0.1:3000",
        "access-control-allow-credentials": "true",
        "access-control-allow-methods": "GET,POST,OPTIONS",
        "access-control-allow-headers": "content-type,x-csrf-token",
    }

    await page.route("**/*", async (route) => {
        if (route.request().url().includes("/payments/orders/") && route.request().url().includes("/status")) {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                headers: corsHeaders,
                body: '{"status":"paid"}',
            })
            return
        }
        await route.fallback()
    })
    await page.route("**/api/analytics/events", async (route) => {
        await route.fulfill({ status: 202, contentType: "application/json", headers: corsHeaders, body: '{"accepted":true,"duplicate":false}' })
    })
    await page.route("**/api/payments/guest-link", async (route) => {
        if (route.request().method() === "OPTIONS") {
            await route.fulfill({ status: 204, headers: corsHeaders })
            return
        }
        checkoutPayload = route.request().postDataJSON() as Record<string, unknown>
        await route.fulfill({
            status: 200,
            contentType: "application/json",
            headers: corsHeaders,
            body: JSON.stringify({
                url: "http://127.0.0.1:3000/payment-success?order_id=order-test&token=status-test",
            }),
        })
    })
    await page.goto("/#pricing")
    await page.getByRole("button", { name: "Начать обучение" }).first().click()
    await expect(page.getByRole("heading", { name: "Оплата без регистрации" })).toBeVisible()

    await page.getByLabel("Email").fill("student@example.com")
    const payButton = page.getByRole("button", { name: "Перейти к оплате" })
    const offer = page.getByRole("checkbox", { name: "Я принимаю условия оферты" })
    const personalData = page.getByRole("checkbox", { name: "Даю согласие на обработку персональных данных" })
    const offerError = page.getByRole("alert").filter({ hasText: "Примите условия оферты" })
    const personalDataError = page.getByRole("alert").filter({ hasText: "Дайте согласие на обработку персональных данных" })
    await expect(payButton).toHaveAttribute("aria-disabled", "true")
    await expect(offer).toHaveAttribute("aria-required", "true")
    await expect(personalData).toHaveAttribute("aria-required", "true")

    // Submitting without consent explains the requirement and does not start checkout.
    await page.getByLabel("Email").press("Enter")
    await expect(offerError).toBeVisible()
    await expect(personalDataError).toBeVisible()
    await expect(offer).toBeFocused()
    expect(checkoutPayload).toBeUndefined()

    // The offer alone is not enough: personal-data consent is a separate, required box.
    await offer.check()
    await expect(offerError).toHaveCount(0)
    await page.getByLabel("Email").press("Enter")
    await expect(personalDataError).toBeVisible()
    await expect(personalData).toBeFocused()
    expect(checkoutPayload).toBeUndefined()

    await personalData.check()
    await expect(personalDataError).toHaveCount(0)
    await expect(payButton).not.toHaveAttribute("aria-disabled", "true")
    await payButton.click()

    await expect(page.getByRole("heading", { name: "Оплата подтверждена" })).toBeVisible()
    expect(checkoutPayload).toMatchObject({
        customer_email: "student@example.com",
        tariff: "self",
        offer_accepted: true,
        personal_data_consent: true,
        consent_version: expect.any(String),
    })
})

test("guest checkout dialog stays usable on a 360×640 phone", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 640 })
    await page.route("**/api/analytics/events", async (route) => {
        await route.fulfill({ status: 202, contentType: "application/json", body: '{"accepted":true,"duplicate":false}' })
    })
    await page.goto("/#pricing")
    const cta = page.getByRole("button", { name: "Начать обучение" }).first()
    // Wait for hydration: a click on the SSR button before React attaches is lost.
    await expect.poll(() => cta.evaluate((button) => Object.keys(button).some((key) => key.startsWith("__reactProps")))).toBe(true)
    await cta.click()

    const dialog = page.getByRole("dialog", { name: "Оплата без регистрации" })
    await expect(dialog).toBeVisible()
    // Measure after the zoom-in animation; the dialog must scroll internally
    // instead of running off the scroll-locked page.
    await dialog.evaluate((element) => Promise.all(element.getAnimations().map((animation) => animation.finished)))
    const box = await dialog.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.y + box!.height).toBeLessThanOrEqual(640)

    for (const target of [
        dialog.getByRole("button", { name: "Перейти к оплате" }),
        dialog.getByRole("link", { name: "Войти" }),
    ]) {
        await target.scrollIntoViewIfNeeded()
        await expect(target).toBeVisible()
        await expect(target).toBeInViewport({ ratio: 1 })
    }
})
