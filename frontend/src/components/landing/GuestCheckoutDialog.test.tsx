import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { GuestCheckoutDialog } from "@/components/landing/GuestCheckoutDialog"

vi.mock("@/lib/api", () => ({ getGuestPaymentLink: vi.fn() }))
vi.mock("@/lib/analytics-client", () => ({ sendYandexGoal: vi.fn() }))
vi.mock("@/lib/attribution", () => ({ captureCheckoutAttribution: () => null }))
beforeEach(() => vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", ""))
afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
})

it("offers the support bot for payment questions below the pay button", () => {
    render(<GuestCheckoutDialog open onOpenChange={vi.fn()} courseId="course-1" tariff="self" />)

    const pay = screen.getByRole("button", { name: "Перейти к оплате" })
    const support = screen.getByRole("link", { name: "Напишите в поддержку в Telegram" })
    expect(support).toHaveAttribute("href", "https://t.me/lucynails_bot")
    expect(support).toHaveAttribute("target", "_blank")
    expect(support).toHaveAttribute("rel", "noopener noreferrer")
    expect(pay.compareDocumentPosition(support) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})
