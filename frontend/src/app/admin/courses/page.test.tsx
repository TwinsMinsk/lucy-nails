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

    it("are left out of an editor's save, so a price changed meanwhile cannot block it", async () => {
        const course = {
            id: "course-1", title: "Course", description: "Old text", cover_image_url: null,
            price_self: 5900, price_support: 11900, is_published: true, access_days: 30,
            created_at: "2026-11-01T00:00:00", modules_count: 0, lessons_count: 0,
        }
        vi.mocked(api.adminGetCourses).mockResolvedValue([course] as unknown as api.AdminCourseFullResponse[])
        vi.mocked(api.adminUpdateCourse).mockResolvedValue(course as unknown as api.AdminCourseFullResponse)
        render(
            <AdminPermissionsContext.Provider value={["content.manage"]}>
                <AdminCoursesPage />
            </AdminPermissionsContext.Provider>,
        )
        fireEvent.click(await screen.findByTitle("Редактировать"))
        fireEvent.change(document.getElementById("description")!, { target: { value: "New text" } })
        fireEvent.click(screen.getByRole("button", { name: "Сохранить" }))

        await waitFor(() => expect(api.adminUpdateCourse).toHaveBeenCalled())
        const payload = vi.mocked(api.adminUpdateCourse).mock.calls[0][1]
        expect(payload.description).toBe("New text")
        expect(payload).not.toHaveProperty("price_self")
        expect(payload).not.toHaveProperty("price_support")
        expect(payload).not.toHaveProperty("access_days")
    })

    it("are sent by a user with the pricing permission", async () => {
        await openCreateDialog(["content.manage", "commerce.manage_pricing"])
        vi.mocked(api.adminCreateCourse).mockResolvedValue({} as api.AdminCourseFullResponse)
        fireEvent.change(document.getElementById("title")!, { target: { value: "Priced" } })
        fireEvent.click(screen.getByRole("button", { name: "Создать" }))

        await waitFor(() => expect(api.adminCreateCourse).toHaveBeenCalled())
        expect(vi.mocked(api.adminCreateCourse).mock.calls[0][0]).toMatchObject({
            price_self: 5900, price_support: 11900, access_days: 30,
        })
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
