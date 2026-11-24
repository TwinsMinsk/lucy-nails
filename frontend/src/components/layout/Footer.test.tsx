import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { Footer } from "@/components/layout/Footer"

vi.mock("next/navigation", () => ({ usePathname: () => "/" }))
beforeEach(() => vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", ""))
afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
})

it("lists the support bot among the contacts", () => {
    render(<Footer />)

    const link = screen.getByRole("link", { name: "Поддержка в Telegram" })
    expect(link).toHaveAttribute("href", "https://t.me/lucynails_bot")
    expect(link).toHaveAttribute("target", "_blank")
    expect(link).toHaveAttribute("rel", "noopener noreferrer")
    expect(screen.getByRole("link", { name: "Luci4ek@gmail.com" })).toBeVisible()
})
