import { describe, expect, it } from "vitest"

import { formatCourseDuration, formatDays, formatLessonDuration, parseApiDate } from "@/lib/format"


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

describe("formatDays", () => {
    it("uses the Russian plural forms", () => {
        expect([1, 2, 5, 11, 14, 21, 22, 30, 90, 111, 365].map(formatDays)).toEqual([
            "1 день", "2 дня", "5 дней", "11 дней", "14 дней", "21 день", "22 дня", "30 дней", "90 дней", "111 дней", "365 дней",
        ])
    })
})

describe("duration helpers", () => {
    it("formats lessons without a dangling zero-minute part", () => {
        expect(formatLessonDuration(0)).toBeUndefined()
        expect(formatLessonDuration(20)).toBe("1 мин")
        expect(formatLessonDuration(20 * 60 + 29)).toBe("20 мин")
        expect(formatLessonDuration(3580)).toBe("1 ч")
        expect(formatLessonDuration(3600)).toBe("1 ч")
        expect(formatLessonDuration(3900)).toBe("1 ч 5 мин")
        expect(formatLessonDuration(7200)).toBe("2 ч")
    })

    it("formats course totals as whole hours from 60 minutes", () => {
        expect(formatCourseDuration(null)).toBeNull()
        expect(formatCourseDuration(40 * 60)).toBe("≈ 40 мин")
        expect(formatCourseDuration(3570)).toBe("≈ 1 ч")
        expect(formatCourseDuration(3599)).toBe("≈ 1 ч")
        expect(formatCourseDuration(5 * 3600 - 300)).toBe("≈ 5 ч")
    })
})
