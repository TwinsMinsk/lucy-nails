import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

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
