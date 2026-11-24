import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import Access from "@/app/admin/access/page"
import Orders from "@/app/admin/orders/page"
import System from "@/app/admin/system/page"
import { AdminPermissionsContext } from "@/app/admin/permissions"
import * as api from "@/lib/api"

vi.mock("next/navigation", () => ({
    usePathname: () => "/admin",
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(""),
}))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetEntitlements: vi.fn(), adminExtendEntitlement: vi.fn(), adminRevokeEntitlement: vi.fn(),
    adminChangeEntitlementState: vi.fn(),
    adminGetOrders: vi.fn(), adminGetPaymentEvents: vi.fn(), adminGetReconciliation: vi.fn(),
    adminGetRefunds: vi.fn(), adminCreateRefund: vi.fn(),
    adminGetSystemStatus: vi.fn(), adminGetRoles: vi.fn(), adminGetTeamUsers: vi.fn(),
    adminGetAuditLogs: vi.fn(), adminUpdateTeamRoles: vi.fn(),
}))

const entitlement: api.AdminEntitlement = {
    id: "ent-1", user_id: "user-1", user_email: "student@example.test", course_id: "course-1",
    course_title: "Course", source: "purchase", tariff: "self", status: "active",
    starts_at: "2026-11-01T00:00:00", expires_at: "2026-12-01T00:00:00", reason: null, revoked_at: null,
} as api.AdminEntitlement

const order: api.AdminOrder = {
    id: "order-1", customer_email: "buyer@example.test", course_id: "course-1", course_title: "Course",
    tariff: "self", amount_kopecks: 590000, currency: "RUB", access_days: 30, status: "partially_refunded",
    order_status: "paid", purchase_id: "purchase-1", refunded_kopecks: 100000, refundable_kopecks: 490000,
    created_at: "2026-11-01T00:00:00", updated_at: "2026-11-01T00:00:00",
}

const withPermissions = (permissions: string[], node: React.ReactNode) => render(
    <AdminPermissionsContext.Provider value={permissions}>{node}</AdminPermissionsContext.Provider>,
)

const deferred = <T,>() => {
    let resolve: (value: T) => void = () => {}
    let reject: (error: unknown) => void = () => {}
    const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail })
    return { promise, resolve, reject }
}

beforeEach(() => {
    vi.mocked(api.adminGetEntitlements).mockResolvedValue({ items: [entitlement], total: 1, limit: 50, offset: 0 })
    vi.mocked(api.adminGetOrders).mockResolvedValue({ items: [order], total: 1, limit: 50, offset: 0 })
    vi.mocked(api.adminGetPaymentEvents).mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
    vi.mocked(api.adminGetReconciliation).mockResolvedValue({ stale_pending_orders: 0, successful_purchases_without_active_entitlement: 0, processed_payment_errors: 0, dead_letter_notifications: 0 })
    vi.mocked(api.adminGetRefunds).mockResolvedValue([])
    vi.mocked(api.adminGetSystemStatus).mockResolvedValue({ checkout_enabled: true, environment: "test", integrations: {}, outbox_pending: 0, outbox_dead_letter: 0, worker_heartbeat: "alive", worker_alive: true })
    vi.mocked(api.adminGetRoles).mockResolvedValue([{ id: "role-1", name: "owner", description: "Owner", permissions: [] }])
    vi.mocked(api.adminGetTeamUsers).mockResolvedValue([{ id: "owner-1", email: "owner@example.test", full_name: null, roles: ["owner"], mfa_enabled: true, active_sessions: 1 }])
    vi.mocked(api.adminGetAuditLogs).mockResolvedValue([])
})
afterEach(() => { cleanup(); vi.clearAllMocks(); vi.restoreAllMocks() })

