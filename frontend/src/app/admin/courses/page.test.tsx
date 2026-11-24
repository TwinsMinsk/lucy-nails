import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import AdminCoursesPage from "@/app/admin/courses/page"
import { AdminPermissionsContext } from "@/app/admin/permissions"
import * as api from "@/lib/api"

const toast = vi.hoisted(() => ({ error: vi.fn(), success: vi.fn(), warning: vi.fn() }))
vi.mock("sonner", () => ({ toast }))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetCourses: vi.fn(), adminCreateCourse: vi.fn(), adminUpdateCourse: vi.fn(),
}))

beforeEach(() => { vi.mocked(api.adminGetCourses).mockResolvedValue([]) })
afterEach(() => { cleanup(); vi.clearAllMocks() })

const openCreateDialog = async (permissions: string[]) => {
    render(
        <AdminPermissionsContext.Provider value={permissions}>
            <AdminCoursesPage />
        </AdminPermissionsContext.Provider>,
    )
    await waitFor(() => expect(api.adminGetCourses).toHaveBeenCalled())
    fireEvent.click(screen.getByRole("button", { name: "Добавить курс" }))
    return screen.findByRole("dialog")
}

describe("course commercial terms", () => {
    it("are read-only without the pricing permission", async () => {
        await openCreateDialog(["content.manage"])
        for (const id of ["price_self", "price_support", "access_days"]) {
            expect(document.getElementById(id)).toBeDisabled()
        }
        expect(screen.getByText("Цены и срок доступа меняет владелец или администратор.")).toBeInTheDocument()
    })

    it("are editable with the pricing permission", async () => {
        await openCreateDialog(["content.manage", "commerce.manage_pricing"])
        for (const id of ["price_self", "price_support", "access_days"]) {
            expect(document.getElementById(id)).toBeEnabled()
        }
    })

    it("shows a 403 from the API as a message", async () => {
        vi.mocked(api.adminCreateCourse).mockRejectedValue(
            new api.ApiError(403, "Permission required: commerce.manage_pricing", "Forbidden"),
        )
        await openCreateDialog(["content.manage"])
        fireEvent.change(document.getElementById("title")!, { target: { value: "New course" } })
        fireEvent.click(screen.getByRole("button", { name: "Создать" }))

        await waitFor(() => expect(toast.error).toHaveBeenCalledWith(
            "Недостаточно прав",
            { description: "Цены и срок доступа может менять только владелец или администратор." },
        ))
        expect(screen.getByRole("dialog")).toBeInTheDocument()
    })
})
