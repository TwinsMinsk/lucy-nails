import { beforeEach, describe, expect, it, vi } from "vitest"
import { getLandingContent } from "@/lib/landing/loader"
import { getLandingPayload, type LandingPayload } from "@/lib/api"
import { programModules } from "@/lib/landing/course-content"
import { worksPhotos } from "@/lib/landing/works-photos"

vi.mock("@/lib/api", () => ({ getLandingPayload: vi.fn() }))
const snapshot = { id: "canonical", title: "New course", price_self: 7200, access_days: 45, lessons_count: 2, total_duration: 3600 }
const payload = { course_id: "canonical", course: snapshot, hero: { landing_title: "CMS title", landing_hero_stats: [], landing_benefits: [] }, modules: [], gallery: [] }
beforeEach(() => { vi.mocked(getLandingPayload).mockReset() })

describe("authoritative landing publication", () => {
    it("restores details and carousel photo keys for all known modules with unset CMS fields", async () => {
        const modules = programModules.map((module, index) => ({
            id: `550e8400-e29b-41d4-a716-${String(index).padStart(12, "0")}`,
            title: module.title,
            landing_duration_label: null,
            landing_description: null,
            landing_outcome: null,
            landing_bullets: null,
            landing_mistakes: null,
        }))
        vi.mocked(getLandingPayload).mockResolvedValue({ ...payload, modules } as unknown as LandingPayload)
        const content = await getLandingContent()
        expect(content.modules).toHaveLength(11)
        content.modules.forEach((module, index) => {
            const original = programModules[index]
            expect(module).toEqual({ slug: original.slug, title: original.title, duration: original.duration, description: original.description, outcome: original.outcome, bullets: original.bullets, mistakes: original.mistakes })
            expect(worksPhotos[module.slug].length).toBeGreaterThan(0)
        })
    })
    it("keeps CMS overrides and intentional empty fields for known modules", async () => {
        vi.mocked(getLandingPayload).mockResolvedValue({ ...payload, modules: [{ id: "known", title: programModules[0].title, landing_duration_label: "", landing_description: "Updated description", landing_outcome: "", landing_bullets: [], landing_mistakes: ["CMS mistake"] }] } as unknown as LandingPayload)
        const content = await getLandingContent()
        expect(content.modules[0]).toEqual({ slug: programModules[0].slug, title: programModules[0].title, duration: "", description: "Updated description", outcome: "", bullets: [], mistakes: ["CMS mistake"] })
    })
    it("preserves publication order and deletion while leaving unknown modules without invented content", async () => {
        vi.mocked(getLandingPayload).mockResolvedValue({ ...payload, modules: [{ id: "second", title: programModules[1].title }, { id: "custom", title: "Custom module" }, { id: "first", title: programModules[0].title }] } as unknown as LandingPayload)
        const content = await getLandingContent()
        expect(content.modules.map((module) => module.slug)).toEqual([programModules[1].slug, "custom", programModules[0].slug])
        expect(content.modules[1]).toEqual({ slug: "custom", title: "Custom module", duration: "", description: "", outcome: "", bullets: [], mistakes: [] })
        expect(content.modules[0].description).toBe(programModules[1].description)
    })
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