describe("admin mutations are single-flight and report API errors", () => {
    it("extends once per dialog with an idempotency key and re-reads the list", async () => {
        const pending = deferred<{ entitlement_id: string; status: string; expires_at: string }>()
        vi.mocked(api.adminExtendEntitlement).mockReturnValue(pending.promise)
        withPermissions(["users.read", "access.manage"], <Access />)
        fireEvent.click(await screen.findByRole("button", { name: "Продлить" }))
        fireEvent.change(screen.getByLabelText("Дней продления"), { target: { value: "10" } })
        fireEvent.change(screen.getByPlaceholderText("Причина продления (обязательно)"), { target: { value: "Goodwill extension" } })
        const submit = screen.getAllByRole("button", { name: /^Продлить$/ }).at(-1) as HTMLElement
        fireEvent.click(submit)
        fireEvent.click(submit)
        await waitFor(() => expect(submit).toBeDisabled())
        expect(api.adminExtendEntitlement).toHaveBeenCalledTimes(1)
        const [id, days, reason, key] = vi.mocked(api.adminExtendEntitlement).mock.calls[0]
        expect([id, days, reason]).toEqual(["ent-1", 10, "Goodwill extension"])
        expect(key).toMatch(/^[0-9a-f-]{36}$/)
        pending.resolve({ entitlement_id: "ent-1", status: "active", expires_at: "2026-12-11T00:00:00" })
        await waitFor(() => expect(api.adminGetEntitlements).toHaveBeenCalledTimes(2))
    })

    it("shows a 422 from the extension endpoint", async () => {
        vi.mocked(api.adminExtendEntitlement).mockRejectedValue(new api.ApiError(422, "Fully refunded access cannot be restored or extended", "HTTP 422"))
        withPermissions(["users.read", "access.manage"], <Access />)
        fireEvent.click(await screen.findByRole("button", { name: "Продлить" }))
        fireEvent.change(screen.getByPlaceholderText("Причина продления (обязательно)"), { target: { value: "Goodwill extension" } })
        fireEvent.click(screen.getAllByRole("button", { name: /^Продлить$/ }).at(-1) as HTMLElement)
        expect(await screen.findByText("Fully refunded access cannot be restored or extended")).toBeVisible()
    })

    it("creates one refund request per submit and shows the API error", async () => {
        const pending = deferred<api.AdminRefund>()
        vi.mocked(api.adminCreateRefund).mockReturnValue(pending.promise)
        withPermissions(["commerce.read", "refunds.manage"], <Orders />)
        fireEvent.click(await screen.findByRole("button", { name: /Возврат/ }))
        fireEvent.change(screen.getByPlaceholderText("Причина возврата"), { target: { value: "Customer request" } })
        const submit = screen.getByRole("button", { name: /Создать заявку/ })
        fireEvent.click(submit)
        fireEvent.click(submit)
        expect(api.adminCreateRefund).toHaveBeenCalledTimes(1)
        pending.reject(new api.ApiError(422, "Refund amount exceeds the remaining paid amount", "HTTP 422"))
        expect(await screen.findByText("Refund amount exceeds the remaining paid amount")).toBeVisible()
        await waitFor(() => expect(api.adminGetOrders).toHaveBeenCalledTimes(2))
    })

    it("saves roles once and shows a 409", async () => {
        vi.mocked(api.adminUpdateTeamRoles).mockRejectedValue(new api.ApiError(409, "Cannot remove the last owner", "HTTP 409"))
        withPermissions(["audit.read", "system.manage_roles"], <System />)
        fireEvent.click(await screen.findByRole("button", { name: "Роли" }))
        fireEvent.change(screen.getByPlaceholderText("Причина изменения ролей"), { target: { value: "Rotate ownership" } })
        const save = screen.getByRole("button", { name: /Сохранить/ })
        fireEvent.click(save)
        fireEvent.click(save)
        expect(await screen.findByText("Cannot remove the last owner")).toBeVisible()
        expect(api.adminUpdateTeamRoles).toHaveBeenCalledTimes(1)
    })
})

describe("refund form after a partial refund", () => {
    it("defaults to the remaining refundable amount and shows what was refunded", async () => {
        withPermissions(["commerce.read", "refunds.manage"], <Orders />)
        fireEvent.click(await screen.findByRole("button", { name: /Возврат/ }))
        expect(screen.getByLabelText("Сумма возврата, копейки")).toHaveValue(490000)
        expect(screen.getByText(/уже возвращено 1\s000 ₽/)).toBeVisible()
        expect(screen.getByText(/доступно к возврату 4\s900 ₽/)).toBeVisible()
        fireEvent.change(screen.getByPlaceholderText("Причина возврата"), { target: { value: "Customer request" } })
        fireEvent.change(screen.getByLabelText("Сумма возврата, копейки"), { target: { value: "590000" } })
        expect(screen.getByRole("button", { name: /Создать заявку/ })).toBeDisabled()
    })

    it("offers no refund for a fully refunded order", async () => {
        vi.mocked(api.adminGetOrders).mockResolvedValue({ items: [{ ...order, status: "refunded", refunded_kopecks: 590000, refundable_kopecks: 0 }], total: 1, limit: 50, offset: 0 })
        withPermissions(["commerce.read", "refunds.manage"], <Orders />)
        await screen.findByText("buyer@example.test")
        expect(screen.queryByRole("button", { name: /Возврат/ })).not.toBeInTheDocument()
    })
})