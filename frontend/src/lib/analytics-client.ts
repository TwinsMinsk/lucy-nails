import { postAnalyticsEvent } from "@/lib/api"
import { captureCheckoutAttribution } from "@/lib/attribution"


export async function trackPublicEvent(
    eventName: "landing_view" | "cta_click",
    properties: Record<string, string | number | boolean | null> = {},
    courseId?: string,
): Promise<void> {
    const attribution = captureCheckoutAttribution()
    if (!attribution) return
    const touch = attribution.first_touch ?? attribution.last_touch ?? {}
    try {
        await postAnalyticsEvent({
            event_id: crypto.randomUUID(),
            event_name: eventName,
            source: "web",
            anonymous_id: attribution.anonymous_id,
            course_id: courseId && courseId !== "default" ? courseId : undefined,
            ...touch,
            properties,
        })
    } catch {
        // Analytics must never interrupt checkout or public navigation.
    }
}

// Funnel order: pricing seen -> buy clicked -> sent to the payment form -> paid.
export type YandexGoal = "pricing_view" | "checkout_open" | "checkout" | "purchase"

/** Order snapshot for purchase revenue; carries no customer data. */
export interface YandexPurchase {
    amount: number
    currency: string
    courseId: string
    courseTitle: string
    tariff: string
}

export function sendYandexGoal(goal: YandexGoal, dedupeKey?: string, purchase?: YandexPurchase): void {
    if (typeof window === "undefined") return
    window.dispatchEvent(new CustomEvent("lucy-metrika-goal", {
        detail: { goal, ...(dedupeKey ? { dedupeKey } : {}), ...(purchase ? { purchase } : {}) },
    }))
}
