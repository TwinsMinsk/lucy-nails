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
