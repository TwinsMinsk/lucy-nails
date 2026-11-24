import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import Landing from "@/app/admin/landing/page"
import * as api from "@/lib/api"

vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(),
    adminGetCourses: vi.fn(), adminGetCourseLandingHero: vi.fn(), adminGetCourseLandingModules: vi.fn(),
    adminGetGallery: vi.fn(), adminUpdateCourseLandingHero: vi.fn(),
}))

const courses = [
    { id: "course-a", title: "Course A", is_published: true },
    { id: "course-b", title: "Course B", is_published: true },
] as unknown as api.AdminCourseFullResponse[]

const hero = (title: string): api.LandingHeroPayload => ({
    landing_title: title, landing_subtitle: `${title} subtitle`, landing_description: `${title} description`,
    landing_audience: null, landing_support_note: null, landing_hero_stats: null, landing_benefits: null,
    landing_instructor_image_url: `/uploads/${title}.jpg`,
})

beforeEach(() => {
    vi.mocked(api.adminGetCourses).mockResolvedValue(courses)
    vi.mocked(api.adminGetCourseLandingModules).mockResolvedValue([])
    vi.mocked(api.adminGetGallery).mockResolvedValue([])
    vi.mocked(api.adminUpdateCourseLandingHero).mockImplementation(async (_id, data) => data)
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe("landing hero editor", () => {
    it("blocks saving after a failed load and offers a retry", async () => {
        vi.mocked(api.adminGetCourseLandingHero)
            .mockRejectedValueOnce(new api.ApiError(500, "Internal error", "HTTP 500"))
            .mockResolvedValueOnce(hero("Alpha"))
        render(<Landing />)
        const alert = await screen.findByText(/Не удалось загрузить hero/)
        expect(alert).toBeVisible()
        expect(screen.queryByRole("button", { name: /Сохранить hero/ })).not.toBeInTheDocument()
        expect(screen.queryByLabelText("Заголовок")).not.toBeInTheDocument()
        fireEvent.click(screen.getAllByRole("button", { name: "Повторить загрузку" })[0])
        expect(await screen.findByDisplayValue("Alpha")).toBeVisible()
        expect(api.adminUpdateCourseLandingHero).not.toHaveBeenCalled()
    })

    it("sends only the changed fields", async () => {
        vi.mocked(api.adminGetCourseLandingHero).mockResolvedValue(hero("Alpha"))
        render(<Landing />)
        fireEvent.change(await screen.findByLabelText("Заголовок"), { target: { value: "Alpha 2" } })
        fireEvent.click(screen.getByRole("button", { name: /Сохранить hero/ }))
        await waitFor(() => expect(api.adminUpdateCourseLandingHero).toHaveBeenCalledTimes(1))
        expect(api.adminUpdateCourseLandingHero).toHaveBeenCalledWith("course-a", { landing_title: "Alpha 2" })
    })

    it("ignores a late response for the previously selected course", async () => {
        let resolveA: (value: api.LandingHeroPayload) => void = () => {}
        vi.mocked(api.adminGetCourseLandingHero).mockImplementation((courseId) => (
            courseId === "course-a"
                ? new Promise((resolve) => { resolveA = resolve })
                : Promise.resolve(hero("Bravo"))
        ))
        render(<Landing />)
        await waitFor(() => expect(api.adminGetCourseLandingHero).toHaveBeenCalledWith("course-a"))
        fireEvent.click(screen.getByRole("button", { name: "Course B" }))
        expect(await screen.findByDisplayValue("Bravo")).toBeVisible()
        await act(async () => { resolveA(hero("Alpha")) })
        expect(screen.queryByDisplayValue("Alpha")).not.toBeInTheDocument()
        expect(screen.getByDisplayValue("Bravo")).toBeVisible()
        fireEvent.change(screen.getByLabelText("Подзаголовок"), { target: { value: "Bravo new subtitle" } })
        fireEvent.click(screen.getByRole("button", { name: /Сохранить hero/ }))
        await waitFor(() => expect(api.adminUpdateCourseLandingHero).toHaveBeenCalledWith("course-b", { landing_subtitle: "Bravo new subtitle" }))
    })
})
