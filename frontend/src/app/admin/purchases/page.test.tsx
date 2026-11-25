import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { AdminPermissionsContext } from "@/app/admin/permissions"
import Purchases from "@/app/admin/purchases/page"
import * as api from "@/lib/api"

vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetPurchases: vi.fn(), adminRevokeAccess: vi.fn(),
}))

const purchase: api.AdminPurchaseResponse = {
    id: "purchase-1", payment_id: "pay-1", user_email: "b***@example.test", course_title: "Course",
    tariff: "self", amount_kopecks: 590000, payment_status: "success", expires_at: "2099-01-01T00:00:00",
    paid_at: "2026-11-01T00:00:00", created_at: "2026-11-01T00:00:00", entitlement_id: "ent-1",
    access_status: "active", access_expires_at: "2099-01-01T00:00:00", kind: "paid",
}

const renderAs = (permissions: string[]) => render(
    <AdminPermissionsContext.Provider value={permissions}><Purchases /></AdminPermissionsContext.Provider>,
)

beforeEach(() => {
    vi.mocked(api.adminGetPurchases).mockResolvedValue({ items: [purchase], total: 120, limit: 50, offset: 0 })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe("admin purchases", () => {
    it("defaults to real payments and pages through the list", async () => {
        renderAs(["commerce.read"])
        expect(await screen.findByText("Покупки и доступы (120)")).toBeVisible()
        expect(api.adminGetPurchases).toHaveBeenCalledWith({ kind: "paid", limit: 50, offset: 0 })
        fireEvent.click(screen.getByRole("button", { name: "Далее" }))
        await waitFor(() => expect(api.adminGetPurchases).toHaveBeenLastCalledWith({ kind: "paid", limit: 50, offset: 50 }))
        fireEvent.change(screen.getByLabelText("Вид записей"), { target: { value: "manual" } })
        await waitFor(() => expect(api.adminGetPurchases).toHaveBeenLastCalledWith({ kind: "manual", limit: 50, offset: 0 }))
    })

    it("hides revoke from a reader without refunds.manage", async () => {
        renderAs(["commerce.read"])
        await screen.findByText("b***@example.test")
        expect(screen.queryByRole("button", { name: /Отозвать/ })).not.toBeInTheDocument()
    })

    it("offers revoke with refunds.manage and re-reads the list after success", async () => {
        vi.spyOn(window, "confirm").mockReturnValue(true)
        vi.spyOn(window, "prompt").mockReturnValue("Chargeback confirmed")
        vi.mocked(api.adminRevokeAccess).mockResolvedValue({ message: "Access revoked", purchase_id: "purchase-1", payment_status: "success", access_status: "revoked" } as never)
        renderAs(["commerce.read", "refunds.manage"])
        fireEvent.click(await screen.findByRole("button", { name: /Отозвать/ }))
        await waitFor(() => expect(api.adminRevokeAccess).toHaveBeenCalledWith("purchase-1", "Chargeback confirmed"))
        await waitFor(() => expect(api.adminGetPurchases).toHaveBeenCalledTimes(2))
    })

    it("shows a load error with retry instead of an empty list", async () => {
        vi.mocked(api.adminGetPurchases).mockRejectedValueOnce(new api.ApiError(503, "Service unavailable", "HTTP 503"))
        renderAs(["commerce.read"])
        expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить покупки")
        expect(screen.queryByText("Покупок пока нет.")).not.toBeInTheDocument()
        fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку" }))
        expect(await screen.findByText("b***@example.test")).toBeVisible()
    })
})

describe("admin purchases against a backend not yet updated", () => {
    it("explains a 404 from the new path instead of crashing", async () => {
        vi.mocked(api.adminGetPurchases).mockRejectedValueOnce(new api.ApiError(404, "Not Found", "HTTP 404"))
        renderAs(["commerce.read"])
        expect(await screen.findByRole("alert")).toHaveTextContent("сервер ещё не обновлён")
    })

    it("explains a plain list (old contract) instead of crashing", async () => {
        vi.mocked(api.adminGetPurchases).mockResolvedValueOnce([purchase] as unknown as api.PageResponse<api.AdminPurchaseResponse>)
        renderAs(["commerce.read"])
        expect(await screen.findByRole("alert")).toHaveTextContent("сервер ещё не обновлён")
    })
})