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
    await page.getByRole("button", { name: "Перейти к оплате" }).click()

    await expect(page.getByRole("heading", { name: "Оплата подтверждена" })).toBeVisible()
    expect(checkoutPayload).toMatchObject({
        customer_email: "student@example.com",
        tariff: "self",
    })
})
