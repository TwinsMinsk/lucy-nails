import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { GET as robots } from "@/app/robots.txt/route"
import sitemap from "@/app/sitemap"
import CoursePage, { generateMetadata } from "@/app/(public)/courses/[id]/page"
import { ApiError, getPublicCourse, getPublicCourseModules, getPublishedCourses } from "@/lib/api"
import { getLandingCourseId, LandingUnavailableError } from "@/lib/landing/loader"
import { LEGAL_UPDATED_AT, SOCIAL_IMAGE } from "@/lib/seo"

vi.mock("@/lib/api", async (importOriginal) => ({
    ApiError: (await importOriginal<typeof import("@/lib/api")>()).ApiError,
    getPublishedCourses: vi.fn(),
    getPublicCourse: vi.fn(),
    getPublicCourseModules: vi.fn(),
}))
vi.mock("@/lib/landing/loader", async (importOriginal) => ({
    LandingUnavailableError: (await importOriginal<typeof import("@/lib/landing/loader")>()).LandingUnavailableError,
    getLandingCourseId: vi.fn(),
}))
vi.mock("@/components/course/CoursePaymentCTA", () => ({ CoursePaymentCTA: ({ children }: { children: React.ReactNode }) => children }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

const LANDING_ID = "11111111-1111-4111-8111-111111111111"
const OTHER_ID = "22222222-2222-4222-8222-222222222222"
const NOT_FOUND_DIGEST = "NEXT_HTTP_ERROR_FALLBACK;404"
const course = (id: string) => ({ id, title: "Nail Design PRO", description: "Course description", price_self: 5900, price_support: 0, cover_image_url: "https://api.example/cover.png", is_published: true, access_days: 30, lessons_count: 7, total_duration: 3600 })
const modules = [{ id: "m1", title: "Фольга", order_index: 0, lessons: [{ id: "l1", title: "Урок", order_index: 0, duration_seconds: 600 }] }]
const params = (id: string) => ({ params: Promise.resolve({ id }) })
const serverError = () => new ApiError(503, "Service unavailable", "HTTP 503")

it("tells Yandex to ignore ad tracking parameters and keeps private areas closed", async () => {
    const body = await robots().text()
    expect(body).toMatch(/^Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term&yclid&ysclid&gclid&fbclid$/m)
    expect(body).toContain("Disallow: /courses/*/lessons/*")
    expect(body).toMatch(/^Sitemap: https?:\/\/.+\/sitemap\.xml$/m)
})

describe("sitemap", () => {
    it("dates legal pages by their last text change and leaves the landing undated", async () => {
        vi.mocked(getPublishedCourses).mockResolvedValue({ courses: [{ id: "landing" }, { id: "other", created_at: "2026-09-01T10:00:00Z" }], total: 2 } as never)
        vi.mocked(getLandingCourseId).mockResolvedValue("landing")
        const entries = await sitemap()
        expect(entries.map((entry) => entry.lastModified)).toEqual([undefined, LEGAL_UPDATED_AT.privacy, LEGAL_UPDATED_AT.terms, new Date("2026-09-01T10:00:00Z")])
        expect(entries.at(-1)?.url).toMatch(/\/courses\/other$/)
    })

    it("never lists the landing course under its own URL while the landing source is down", async () => {
        vi.mocked(getPublishedCourses).mockResolvedValue({ courses: [{ id: LANDING_ID }], total: 1 } as never)
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        const normal = (await sitemap()).map((entry) => entry.url)
        vi.mocked(getLandingCourseId).mockRejectedValue(new LandingUnavailableError())
        const duringOutage = (await sitemap()).map((entry) => entry.url)
        expect(duringOutage).toEqual(normal)
        expect(duringOutage.some((url) => url.includes(LANDING_ID))).toBe(false)
    })
})

describe("course page", () => {
    it("renders a normal course with its programme, and the landing course points its canonical and preview to /", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        vi.mocked(getPublicCourseModules).mockResolvedValue(modules as never)
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        const metadata = await generateMetadata(params(LANDING_ID))
        expect(metadata.title).toBe("Nail Design PRO")
        expect(metadata.alternates?.canonical).toBe("/")
        expect(metadata.robots).toBeUndefined()
        expect(metadata.openGraph?.images).toEqual([SOCIAL_IMAGE])
        expect(metadata.twitter?.images).toEqual([SOCIAL_IMAGE])
        render(await CoursePage(params(LANDING_ID)))
        expect(screen.getByRole("heading", { level: 1, name: "Nail Design PRO" })).toBeInTheDocument()
        expect(screen.getByText(/Модуль 1: Фольга/)).toBeInTheDocument()
        expect(screen.getByText("1 уроков")).toBeInTheDocument()
        const headings = screen.getAllByRole("heading").map((heading) => `${heading.tagName} ${heading.textContent}`)
        expect(headings).toEqual(["H1 Nail Design PRO", "H2 Программа курса", "H3 Модуль 1: Фольга", "H2 Стоимость обучения"])
    })

    it("gives another course a self canonical", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(OTHER_ID))
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        const metadata = await generateMetadata(params(OTHER_ID))
        expect(metadata.alternates?.canonical).toBe(`/courses/${OTHER_ID}`)
        expect(metadata.openGraph?.images).toEqual(["https://api.example/cover.png"])
    })

    it("answers 404 only when the course request itself returns 404", async () => {
        vi.mocked(getPublicCourse).mockRejectedValue(new ApiError(404, "Course not found", "HTTP 404"))
        vi.mocked(getPublicCourseModules).mockRejectedValue(new ApiError(404, "Course not found", "HTTP 404"))
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        await expect(generateMetadata(params(OTHER_ID))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
        await expect(CoursePage(params(OTHER_ID))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
    })

    it("answers 404 to an id that cannot be a course without asking the API", async () => {
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        await expect(CoursePage(params("not-a-uuid"))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
        expect(getPublicCourse).not.toHaveBeenCalled()
    })

    it("still renders the course when only the modules request fails", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        vi.mocked(getPublicCourseModules).mockRejectedValue(serverError())
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        vi.spyOn(console, "error").mockImplementation(() => {})
        expect((await generateMetadata(params(LANDING_ID))).alternates?.canonical).toBe("/")
        render(await CoursePage(params(LANDING_ID)))
        expect(screen.getByRole("heading", { level: 1, name: "Nail Design PRO" })).toBeInTheDocument()
        expect(screen.queryByText(/Модуль 1/)).not.toBeInTheDocument()
        expect(screen.getByText("7 уроков")).toBeInTheDocument()
        expect(screen.getAllByText(/5\s900 ₽/).length).toBeGreaterThan(0)
    })

    it("passes a server error of the course request to the error boundary instead of a 404", async () => {
        const error = serverError()
        vi.mocked(getPublicCourse).mockRejectedValue(error)
        vi.mocked(getPublicCourseModules).mockResolvedValue(modules as never)
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        await expect(generateMetadata(params(LANDING_ID))).rejects.toBe(error)
        await expect(CoursePage(params(LANDING_ID))).rejects.toBe(error)
    })

    it("keeps the landing canonical from the last confirmed id while the landing source is down", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        // getLandingCourseId answers with the last confirmed id during an outage (see loader.test.ts).
        vi.mocked(getLandingCourseId).mockResolvedValue(LANDING_ID)
        expect((await generateMetadata(params(LANDING_ID))).alternates?.canonical).toBe("/")
    })

    it("fails with a server error rather than a self canonical when the landing course is unknown", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        vi.mocked(getLandingCourseId).mockRejectedValue(new LandingUnavailableError())
        await expect(generateMetadata(params(LANDING_ID))).rejects.toBeInstanceOf(LandingUnavailableError)
    })
})
