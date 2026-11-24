import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { GET as robots } from "@/app/robots.txt/route"
import sitemap from "@/app/sitemap"
import CoursePage, { generateMetadata } from "@/app/(public)/courses/[id]/page"
import { ApiError, getLandingPayload, getPublicCourse, getPublicCourseModules, getPublishedCourses, type LandingPayload } from "@/lib/api"
import { PrimaryCourseUnknownError } from "@/lib/landing/loader"
import { LEGAL_UPDATED_AT, SOCIAL_IMAGE } from "@/lib/seo"

// Only the API is mocked: the routes run against the real landing loader.
vi.mock("@/lib/api", async (importOriginal) => ({
    ApiError: (await importOriginal<typeof import("@/lib/api")>()).ApiError,
    getLandingPayload: vi.fn(),
    getPublishedCourses: vi.fn(),
    getPublicCourse: vi.fn(),
    getPublicCourseModules: vi.fn(),
}))
vi.mock("@/components/course/CoursePaymentCTA", () => ({ CoursePaymentCTA: ({ children }: { children: React.ReactNode }) => children }))
afterEach(() => { cleanup(); vi.resetAllMocks(); vi.unstubAllEnvs() })

const LANDING_ID = "11111111-1111-4111-8111-111111111111"
const OTHER_ID = "22222222-2222-4222-8222-222222222222"
const NOT_FOUND_DIGEST = "NEXT_HTTP_ERROR_FALLBACK;404"
const course = (id: string) => ({ id, title: "Nail Design PRO", description: "Course description", price_self: 5900, price_support: 0, cover_image_url: "https://api.example/cover.png", is_published: true, access_days: 30, lessons_count: 7, total_duration: 3600, created_at: "2026-09-01T10:00:00Z" })
const modules = [{ id: "m1", title: "Фольга", order_index: 0, lessons: [{ id: "l1", title: "Урок", order_index: 0, duration_seconds: 600 }] }]
const params = (id: string) => ({ params: Promise.resolve({ id }) })
const serverError = () => new ApiError(503, "Service unavailable", "HTTP 503")
const landingSells = (id: string | null) => vi.mocked(getLandingPayload).mockResolvedValue({ course_id: id, course: id ? { id, title: "Nail Design PRO", price_self: 5900, access_days: 30, lessons_count: 7, total_duration: 3600 } : null, hero: {}, modules: [], gallery: [] } as unknown as LandingPayload)
const landingDown = () => vi.mocked(getLandingPayload).mockRejectedValue(new Error("Failed to load landing payload: 503"))
const catalogOf = (...ids: string[]) => vi.mocked(getPublishedCourses).mockResolvedValue({ courses: ids.map(course), total: ids.length })
const urls = (entries: { url: string }[]) => entries.map((entry) => entry.url.replace(/^https?:\/\/[^/]+/, ""))

it("tells Yandex to ignore ad tracking parameters and keeps private areas closed", async () => {
    const body = await robots().text()
    expect(body).toMatch(/^Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term&yclid&ysclid&gclid&fbclid$/m)
    expect(body).toContain("Disallow: /courses/*/lessons/*")
    expect(body).toMatch(/^Sitemap: https?:\/\/.+\/sitemap\.xml$/m)
})

describe("sitemap", () => {
    it("dates legal pages by their last text change, leaves the landing undated and lists only other courses", async () => {
        landingSells(LANDING_ID)
        catalogOf(LANDING_ID, OTHER_ID)
        const entries = await sitemap()
        expect(entries.map((entry) => entry.lastModified)).toEqual([undefined, LEGAL_UPDATED_AT.privacy, LEGAL_UPDATED_AT.terms, new Date("2026-09-01T10:00:00Z")])
        expect(urls(entries)).toEqual(["", "/privacy", "/terms", `/courses/${OTHER_ID}`])
    })

    it("keeps the same map when the landing request fails and the only course is the primary one", async () => {
        landingSells(LANDING_ID)
        catalogOf(LANDING_ID)
        const normal = urls(await sitemap())
        landingDown()
        expect(urls(await sitemap())).toEqual(normal)
    })

    it("never publishes a map without the second course when the landing request fails", async () => {
        landingDown()
        catalogOf(LANDING_ID, OTHER_ID)
        // Throwing keeps Next.js serving the last complete sitemap, which lists the second course.
        await expect(sitemap()).rejects.toBeInstanceOf(PrimaryCourseUnknownError)
    })

    it("throws during a full outage at request time", async () => {
        landingDown()
        vi.mocked(getPublishedCourses).mockRejectedValue(new Error("Failed to load courses: 503"))
        await expect(sitemap()).rejects.toThrow("Failed to load courses: 503")
    })

    it("publishes the static routes during the production build, which has no API", async () => {
        vi.stubEnv("NEXT_PHASE", "phase-production-build")
        landingDown()
        vi.mocked(getPublishedCourses).mockRejectedValue(new TypeError("fetch failed"))
        expect(urls(await sitemap())).toEqual(["", "/privacy", "/terms"])
    })
})

