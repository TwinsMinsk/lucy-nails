import { beforeEach, describe, expect, it, vi } from "vitest"
import { getLandingContent } from "@/lib/landing/loader"
import { getLandingPayload, type LandingPayload } from "@/lib/api"

vi.mock("@/lib/api", () => ({ getLandingPayload: vi.fn() }))
const snapshot = { id: "canonical", title: "New course", price_self: 7200, access_days: 45, lessons_count: 2, total_duration: 3600 }
const payload = { course_id: "canonical", course: snapshot, hero: { landing_title: "CMS title", landing_hero_stats: [], landing_benefits: [] }, modules: [], gallery: [] }
beforeEach(() => { vi.mocked(getLandingPayload).mockReset() })

describe("authoritative landing publication", () => {
    it("keeps successful empty modules and gallery empty", async () => {
        vi.mocked(getLandingPayload).mockResolvedValue(payload as unknown as LandingPayload)
        const content = await getLandingContent()
        expect(content.modules).toEqual([])
        expect(content.gallery).toEqual([])
        expect(content.course).toEqual(snapshot)
        expect(content.hero.heroStats).toEqual([])
    })
    it("renders newly named CMS modules in API order without old static modules", async () => {
        vi.mocked(getLandingPayload).mockResolvedValue({ ...payload, modules: [{ id: "new", title: "Renamed technique", order_index: 2, landing_description: "Only CMS text", landing_bullets: [] }] } as unknown as LandingPayload)
        const content = await getLandingContent()
        expect(content.modules).toHaveLength(1)
        expect(content.modules[0]).toMatchObject({ slug: "new", title: "Renamed technique", description: "Only CMS text", bullets: [] })
    })
    it("does not invent a course when publication is absent", async () => {
        vi.mocked(getLandingPayload).mockResolvedValue({ ...payload, course: null, course_id: null, hero: {} } as unknown as LandingPayload)
        const content = await getLandingContent()
        expect(content.course).toBeNull()
        expect(content.modules).toEqual([])
    })
    it("falls back to marketing only after actual API failure, with checkout disabled", async () => {
        vi.mocked(getLandingPayload).mockRejectedValue(new Error("API unavailable"))
        const content = await getLandingContent()
        expect(content.modules.length).toBeGreaterThan(0)
        expect(content.course).toBeNull()
    })
})
