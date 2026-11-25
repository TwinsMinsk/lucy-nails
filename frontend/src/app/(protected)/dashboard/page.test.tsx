import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import DashboardPage from "@/app/(protected)/dashboard/page"

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }))
vi.mock("@/components/landing/PaymentButton", () => ({ PaymentButton: () => null }))
vi.mock("@/components/certificate/CertificateClaimDialog", () => ({ CertificateClaimDialog: () => null }))
vi.mock("@/lib/api", () => ({
    getMe: vi.fn(async () => ({ email: "anna@example.com" })),
    getMyCourses: vi.fn(async () => []),
    getMyExpiredCourses: vi.fn(async () => []),
    isAuthError: () => false,
}))
beforeEach(() => vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", ""))
afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
})

it("links the student to the support bot", async () => {
    render(<DashboardPage />)

    const support = await screen.findByRole("link", { name: "Поддержка" })
    expect(support).toHaveAttribute("href", "https://t.me/lucynails_bot")
    expect(support).toHaveAttribute("target", "_blank")
    expect(support).toHaveAttribute("rel", "noopener noreferrer")
    expect(screen.getByRole("link", { name: "Программа курса" })).toHaveAttribute("href", "/#program")
})
