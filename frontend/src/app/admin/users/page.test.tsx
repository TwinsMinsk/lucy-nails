import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { AdminPermissionsContext } from "@/app/admin/permissions"
import Users from "@/app/admin/users/page"
import * as api from "@/lib/api"

vi.mock("next/navigation", () => ({
    usePathname: () => "/admin/users",
    useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
    useSearchParams: () => new URLSearchParams(""),
}))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetStudents: vi.fn(), adminGetStudent: vi.fn(), adminGetAccessCourses: vi.fn(),
    adminGrantAccess: vi.fn(), adminCreateStudent: vi.fn(),
}))

const student = { id: "student-1", email: "student@example.test", role: "student", created_at: "2026-10-07T22:30:00", active_entitlements: 0 }

const renderUsers = () => render(
    <AdminPermissionsContext.Provider value={["users.read", "access.manage"]}><Users /></AdminPermissionsContext.Provider>,
)

const deferred = <T,>() => {
    let resolve: (value: T) => void = () => {}
    let reject: (error: unknown) => void = () => {}
    const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail })
    return { promise, resolve, reject }
}

beforeEach(() => {
    // Radix Select needs these browser APIs, which jsdom lacks.
    Element.prototype.scrollIntoView = vi.fn()
    Element.prototype.hasPointerCapture = vi.fn(() => false)
    Element.prototype.releasePointerCapture = vi.fn()
    vi.mocked(api.adminGetStudents).mockResolvedValue({ items: [student], total: 1, limit: 50, offset: 0 } as api.PageResponse<api.AdminStudentListItem>)
    vi.mocked(api.adminGetStudent).mockResolvedValue({ ...student, completed_lessons: 0, tracked_lessons: 0, purchases: [], entitlements: [], certificates: [], notes: [], tags: [], lesson_progress: [] } as unknown as api.AdminStudentDetail)
    vi.mocked(api.adminGetAccessCourses).mockResolvedValue([{ id: "course-1", title: "Course", access_days: 30 }])
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

const keyOf = (call: unknown[]) => call[5] as string

async function chooseCourse(scope: HTMLElement) {
    fireEvent.keyDown(within(scope).getByRole("combobox"), { key: "Enter" })
    fireEvent.keyDown(await screen.findByRole("option", { name: "Course" }), { key: "Enter" })
    await waitFor(() => expect(within(scope).getByRole("combobox")).toHaveTextContent("Course"))
}

describe("manual grant from the student card", () => {
    it("keeps the operation key across a retry, renews it after success and submits once at a time", async () => {
        const first = deferred<api.GrantAccessResponse>()
        vi.mocked(api.adminGrantAccess)
            .mockImplementationOnce(() => first.promise)
            .mockResolvedValueOnce({ message: "ok", entitlement_id: "ent-1", expires_at: "2026-12-01T00:00:00" } as api.GrantAccessResponse)
            .mockResolvedValueOnce({ message: "ok", entitlement_id: "ent-2", expires_at: "2027-01-01T00:00:00" } as api.GrantAccessResponse)
        renderUsers()
        fireEvent.click(await screen.findByRole("button", { name: /student@example.test/ }))
        const dialog = await screen.findByRole("dialog")
        await chooseCourse(dialog)
        fireEvent.change(within(dialog).getByPlaceholderText(/причина/i), { target: { value: "Gift from the author" } })
        const submit = within(dialog).getByRole("button", { name: "Выдать доступ" })

        fireEvent.click(submit)
        fireEvent.click(submit)
        expect(api.adminGrantAccess).toHaveBeenCalledTimes(1)
        first.reject(new api.ApiError(503, "Service unavailable", "HTTP 503"))
        await waitFor(() => expect(submit).toBeEnabled())

        fireEvent.click(submit)
        await waitFor(() => expect(api.adminGrantAccess).toHaveBeenCalledTimes(2))
        const calls = vi.mocked(api.adminGrantAccess).mock.calls
        expect(keyOf(calls[0])).toMatch(/^[0-9a-f-]{36}$/)
        expect(keyOf(calls[1])).toBe(keyOf(calls[0]))

        fireEvent.change(within(dialog).getByPlaceholderText(/причина/i), { target: { value: "Another gift later" } })
        fireEvent.click(within(dialog).getByRole("button", { name: "Выдать доступ" }))
        await waitFor(() => expect(api.adminGrantAccess).toHaveBeenCalledTimes(3))
        expect(keyOf(vi.mocked(api.adminGrantAccess).mock.calls[2])).not.toBe(keyOf(calls[0]))
    })
})

describe("create student dialog", () => {
    it("sends one operation key per opened dialog and keeps it across a retry", async () => {
        vi.mocked(api.adminCreateStudent)
            .mockRejectedValueOnce(new api.ApiError(503, "Service unavailable", "HTTP 503"))
            .mockResolvedValueOnce({ user_id: "u1", user_created: true, entitlement_id: "e1", expires_at: "2026-12-01T00:00:00" } as api.AdminCreateStudentResponse)
        renderUsers()
        fireEvent.click(await screen.findByRole("button", { name: /Добавить ученика/ }))
        const dialog = await screen.findByRole("dialog")
        fireEvent.change(within(dialog).getByLabelText(/Email/), { target: { value: "new@example.test" } })
        await chooseCourse(dialog)
        fireEvent.change(within(dialog).getByLabelText(/Причина/), { target: { value: "Manual sale by support" } })
        const submit = within(dialog).getByRole("button", { name: /Добавить/ })

        fireEvent.click(submit)
        await waitFor(() => expect(api.adminCreateStudent).toHaveBeenCalledTimes(1))
        await waitFor(() => expect(submit).toBeEnabled())
        fireEvent.click(submit)
        await waitFor(() => expect(api.adminCreateStudent).toHaveBeenCalledTimes(2))

        const [first, retry] = vi.mocked(api.adminCreateStudent).mock.calls.map(([body]) => body.idempotency_key)
        expect(first).toMatch(/^[0-9a-f-]{36}$/)
        expect(retry).toBe(first)
    })
})
