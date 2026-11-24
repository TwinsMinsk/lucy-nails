import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { toast } from "sonner"
import { PaymentButton } from "@/components/landing/PaymentButton"
import { getMe, getPaymentLink } from "@/lib/api"

vi.mock("@/components/landing/GuestCheckoutDialog", () => ({ GuestCheckoutDialog: () => null }))
vi.mock("@/lib/api", () => ({ getMe: vi.fn(), getPaymentLink: vi.fn(), isAuthError: () => false }))
vi.mock("@/lib/analytics-client", () => ({ sendYandexGoal: vi.fn(), trackPublicEvent: vi.fn() }))
vi.mock("@/lib/attribution", () => ({ captureCheckoutAttribution: () => null }))
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }))
beforeEach(() => vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", ""))
afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    document.cookie = "auth_session=; expires=Thu, 01 Jan 1970 00:00:00 GMT"
})

it("disables payment when the canonical course is unavailable", () => {
    render(<PaymentButton courseId={null} tariff="self">Начать обучение</PaymentButton>)
    expect(screen.getByRole("button", { name: "Начать обучение" })).toBeDisabled()
})

it("offers the support bot when the payment link cannot be created", async () => {
    document.cookie = "auth_session=1"
    vi.mocked(getMe).mockResolvedValue({ email: "member@example.com" } as never)
    vi.mocked(getPaymentLink).mockResolvedValue({ url: "" } as never)
    const open = vi.spyOn(window, "open").mockImplementation(() => null)

    render(<PaymentButton courseId="course-1" tariff="self">Начать обучение</PaymentButton>)
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Начать обучение" })) })

    expect(toast.error).toHaveBeenCalledTimes(1)
    const [title, options] = vi.mocked(toast.error).mock.calls[0] as [string, { description: string; action: { label: string; onClick: () => void } }]
    expect(title).toBe("Ошибка при генерации ссылки")
    expect(options.description).toBe("Попробуйте позже или напишите нам.")
    expect(options.action.label).toBe("Написать в Telegram")
    options.action.onClick()
    expect(open).toHaveBeenCalledWith("https://t.me/lucynails_bot", "_blank", "noopener,noreferrer")
})
