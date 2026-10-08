import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import Home, { generateMetadata } from "@/app/page"
import { getLandingContent } from "@/lib/landing/loader"
import { landingCourse } from "@/lib/landing/course-content"
import { getPublishedCourses, getPublicCourseModules } from "@/lib/api"

vi.mock("@/lib/landing/loader", () => ({ getLandingContent: vi.fn() }))
vi.mock("@/lib/api", () => ({ getPublishedCourses: vi.fn(), getPublicCourseModules: vi.fn() }))
vi.mock("@/components/landing/ProgramSection", () => ({ ProgramSection: () => null }))
vi.mock("@/components/landing/NailsGallery", () => ({ NailsGallery: () => null }))
vi.mock("@/components/landing/PaymentButton", () => ({ PaymentButton: ({ courseId }: { courseId: string | null }) => <button data-course-id={courseId || ""} disabled={!courseId}>Purchase</button> }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it("uses the canonical CMS identity in landing metadata", async () => {
    vi.mocked(getLandingContent).mockResolvedValue({ course: { id: "canonical", title: "Canonical", price_self: 7200, access_days: 45, lessons_count: 2, total_duration: 3600 }, hero: { ...landingCourse, title: "Renamed CMS course", description: "Published CMS description", instructorImageUrl: null }, modules: [], gallery: [] })
    const metadata = await generateMetadata()
    expect(metadata.title).toBe("Renamed CMS course")
    expect(metadata.description).toBe("Published CMS description")
    expect(metadata.openGraph?.title).toBe("Renamed CMS course")
})

it("binds the canonical CMS course to displayed price access and checkout", async () => {
    vi.mocked(getLandingContent).mockResolvedValue({ course: { id: "canonical", title: "Canonical", price_self: 7200, access_days: 45, lessons_count: 2, total_duration: 3600 }, hero: { ...landingCourse, instructorImageUrl: null }, modules: [], gallery: [] })
    vi.mocked(getPublishedCourses).mockResolvedValue({ courses: [{ id: "wrong", price_self: 12300, access_days: 20 }], total: 1 } as never)
    vi.mocked(getPublicCourseModules).mockResolvedValue([])
    render(await Home())
    expect(screen.getByRole("button", { name: "Purchase" })).toHaveAttribute("data-course-id", "canonical")
    expect(screen.getByText(/7\s*200 ₽/)).toBeVisible()
    expect(screen.getByText("Доступ на 45 дней")).toBeVisible()
    expect(getPublishedCourses).not.toHaveBeenCalled()
})

it("does not display fabricated pricing or permit checkout with no publication", async () => {
    vi.mocked(getLandingContent).mockResolvedValue({ course: null, hero: { ...landingCourse, instructorImageUrl: null }, modules: [], gallery: [] })
    vi.mocked(getPublishedCourses).mockResolvedValue({ courses: [], total: 0 })
    render(await Home())
    expect(screen.getByRole("button", { name: "Purchase" })).toBeDisabled()
    expect(screen.queryByText(/5\s*900 ₽/)).not.toBeInTheDocument()
    expect(screen.getByText("Продажи пока недоступны")).toBeVisible()
})
