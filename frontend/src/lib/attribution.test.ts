import { beforeEach, describe, expect, it } from "vitest"

import {
    CONSENT_STORAGE_KEY,
    captureCheckoutAttribution,
    saveConsent,
} from "@/lib/attribution"


describe("checkout attribution", () => {
    beforeEach(() => {
        window.localStorage.clear()
        saveConsent(false)
    })

    it("does not persist identifiers or UTM without analytics consent", () => {
        const attribution = captureCheckoutAttribution("?utm_source=instagram&utm_campaign=launch")
        expect(attribution).toBeUndefined()
        expect(window.localStorage.getItem("lucy_attribution_first")).toBeNull()
    })

    it("keeps first touch and refreshes last touch after consent", () => {
        saveConsent(true)
        const first = captureCheckoutAttribution("?utm_source=instagram&utm_campaign=launch")
        const last = captureCheckoutAttribution("?utm_source=telegram&utm_campaign=reminder")

        expect(first?.first_touch).toMatchObject({
            utm_source: "instagram",
            utm_campaign: "launch",
        })
        expect(last?.first_touch).toMatchObject({ utm_source: "instagram" })
        expect(last?.last_touch).toMatchObject({
            utm_source: "telegram",
            utm_campaign: "reminder",
        })
        expect(last?.anonymous_id).toBeTruthy()
        expect(window.localStorage.getItem(CONSENT_STORAGE_KEY)).toContain('"analytics":true')
    })

    it("withdrawal removes analytics identifiers and attribution", () => {
        saveConsent(true)
        captureCheckoutAttribution("?utm_source=instagram")
        saveConsent(false)

        expect(window.localStorage.getItem("lucy_attribution_first")).toBeNull()
        expect(window.localStorage.getItem("lucy_attribution_last")).toBeNull()
        expect(window.localStorage.getItem("lucy_analytics_anonymous_id")).toBeNull()
    })
})
