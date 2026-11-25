import { act, cleanup, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { POLL_DEADLINE_MS, PaymentStatus } from "@/app/payment-success/payment-status"
import { sendYandexGoal } from "@/lib/analytics-client"

vi.mock("next/navigation", () => ({
    useSearchParams: () => new URLSearchParams("order_id=order%7C11111111-1111-4111-8111-111111111111&token=secret"),
}))
vi.mock("@/lib/env", () => ({ getPublicApiUrl: () => "https://api.example.test/api" }))
vi.mock("@/lib/analytics-client", () => ({ sendYandexGoal: vi.fn() }))

const json = (status: number, body: unknown = {}) => new Response(JSON.stringify(body), { status })
const fetchMock = vi.fn()

beforeEach(() => {
    vi.useFakeTimers()
    fetchMock.mockReset()
    vi.mocked(sendYandexGoal).mockReset()
    vi.stubGlobal("fetch", fetchMock)
    vi.stubEnv("NEXT_PUBLIC_SUPPORT_BOT_USERNAME", "")
})
afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.useRealTimers()
})

const supportLink = () => screen.getByRole("link", { name: "Напишите в поддержку в Telegram" })

it("links to the support bot with the order the status endpoint signed", async () => {
    fetchMock.mockResolvedValueOnce(json(200, { status: "pending", support_start: "o_signedOrderRef-123" }))
    render(<PaymentStatus />)
    await act(async () => {})
    expect(supportLink()).toHaveAttribute("href", "https://t.me/lucynails_bot?start=o_signedOrderRef-123")
    expect(supportLink()).toHaveAttribute("target", "_blank")
    expect(supportLink()).toHaveAttribute("rel", "noopener noreferrer")
})

it("links to the support bot without an order when the order is unknown", async () => {
    fetchMock.mockResolvedValueOnce(json(404))
    const { container } = render(<PaymentStatus />)
    await act(async () => {})
    expect(supportLink()).toHaveAttribute("href", "https://t.me/lucynails_bot")
    expect(container.querySelector('a[href*="lucysmirnova_nails"]')).toBeNull()
    expect(screen.getByRole("link", { name: "Luci4ek@gmail.com" })).toHaveAttribute("href", "mailto:Luci4ek@gmail.com")
})

it("keeps checking through a temporary server error and confirms the payment", async () => {
    fetchMock
        .mockResolvedValueOnce(json(502))
        .mockResolvedValueOnce(json(200, { status: "pending" }))
        .mockResolvedValueOnce(json(200, { status: "paid", amount: 5900, currency: "RUB", course_id: "course-1" }))
    render(<PaymentStatus />)
    await act(async () => {})
    expect(screen.getByRole("heading", { name: "Ожидаем подтверждение" })).toBeVisible()
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByRole("heading", { name: "Оплата подтверждена" })).toBeVisible()
    expect(sendYandexGoal).toHaveBeenCalledTimes(1)
})

it("asks for help only when the link itself is invalid", async () => {
    fetchMock.mockResolvedValueOnce(json(404))
    render(<PaymentStatus />)
    await act(async () => {})
    expect(screen.getByRole("heading", { name: "Нужна проверка оплаты" })).toBeVisible()
    expect(fetchMock).toHaveBeenCalledTimes(1)
})

it("tells the buyer to wait for the email when confirmation is slow", async () => {
    fetchMock.mockImplementation(async () => json(200, { status: "pending" }))
    render(<PaymentStatus />)
    await act(async () => {})
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(screen.queryByRole("heading", { name: "Нужна проверка оплаты" })).not.toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(POLL_DEADLINE_MS) })
    expect(screen.getByRole("heading", { name: "Платёж ещё обрабатывается" })).toBeVisible()
    expect(screen.getByRole("button", { name: "Проверить ещё раз" })).toBeVisible()
})
