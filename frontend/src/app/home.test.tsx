import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import Home, { generateMetadata } from "@/app/page"
import { getLandingContent } from "@/lib/landing/loader"
import { landingCourse } from "@/lib/landing/course-content"
import { getPublishedCourses, getPublicCourseModules } from "@/lib/api"
import { HOME_DESCRIPTION, HOME_TITLE, ORGANIZATION_NAME, SITE_NAME, SOCIAL_IMAGE } from "@/lib/seo"

vi.mock("@/lib/landing/loader", () => ({ getLandingContent: vi.fn() }))
vi.mock("@/lib/api", () => ({ getPublishedCourses: vi.fn(), getPublicCourseModules: vi.fn() }))
vi.mock("@/components/landing/ProgramSection", () => ({ ProgramSection: () => null }))
vi.mock("@/components/landing/NailsGallery", () => ({ NailsGallery: () => null }))
vi.mock("@/components/landing/PaymentButton", () => ({ PaymentButton: ({ courseId }: { courseId: string | null }) => <button data-course-id={courseId || ""} disabled={!courseId}>Purchase</button> }))
afterEach(() => { cleanup(); vi.clearAllMocks() })

it("uses the search snippet for the page and the CMS identity for social cards", async () => {
    vi.mocked(getLandingContent).mockResolvedValue({ course: { id: "canonical", title: "Canonical", price_self: 7200, access_days: 45, lessons_count: 2, total_duration: 3600 }, hero: { ...landingCourse, title: "Renamed CMS course", description: "Published CMS description", instructorImageUrl: null }, modules: [], gallery: [] })
    const metadata = await generateMetadata()
    expect(metadata.title).toBe(HOME_TITLE)
    expect(metadata.description).toBe(HOME_DESCRIPTION)
    expect(metadata.openGraph).toMatchObject({ title: "Renamed CMS course", description: "Published CMS description", siteName: "Lucy Smirnova", locale: "ru_RU", images: [SOCIAL_IMAGE] })
    expect(metadata.twitter).toMatchObject({ title: "Renamed CMS course", description: "Published CMS description", images: [SOCIAL_IMAGE] })
})

it("describes the published course in JSON-LD with its CMS price", async () => {
    vi.mocked(getLandingContent).mockResolvedValue({ course: { id: "canonical", title: "Canonical", price_self: 7200, access_days: 45, lessons_count: 2, total_duration: 3600 }, hero: { ...landingCourse, title: "Renamed </script> course", instructorImageUrl: null }, modules: [], gallery: [] })
    vi.mocked(getPublicCourseModules).mockResolvedValue([])
    const { container } = render(await Home())
    const script = container.querySelector('script[type="application/ld+json"]')
    expect(script?.innerHTML).not.toContain("</script>")
    const course = JSON.parse(script?.textContent ?? "{}")["@graph"].find((item: { "@type": string }) => item["@type"] === "Course")
    expect(course).toMatchObject({ name: "Renamed </script> course", offers: { category: "Paid", price: 7200, priceCurrency: "RUB" }, hasCourseInstance: { courseMode: "Online", courseWorkload: "PT60M" } })
})

it("omits the course from JSON-LD with no publication", async () => {
    vi.mocked(getLandingContent).mockResolvedValue({ course: null, hero: { ...landingCourse, instructorImageUrl: null }, modules: [], gallery: [] })
    const { container } = render(await Home())
    const graph = JSON.parse(container.querySelector('script[type="application/ld+json"]')?.textContent ?? "{}")["@graph"]
    expect(graph.map((item: { "@type": string }) => item["@type"])).toEqual(["Organization", "Person", "WebSite"])
    expect(graph[0].image).toMatch(new RegExp(`${SOCIAL_IMAGE.url}$`))
    expect(graph[0].name).toBe(ORGANIZATION_NAME)
    expect(graph[2]).toMatchObject({ name: SITE_NAME, alternateName: ORGANIZATION_NAME })
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
