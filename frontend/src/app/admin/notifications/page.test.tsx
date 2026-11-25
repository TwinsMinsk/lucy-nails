import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import Notifications from "@/app/admin/notifications/page"
import * as api from "@/lib/api"

vi.mock("next/navigation", () => ({
    usePathname: () => "/admin/notifications",
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(""),
}))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetNotifications: vi.fn(), adminRetryNotification: vi.fn(),
}))

const message = (id: string, status: string): api.AdminNotification => ({
    id, kind: "access_granted", channel: "email", recipient: `${id}@example.test`, status,
    attempts: 1, max_attempts: 5, next_attempt_at: "2026-11-01T00:00:00", sent_at: null,
    last_error: null, created_at: "2026-11-01T00:00:00", updated_at: "2026-11-01T00:00:00",
})

beforeEach(() => {
    vi.mocked(api.adminGetNotifications).mockResolvedValue({
        items: ["pending", "processing", "retry", "sent", "dead_letter"].map((status) => message(status, status)),
        total: 5, limit: 50, offset: 0,
    })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe("admin notifications", () => {
    it("offers retry only for retry and dead_letter messages", async () => {
        render(<Notifications />)
        await screen.findByText("processing@example.test")
        expect(screen.getAllByRole("button", { name: /Повторить/ })).toHaveLength(2)
        const rows = screen.getAllByRole("row")
        const withButton = rows.filter((row) => row.textContent?.includes("Повторить")).map((row) => row.textContent)
        expect(withButton.some((text) => text?.includes("retry@example.test"))).toBe(true)
        expect(withButton.some((text) => text?.includes("dead_letter@example.test"))).toBe(true)
    })

    it("shows the 409 message and blocks a second submit while in flight", async () => {
        let reject: (error: unknown) => void = () => {}
        vi.mocked(api.adminRetryNotification).mockImplementation(() => new Promise((_, fail) => { reject = fail }))
        render(<Notifications />)
        await screen.findByText("retry@example.test")
        fireEvent.click(screen.getAllByRole("button", { name: /Повторить/ })[0])
        fireEvent.change(screen.getByPlaceholderText("Причина ручного повтора"), { target: { value: "Provider is back" } })
        const submit = screen.getByRole("button", { name: /Вернуть в очередь/ })
        fireEvent.click(submit)
        await waitFor(() => expect(submit).toBeDisabled())
        fireEvent.click(submit)
        expect(api.adminRetryNotification).toHaveBeenCalledTimes(1)
        reject(new api.ApiError(409, "Повтор невозможен: уведомление в статусе «sent».", "HTTP 409"))
        expect(await screen.findByText(/Повтор невозможен/)).toBeVisible()
        // The list is re-read so the operator sees the real state.
        await waitFor(() => expect(api.adminGetNotifications).toHaveBeenCalledTimes(2))
    })

    it("shows a load error with retry instead of an empty queue", async () => {
        vi.mocked(api.adminGetNotifications).mockRejectedValueOnce(new api.ApiError(500, "Internal error", "HTTP 500"))
        render(<Notifications />)
        expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить очередь")
        fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }))
        expect(await screen.findByText("retry@example.test")).toBeVisible()
    })
})
