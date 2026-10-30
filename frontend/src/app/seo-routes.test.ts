import { afterEach, expect, it, vi } from "vitest"
import { GET as robots } from "@/app/robots.txt/route"
import sitemap from "@/app/sitemap"
import { getPublishedCourses } from "@/lib/api"
import { getLandingContent } from "@/lib/landing/loader"
import { LEGAL_UPDATED_AT } from "@/lib/seo"

vi.mock("@/lib/api", () => ({ getPublishedCourses: vi.fn() }))
vi.mock("@/lib/landing/loader", () => ({ getLandingContent: vi.fn() }))
afterEach(() => { vi.clearAllMocks() })

it("tells Yandex to ignore ad tracking parameters and keeps private areas closed", async () => {
    const body = await robots().text()
    expect(body).toMatch(/^Clean-param: utm_source&utm_medium&utm_campaign&utm_content&utm_term&yclid&ysclid&gclid&fbclid$/m)
    expect(body).toContain("Disallow: /courses/*/lessons/*")
    expect(body).toMatch(/^Sitemap: https?:\/\/.+\/sitemap\.xml$/m)
})

it("dates legal pages by their last text change and leaves the landing undated", async () => {
    vi.mocked(getPublishedCourses).mockResolvedValue({ courses: [{ id: "landing" }, { id: "other", created_at: "2026-09-01T10:00:00Z" }], total: 2 } as never)
    vi.mocked(getLandingContent).mockResolvedValue({ course: { id: "landing" } } as never)
    const entries = await sitemap()
    expect(entries.map((entry) => entry.lastModified)).toEqual([undefined, LEGAL_UPDATED_AT.privacy, LEGAL_UPDATED_AT.terms, new Date("2026-09-01T10:00:00Z")])
    expect(entries.at(-1)?.url).toMatch(/\/courses\/other$/)
})