describe("course page", () => {
    it("renders a normal course with its programme, and the primary course points its canonical and preview to /", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        vi.mocked(getPublicCourseModules).mockResolvedValue(modules as never)
        landingSells(LANDING_ID)
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

    it("gives another course a self canonical and its own cover", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(OTHER_ID))
        landingSells(LANDING_ID)
        const metadata = await generateMetadata(params(OTHER_ID))
        expect(metadata.alternates?.canonical).toBe(`/courses/${OTHER_ID}`)
        expect(metadata.openGraph?.images).toEqual(["https://api.example/cover.png"])
    })

    it("compares the ids the API returns, not the URL parameter", async () => {
        landingSells(LANDING_ID)
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        expect((await generateMetadata(params(LANDING_ID.toUpperCase()))).alternates?.canonical).toBe("/")
        vi.mocked(getPublicCourse).mockResolvedValue(course(OTHER_ID))
        expect((await generateMetadata(params(OTHER_ID.toUpperCase()))).alternates?.canonical).toBe(`/courses/${OTHER_ID}`)
    })

    it("answers 404 when the course request itself returns 404", async () => {
        vi.mocked(getPublicCourse).mockRejectedValue(new ApiError(404, "Course not found", "HTTP 404"))
        vi.mocked(getPublicCourseModules).mockRejectedValue(new ApiError(404, "Course not found", "HTTP 404"))
        landingSells(LANDING_ID)
        vi.spyOn(console, "error").mockImplementation(() => {})
        await expect(generateMetadata(params(OTHER_ID))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
        await expect(CoursePage(params(OTHER_ID))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
    })

    it("answers 404 for an unknown course even when the primary course lookup fails first", async () => {
        vi.mocked(getPublicCourse).mockImplementation(() => new Promise((_, reject) => setTimeout(() => reject(new ApiError(404, "Course not found", "HTTP 404")), 20)))
        landingDown()
        vi.mocked(getPublishedCourses).mockRejectedValue(new Error("Failed to load courses: 503"))
        await expect(generateMetadata(params(OTHER_ID))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
    })

    it("answers 404 to an id that cannot be a course without any API request", async () => {
        await expect(generateMetadata(params("not-a-uuid"))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
        await expect(CoursePage(params("not-a-uuid"))).rejects.toMatchObject({ digest: NOT_FOUND_DIGEST })
        for (const request of [getPublicCourse, getPublicCourseModules, getLandingPayload, getPublishedCourses]) {
            expect(request).not.toHaveBeenCalled()
        }
    })

    it("still renders the course when only the modules request fails", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        vi.mocked(getPublicCourseModules).mockRejectedValue(serverError())
        landingSells(LANDING_ID)
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
        landingSells(LANDING_ID)
        await expect(generateMetadata(params(LANDING_ID))).rejects.toBe(error)
        await expect(CoursePage(params(LANDING_ID))).rejects.toBe(error)
    })

    it("keeps the canonical / from the catalog when the landing request fails and one course is published", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(LANDING_ID))
        landingDown()
        catalogOf(LANDING_ID)
        const metadata = await generateMetadata(params(LANDING_ID))
        expect(metadata.alternates?.canonical).toBe("/")
        expect(metadata.openGraph?.images).toEqual([SOCIAL_IMAGE])
    })

    it("fails with a server error rather than guess a canonical when the primary course is unknown", async () => {
        vi.mocked(getPublicCourse).mockResolvedValue(course(OTHER_ID))
        landingDown()
        catalogOf(LANDING_ID, OTHER_ID)
        await expect(generateMetadata(params(OTHER_ID))).rejects.toBeInstanceOf(PrimaryCourseUnknownError)
        const outage = new Error("Failed to load courses: 503")
        vi.mocked(getPublishedCourses).mockRejectedValue(outage)
        await expect(generateMetadata(params(OTHER_ID))).rejects.toBe(outage)
    })
})
