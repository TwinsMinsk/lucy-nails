export const CONSENT_STORAGE_KEY = "lucy_consent_v1"
export const CONSENT_POLICY_VERSION = "2026-08-26"

const FIRST_TOUCH_KEY = "lucy_attribution_first"
const LAST_TOUCH_KEY = "lucy_attribution_last"
const ANONYMOUS_ID_KEY = "lucy_analytics_anonymous_id"

const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"] as const

export type AttributionTouch = Partial<Record<(typeof UTM_KEYS)[number], string>>

export interface CheckoutAttribution {
    anonymous_id: string
    first_touch?: AttributionTouch
    last_touch?: AttributionTouch
}

export interface ConsentState {
    necessary: true
    analytics: boolean
    policy_version: string
    updated_at: string
}

const isBrowser = () => typeof window !== "undefined" && typeof window.localStorage !== "undefined"

export function readConsent(): ConsentState | null {
    if (!isBrowser()) return null
    try {
        const parsed = JSON.parse(window.localStorage.getItem(CONSENT_STORAGE_KEY) || "null") as ConsentState | null
        if (!parsed || parsed.policy_version !== CONSENT_POLICY_VERSION) return null
        return parsed
    } catch {
        return null
    }
}

export function saveConsent(analytics: boolean): ConsentState | null {
    if (!isBrowser()) return null
    const consent: ConsentState = {
        necessary: true,
        analytics,
        policy_version: CONSENT_POLICY_VERSION,
        updated_at: new Date().toISOString(),
    }
    window.localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consent))
    if (!analytics) {
        window.localStorage.removeItem(FIRST_TOUCH_KEY)
        window.localStorage.removeItem(LAST_TOUCH_KEY)
        window.localStorage.removeItem(ANONYMOUS_ID_KEY)
    }
    window.dispatchEvent(new CustomEvent("lucy-consent-updated", { detail: consent }))
    return consent
}

function parseTouch(search: string): AttributionTouch | undefined {
    const params = new URLSearchParams(search)
    const touch: AttributionTouch = {}
    UTM_KEYS.forEach((key) => {
        const value = params.get(key)?.trim().slice(0, 255)
        if (value) touch[key] = value
    })
    return Object.keys(touch).length ? touch : undefined
}

function readTouch(key: string): AttributionTouch | undefined {
    try {
        return JSON.parse(window.localStorage.getItem(key) || "null") || undefined
    } catch {
        return undefined
    }
}

function anonymousId(): string {
    const existing = window.localStorage.getItem(ANONYMOUS_ID_KEY)
    if (existing) return existing
    const value = typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    window.localStorage.setItem(ANONYMOUS_ID_KEY, value)
    return value
}

export function captureCheckoutAttribution(search?: string): CheckoutAttribution | undefined {
    if (!isBrowser() || !readConsent()?.analytics) return undefined
    const current = parseTouch(search ?? window.location.search)
    let firstTouch = readTouch(FIRST_TOUCH_KEY)
    let lastTouch = readTouch(LAST_TOUCH_KEY)
    if (current) {
        if (!firstTouch) {
            firstTouch = current
            window.localStorage.setItem(FIRST_TOUCH_KEY, JSON.stringify(firstTouch))
        }
        lastTouch = current
        window.localStorage.setItem(LAST_TOUCH_KEY, JSON.stringify(lastTouch))
    }
    return {
        anonymous_id: anonymousId(),
        first_touch: firstTouch,
        last_touch: lastTouch,
    }
}
