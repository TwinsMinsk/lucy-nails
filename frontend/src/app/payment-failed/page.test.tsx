import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import PaymentFailedPage from "@/app/payment-failed/page"

beforeEach(() => vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", ""))
afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
})

it("sends buyers to the support bot instead of a personal contact", () => {
    const { container } = render(<PaymentFailedPage />)

    const link = screen.getByRole("link", { name: "Напишите в поддержку в Telegram" })
    expect(link).toHaveAttribute("href", "https://t.me/lucynails_bot")
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
    expect(container.querySelector('a[href*="lucysmirnova_nails"]')).toBeNull()
    expect(screen.getByRole("link", { name: /Попробовать ещё раз/ })).toHaveAttribute("href", "/#pricing")
})
