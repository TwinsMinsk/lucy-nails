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

export function sendYandexGoal(goal: "checkout" | "purchase"): void {
    if (typeof window === "undefined") return
    window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal } }))
}
