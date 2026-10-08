import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import AdminLayout from "@/app/admin/layout"
import Orders from "@/app/admin/orders/page"
import Notifications from "@/app/admin/notifications/page"
import Users from "@/app/admin/users/page"
import Access from "@/app/admin/access/page"
import System from "@/app/admin/system/page"
import Certificates from "@/app/admin/certificates/page"
import Dashboard from "@/app/admin/page"
import * as api from "@/lib/api"

const navigation = vi.hoisted(() => ({ path: "/admin/orders", query: "", replace: vi.fn() }))
vi.mock("next/navigation", () => ({
    usePathname: () => navigation.path,
    useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(navigation.query),
}))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    getMe: vi.fn(), adminGetCapabilities: vi.fn(), adminGetOrders: vi.fn(),
    adminGetPaymentEvents: vi.fn(), adminGetReconciliation: vi.fn(), adminGetRefunds: vi.fn(),
    adminGetStudents: vi.fn(), adminGetStudent: vi.fn(), adminGetCourses: vi.fn(),
    adminGetAccessCourses: vi.fn(), adminGetNotifications: vi.fn(), adminGetEntitlements: vi.fn(),
    adminGetSystemStatus: vi.fn(), adminGetRoles: vi.fn(), adminGetTeamUsers: vi.fn(), adminGetAuditLogs: vi.fn(),
    adminGetCertificates: vi.fn(),
    adminGetDashboard: vi.fn(),
}))

const order = { id: "order-1", customer_email: "b***@example.test", course_title: "Course", tariff: "self", amount_kopecks: 10000, currency: "RUB", access_days: 30, status: "paid", purchase_id: "purchase-1", created_at: "2026-10-07T22:30:00" }
const student = { id: "student-1", email: "student@example.test", role: "student", created_at: "2026-10-07T22:30:00", active_entitlements: 1 }
const recon = { stale_pending_orders: 0, successful_purchases_without_active_entitlement: 0, processed_payment_errors: 0, dead_letter_notifications: 0 }

beforeEach(() => {
    navigation.path = "/admin/orders"; navigation.query = ""; navigation.replace.mockReset()
    vi.mocked(api.getMe).mockResolvedValue({ id: "staff-1", email: "staff@example.test", role: "student", created_at: "2026-10-07T00:00:00Z" } as api.UserResponse)
    vi.mocked(api.adminGetOrders).mockResolvedValue({ items: [order], total: 201, limit: 50, offset: 0 } as api.PageResponse<api.AdminOrder>)
    vi.mocked(api.adminGetPaymentEvents).mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 })
    vi.mocked(api.adminGetReconciliation).mockResolvedValue(recon)
    vi.mocked(api.adminGetRefunds).mockRejectedValue(new api.ApiError(403, "Permission required: refunds.manage", "Forbidden"))
    vi.mocked(api.adminGetStudents).mockResolvedValue({ items: [student], total: 1, limit: 100, offset: 0 } as api.PageResponse<api.AdminStudentListItem>)
    vi.mocked(api.adminGetCourses).mockResolvedValue([])
    vi.mocked(api.adminGetAccessCourses).mockResolvedValue([{ id: "course-1", title: "Hidden course", access_days: 45 }])
    vi.mocked(api.adminGetStudent).mockResolvedValue({ ...student, completed_lessons: 0, tracked_lessons: 0, purchases: [], entitlements: [], certificates: [], notes: [], tags: ["vip"], lesson_progress: [] } as unknown as api.AdminStudentDetail)
    vi.mocked(api.adminGetNotifications).mockResolvedValue({ items: [], total: 201, limit: 50, offset: 0 })
    vi.mocked(api.adminGetSystemStatus).mockResolvedValue({ checkout_enabled: true, environment: "test", integrations: {}, outbox_pending: 0, outbox_dead_letter: 0, last_payment_event_at: null })
    vi.mocked(api.adminGetRoles).mockRejectedValue(new Error("Forbidden"))
    vi.mocked(api.adminGetTeamUsers).mockRejectedValue(new Error("Forbidden"))
    vi.mocked(api.adminGetAuditLogs).mockResolvedValue([])
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

const enter = (roles: string[], permissions: string[], page: React.ReactNode) => {
    vi.mocked(api.adminGetCapabilities).mockResolvedValue({ roles, permissions })
    render(<AdminLayout>{page}</AdminLayout>)
}

