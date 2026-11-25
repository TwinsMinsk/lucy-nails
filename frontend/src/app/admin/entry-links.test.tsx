import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import Dashboard from "@/app/admin/page"
import { AdminPermissionsContext } from "@/app/admin/permissions"
import { Header } from "@/components/layout/Header"
import { firstAdminRoute } from "@/lib/admin-access"
import * as api from "@/lib/api"

vi.mock("next/navigation", () => ({
    usePathname: () => "/dashboard",
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(""),
}))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    getMe: vi.fn(), adminGetCapabilities: vi.fn(), adminGetDashboard: vi.fn(), adminGetReconciliation: vi.fn(),
}))

beforeEach(() => {
    vi.mocked(api.getMe).mockResolvedValue({ id: "staff-1", email: "staff@example.test", role: "student", created_at: "2026-11-01T00:00:00" } as api.UserResponse)
    vi.mocked(api.adminGetDashboard).mockResolvedValue({ total_students: 3, active_entitlements: 1, gross_revenue_kopecks: 10000, refunded_kopecks: 0, net_revenue_kopecks: 10000, pending_orders: 0, payment_errors: 0, notification_dead_letters: 0, expiring_entitlements_7d: 0 })
    vi.mocked(api.adminGetReconciliation).mockResolvedValue({ stale_pending_orders: 0, successful_purchases_without_active_entitlement: 0, processed_payment_errors: 0, dead_letter_notifications: 0 })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

const openMenu = async () => {
    const trigger = await screen.findByRole("button", { name: /S/ })
    fireEvent.keyDown(trigger, { key: "Enter" })
}

describe("admin entry from the header", () => {
    it.each([
        ["analyst", ["analytics.read", "commerce.read", "audit.read"], "/admin"],
        ["curator", ["users.read", "access.manage", "notifications.manage", "certificates.manage"], "/admin/users"],
        ["content_manager", ["content.manage"], "/admin/courses"],
        ["marketer", ["ads.read"], "/admin/ads"],
    ])("links a %s to the first admin page they may open", async (role, permissions, href) => {
        vi.mocked(api.adminGetCapabilities).mockResolvedValue({ roles: [role], permissions })
        render(<Header />)
        await openMenu()
        const link = await screen.findByRole("menuitem", { name: /Админ панель/ })
        expect(link).toHaveAttribute("href", href)
        expect(screen.getByText("Команда")).toBeVisible()
    })

    it("shows a student no admin link", async () => {
        vi.mocked(api.adminGetCapabilities).mockResolvedValue({ roles: [], permissions: [] })
        render(<Header />)
        await openMenu()
        expect(await screen.findByText("Студент")).toBeVisible()
        expect(screen.queryByRole("menuitem", { name: /Админ панель/ })).not.toBeInTheDocument()
    })

    it("maps legacy admin capabilities to the dashboard", () => {
        expect(firstAdminRoute(["*"])).toBe("/admin")
        expect(firstAdminRoute([])).toBeNull()
    })
})

describe("admin dashboard links", () => {
    it("links only to sections the user may open", async () => {
        render(<AdminPermissionsContext.Provider value={["analytics.read", "commerce.read", "audit.read"]}><Dashboard /></AdminPermissionsContext.Provider>)
        await screen.findByText("Операционный центр")
        const hrefs = screen.getAllByRole("link").map((link) => link.getAttribute("href"))
        expect(hrefs).toContain("/admin/orders")
        expect(hrefs).not.toContain("/admin/users")
        expect(hrefs).not.toContain("/admin/access")
        expect(hrefs).not.toContain("/admin/notifications")
        expect(screen.getByText("Ученики")).toBeVisible()
    })
})
