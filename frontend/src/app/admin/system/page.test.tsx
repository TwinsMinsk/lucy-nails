import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { AdminPermissionsContext } from "@/app/admin/permissions"
import System from "@/app/admin/system/page"
import * as api from "@/lib/api"

const toast = vi.hoisted(() => ({ error: vi.fn(), success: vi.fn(), warning: vi.fn() }))
vi.mock("sonner", () => ({ toast }))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetSystemStatus: vi.fn(), adminGetRoles: vi.fn(), adminGetTeamUsers: vi.fn(),
    adminGetAuditLogs: vi.fn(), adminUpdateTeamRoles: vi.fn(),
}))

afterEach(() => { cleanup(); vi.clearAllMocks() })

describe("team roles", () => {
    it("shows the API refusal instead of failing silently", async () => {
        vi.mocked(api.adminGetSystemStatus).mockResolvedValue({ checkout_enabled: true, environment: "test", integrations: {}, outbox_pending: 0, outbox_dead_letter: 0, last_payment_event_at: null })
        vi.mocked(api.adminGetAuditLogs).mockResolvedValue([])
        vi.mocked(api.adminGetRoles).mockResolvedValue([{ id: "role-1", name: "curator", description: "Curator", permissions: [] }])
        vi.mocked(api.adminGetTeamUsers).mockResolvedValue([{ id: "user-1", email: "staff@example.test", full_name: null, roles: ["curator"], mfa_enabled: false, active_sessions: 0 }])
        const refusal = "Почта этого аккаунта не подтверждена."
        vi.mocked(api.adminUpdateTeamRoles).mockRejectedValue(new api.ApiError(409, refusal, "Conflict"))

        render(
            <AdminPermissionsContext.Provider value={["audit.read", "system.manage_roles"]}>
                <System />
            </AdminPermissionsContext.Provider>,
        )
        fireEvent.click(await screen.findByRole("button", { name: "Роли" }))
        fireEvent.change(screen.getByPlaceholderText("Причина изменения ролей"), { target: { value: "New support curator" } })
        fireEvent.click(screen.getByRole("button", { name: "Сохранить" }))

        await waitFor(() => expect(toast.error).toHaveBeenCalledWith(refusal))
        expect(toast.success).not.toHaveBeenCalled()
        expect(screen.getByRole("dialog")).toBeInTheDocument()
    })
})

const baseStatus: api.AdminSystemStatus = {
    checkout_enabled: true, environment: "production", integrations: { redis: true },
    outbox_pending: 1, outbox_retry: 3, outbox_processing: 2, outbox_dead_letter: 0,
    oldest_undelivered_seconds: 120, worker_heartbeat: "alive", worker_alive: true,
    worker_heartbeat_age_seconds: 20, last_payment_event_at: null,
}

const renderAuditor = () => render(
    <AdminPermissionsContext.Provider value={["audit.read"]}>
        <System />
    </AdminPermissionsContext.Provider>,
)

describe("admin system status", () => {
    beforeEach(() => {
        vi.mocked(api.adminGetAuditLogs).mockResolvedValue([])
        vi.mocked(api.adminGetRoles).mockResolvedValue([])
        vi.mocked(api.adminGetTeamUsers).mockResolvedValue([])
    })

    it("shows retry and processing counts and a healthy worker without warnings", async () => {
        vi.mocked(api.adminGetSystemStatus).mockResolvedValue(baseStatus)
        renderAuditor()
        expect(await screen.findByText("Retry: 3")).toBeVisible()
        expect(screen.getByText("Processing: 2")).toBeVisible()
        expect(screen.getByText(/Worker: работает/)).toBeVisible()
        expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    })

    it("warns when the worker is not alive", async () => {
        vi.mocked(api.adminGetSystemStatus).mockResolvedValue({ ...baseStatus, worker_heartbeat: "missing", worker_alive: false, worker_heartbeat_age_seconds: null })
        renderAuditor()
        expect(await screen.findByRole("alert")).toHaveTextContent("не присылает heartbeat")
    })

    it("does not present an unknown heartbeat as healthy", async () => {
        vi.mocked(api.adminGetSystemStatus).mockResolvedValue({ ...baseStatus, worker_heartbeat: "unknown", worker_alive: null, worker_heartbeat_age_seconds: null })
        renderAuditor()
        expect(await screen.findByRole("alert")).toHaveTextContent("Состояние worker уведомлений неизвестно")
    })

    it("warns when the oldest undelivered message is older than 15 minutes", async () => {
        vi.mocked(api.adminGetSystemStatus).mockResolvedValue({ ...baseStatus, oldest_undelivered_seconds: 16 * 60 })
        renderAuditor()
        expect(await screen.findByRole("alert")).toHaveTextContent("ждёт доставки уже 16 мин")
    })
})

describe("admin system load errors", () => {
    it("reports a 5xx as a load failure with retry, not as missing rights", async () => {
        vi.mocked(api.adminGetSystemStatus)
            .mockRejectedValueOnce(new api.ApiError(503, "Service unavailable", "HTTP 503"))
            .mockResolvedValueOnce(baseStatus)
        render(<System />)
        expect(await screen.findByText(/Не удалось загрузить часть системных данных: Service unavailable/)).toBeVisible()
        screen.getByRole("button", { name: "Повторить загрузку" }).click()
        expect(await screen.findByText("Retry: 3")).toBeVisible()
    })

    it("does not show a load error for a 403", async () => {
        vi.mocked(api.adminGetSystemStatus).mockResolvedValue(baseStatus)
        vi.mocked(api.adminGetAuditLogs).mockRejectedValue(new api.ApiError(403, "Permission required: audit.read", "HTTP 403"))
        render(<System />)
        await screen.findByText("Retry: 3")
        expect(screen.queryByText(/Не удалось загрузить часть системных данных/)).not.toBeInTheDocument()
    })
})