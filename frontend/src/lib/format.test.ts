import { describe, expect, it } from "vitest"

import { parseApiDate } from "@/lib/format"


describe("parseApiDate", () => {
    it("reads naive backend datetimes as UTC", () => {
        expect(parseApiDate("2026-10-25T21:30:00").toISOString()).toBe("2026-10-25T21:30:00.000Z")
        expect(parseApiDate("2026-10-25T21:30:00.123456").toISOString()).toBe("2026-10-25T21:30:00.123Z")
    })

    it("keeps explicit offsets", () => {
        expect(parseApiDate("2026-10-25T21:30:00Z").toISOString()).toBe("2026-10-25T21:30:00.000Z")
        expect(parseApiDate("2026-10-26T00:30:00+03:00").toISOString()).toBe("2026-10-25T21:30:00.000Z")
        expect(parseApiDate("2026-10-25T16:30:00-0500").toISOString()).toBe("2026-10-25T21:30:00.000Z")
    })

    it("shows the Moscow calendar day for a late-evening UTC expiry", () => {
        const expiry = parseApiDate("2026-10-25T22:15:00")
        expect(expiry.toLocaleDateString("ru-RU", { timeZone: "Europe/Moscow" })).toBe("26.10.2026")
    })

    it("leaves date-only values untouched", () => {
        expect(parseApiDate("2026-10-25").toISOString()).toBe("2026-10-25T00:00:00.000Z")
    })
})