describe("admin operational permissions", () => {
    it.each(["orders", "notifications", "users", "access"] as const)("ignores an older %s response after the URL page changes", async (kind) => {
        const component = { orders: Orders, notifications: Notifications, users: Users, access: Access }[kind]
        const fetchPage = { orders: api.adminGetOrders, notifications: api.adminGetNotifications, users: api.adminGetStudents, access: api.adminGetEntitlements }[kind]
        let resolveOld: (value: unknown) => void = () => {}
        const old = new Promise((resolve) => { resolveOld = resolve })
        const oldItem = { ...order, ...student, user_email: "old@example.test", customer_email: "old@example.test", email: "old@example.test", recipient: "old@example.test", id: "old", course_title: "Course", status: "active", source: "manual", kind: "activation", channel: "email", attempts: 0, max_attempts: 5 }
        const newItem = { ...oldItem, id: "new", user_email: "new@example.test", customer_email: "new@example.test", email: "new@example.test", recipient: "new@example.test" }
        vi.mocked(fetchPage).mockImplementationOnce(() => old as never).mockResolvedValueOnce({ items: [newItem], total: 201, limit: 50, offset: 50 } as never)
        navigation.path = `/admin/${kind}`
        const Component = component
        const view = render(<Component />)
        await waitFor(() => expect(fetchPage).toHaveBeenCalledTimes(1))
        navigation.query = "offset=50"
        view.rerender(<Component />)
        await screen.findAllByText("new@example.test")
        await act(async () => { resolveOld({ items: [oldItem], total: 201, limit: 50, offset: 0 }); await old })
        expect(screen.queryAllByText("old@example.test")).toHaveLength(0)
        expect(screen.getAllByText("new@example.test").length).toBeGreaterThan(0)
    })
    it("restores student search and pages beyond 200 from URL", async () => {
        navigation.path = "/admin/users"; navigation.query = "search=student&offset=200"
        vi.mocked(api.adminGetStudents).mockResolvedValue({ items: [student], total: 201, limit: 50, offset: 200 } as api.PageResponse<api.AdminStudentListItem>)
        enter(["curator"], ["users.read"], <Users />)
        await screen.findByRole("button", { name: /student@example.test/ })
        expect(api.adminGetStudents).toHaveBeenCalledWith({ search: "student", limit: 50, offset: 200 })
        fireEvent.click(screen.getByRole("button", { name: "Назад" }))
        expect(navigation.replace).toHaveBeenCalledWith("/admin/users?search=student&offset=150", { scroll: false })
    })
    it("restores entitlement search status and pages beyond 200 from URL", async () => {
        navigation.path = "/admin/access"; navigation.query = "search=student&status=revoked&offset=200"
        vi.mocked(api.adminGetEntitlements).mockResolvedValue({ items: [], total: 201, limit: 50, offset: 200 })
        enter(["curator"], ["users.read"], <Access />)
        await screen.findByText("201 записей")
        expect(api.adminGetEntitlements).toHaveBeenCalledWith({ search: "student", status: "revoked", limit: 50, offset: 200 })
        fireEvent.click(screen.getByRole("button", { name: "Назад" }))
        expect(navigation.replace).toHaveBeenCalledWith("/admin/access?search=student&status=revoked&offset=150", { scroll: false })
    })
    it("marks duplicate payment incidents visibly", async () => {
        vi.mocked(api.adminGetPaymentEvents).mockResolvedValue({ items: [{ id: "event-1", event_type: "payment", processing_status: "financial_incident", error_code: "duplicate_order_payment", error_detail: "Duplicate payment", received_at: "2026-10-08T00:00:00" }], total: 1, limit: 50, offset: 0 } as api.PageResponse<api.AdminPaymentEvent>)
        enter(["analyst"], ["commerce.read"], <Orders />)
        expect(await screen.findByText("Финансовый инцидент")).toBeVisible()
    })
    it("keeps an analytics-only overview usable without commerce.read", async () => {
        navigation.path = "/admin"
        vi.mocked(api.adminGetReconciliation).mockRejectedValue(new Error("Forbidden"))
        vi.mocked(api.adminGetDashboard).mockResolvedValue({ total_students: 3, active_entitlements: 1, gross_revenue_kopecks: 10000, refunded_kopecks: 0, net_revenue_kopecks: 10000, pending_orders: 0, payment_errors: 0, notification_dead_letters: 0, expiring_entitlements_7d: 0 })
        enter(["analyst"], ["analytics.read"], <Dashboard />)
        expect(await screen.findByRole("heading", { name: "Операционный центр" })).toBeVisible()
        expect(api.adminGetReconciliation).not.toHaveBeenCalled()
    })
    it.each([
        { role: "owner", path: "/admin/orders", permissions: ["analytics.read", "users.read", "users.manage", "access.manage", "commerce.read", "refunds.manage", "content.manage", "notifications.manage", "audit.read", "certificates.manage", "system.manage_roles", "system.manage_operations"], users: true, orders: true, content: true },
        { role: "admin", path: "/admin/orders", permissions: ["analytics.read", "users.read", "users.manage", "access.manage", "commerce.read", "refunds.manage", "content.manage", "notifications.manage", "audit.read", "certificates.manage", "system.manage_operations"], users: true, orders: true, content: true },
        { role: "content_manager", path: "/admin/courses", permissions: ["content.manage"], users: false, orders: false, content: true },
        { role: "curator", path: "/admin/users", permissions: ["users.read", "access.manage", "notifications.manage", "certificates.manage"], users: true, orders: false, content: false },
        { role: "analyst", path: "/admin/orders", permissions: ["analytics.read", "commerce.read", "audit.read"], users: false, orders: true, content: false },
    ])("renders only permitted navigation for $role", async ({ role, path, permissions, users, orders, content }) => {
        navigation.path = path
        enter([role], permissions, <h1>Ready</h1>)
        await screen.findByRole("heading", { name: "Ready" })
        expect(screen.queryAllByRole("link", { name: "Ученики" }).length > 0).toBe(users)
        expect(screen.queryAllByRole("link", { name: "Заказы и оплаты" }).length > 0).toBe(orders)
        expect(screen.queryAllByRole("link", { name: "Курсы и контент" }).length > 0).toBe(content)
    })

    it("shows revoked certificate status without download or lifecycle buttons", async () => {
        navigation.path = "/admin/certificates"
        vi.mocked(api.adminGetCertificates).mockResolvedValue({ items: [{ id: "cert-1", certificate_number: "CERT-1", student_name: "Learner", student_email: "student@example.test", course_title: "Course", status: "revoked", issued_at: "2026-10-07T22:30:00", revoke_reason: "Refund processed" }], total: 1, limit: 50, offset: 0 } as api.PageResponse<api.AdminCertificate>)
        enter(["curator"], ["certificates.manage"], <Certificates />)
        expect(await screen.findByText("Отозван")).toBeVisible()
        expect(screen.queryByRole("link", { name: "PDF" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: "Отозвать" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: "Отправить" })).not.toBeInTheDocument()
    })
    it("keeps analyst commerce readable without refunds.manage", async () => {
        enter(["analyst"], ["analytics.read", "commerce.read", "audit.read"], <Orders />)
        expect(await screen.findByText("b***@example.test")).toBeVisible()
        expect(screen.queryByRole("button", { name: "Возврат" })).not.toBeInTheDocument()
        expect(api.adminGetRefunds).not.toHaveBeenCalled()
        expect(screen.getByText("08.10.2026, 01:30:00")).toBeVisible()
        expect(screen.getByText("Заказы (201)")).toBeVisible()
    })

    it("keeps successful orders when a permitted refund section fails", async () => {
        enter(["admin"], ["commerce.read", "refunds.manage"], <Orders />)
        expect(await screen.findByText("b***@example.test")).toBeVisible()
    })

    it("pages orders using server offset and retains URL search and status", async () => {
        navigation.query = "search=buyer&status=paid&offset=200"
        enter(["analyst"], ["commerce.read"], <Orders />)
        expect(await screen.findByText("b***@example.test")).toBeVisible()
        expect(api.adminGetOrders).toHaveBeenCalledWith({ search: "buyer", status: "paid", limit: 50, offset: 200 })
        expect(screen.getByPlaceholderText("Email клиента")).toHaveValue("buyer")
        fireEvent.click(screen.getByRole("button", { name: "Назад" }))
        expect(navigation.replace).toHaveBeenCalledWith("/admin/orders?search=buyer&status=paid&offset=150", { scroll: false })
    })

    it("hides users.manage mutations from curator while allowing course access", async () => {
        navigation.path = "/admin/users"
        enter(["curator"], ["users.read", "access.manage", "notifications.manage", "certificates.manage"], <Users />)
        fireEvent.click(await screen.findByRole("button", { name: /student@example.test/ }))
        expect(await screen.findByRole("heading", { name: "Выдать доступ" })).toBeVisible()
        expect(screen.queryByRole("button", { name: "Добавить заметку" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: "Сохранить теги" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: "Отправить ссылку для входа" })).not.toBeInTheDocument()
        expect(api.adminGetCourses).not.toHaveBeenCalled()
        expect(api.adminGetAccessCourses).toHaveBeenCalled()
    })

    it("shows paginated notifications and preserves URL filters", async () => {
        navigation.path = "/admin/notifications"; navigation.query = "search=buyer&status=dead_letter&channel=email&offset=200"
        enter(["curator"], ["notifications.manage"], <Notifications />)
        expect(await screen.findByText("Очередь (201)")).toBeVisible()
        expect(api.adminGetNotifications).toHaveBeenCalledWith({ search: "buyer", status: "dead_letter", channel: "email", limit: 50, offset: 200 })
        expect(screen.getByPlaceholderText("Получатель или тип сообщения")).toHaveValue("buyer")
        fireEvent.click(screen.getByRole("button", { name: "Назад" }))
        expect(navigation.replace).toHaveBeenCalledWith("/admin/notifications?search=buyer&status=dead_letter&channel=email&offset=150", { scroll: false })
    })

    it("does not expose checkout switch or role calls to analyst", async () => {
        navigation.path = "/admin/system"
        enter(["analyst"], ["audit.read"], <System />)
        await screen.findByRole("heading", { name: "Аудит и система" })
        expect(screen.queryByRole("button", { name: /checkout/i })).not.toBeInTheDocument()
        expect(api.adminGetRoles).not.toHaveBeenCalled()
        expect(api.adminGetTeamUsers).not.toHaveBeenCalled()
    })
})
