const HAS_TIMEZONE = /(?:Z|[+-]\d{2}:?\d{2})$/i

/**
 * The backend serialises naive UTC datetimes ("2026-09-25T21:30:00"), which
 * `new Date()` would read as local time and shift the date for Moscow users.
 * Treat datetimes without an explicit offset as UTC.
 */
export function parseApiDate(value: string): Date {
    const isDateTime = value.includes("T")
    return new Date(isDateTime && !HAS_TIMEZONE.test(value) ? `${value}Z` : value)
}

/** "1 день", "3 дня", "30 дней". */
export function formatDays(days: number): string {
    const mod10 = days % 10
    const mod100 = days % 100
    const word = mod10 === 1 && mod100 !== 11
        ? "день"
        : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
            ? "дня"
            : "дней"
    return `${days} ${word}`
}

// Durations round to whole minutes first, so 59:40 is "1 ч", never "60 мин" or "1 ч 0 мин".
const toMinutes = (seconds: number) => Math.max(1, Math.round(seconds / 60))

/** Lesson length like "20 мин", "1 ч" or "1 ч 5 мин"; undefined when unknown. */
export function formatLessonDuration(seconds?: number | null): string | undefined {
    if (!seconds || seconds <= 0) return undefined
    const minutes = toMinutes(seconds)
    if (minutes < 60) return `${minutes} мин`
    const hours = Math.floor(minutes / 60)
    const rest = minutes % 60
    return rest ? `${hours} ч ${rest} мин` : `${hours} ч`
}

/** Approximate course length like "≈ 40 мин" or "≈ 5 ч"; null when unknown. */
export function formatCourseDuration(seconds?: number | null): string | null {
    if (!seconds || seconds <= 0) return null
    const minutes = toMinutes(seconds)
    return minutes < 60 ? `≈ ${minutes} мин` : `≈ ${Math.round(minutes / 60)} ч`
}
