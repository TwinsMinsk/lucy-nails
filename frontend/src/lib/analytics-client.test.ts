import { describe, expect, it, vi } from "vitest"

import { sendYandexGoal } from "@/lib/analytics-client"


describe("Yandex goal bridge", () => {
    it("dispatches a PII-free purchase conversion event", () => {
        const listener = vi.fn()
        window.addEventListener("lucy-metrika-goal", listener)

        sendYandexGoal("purchase")

        expect(listener).toHaveBeenCalledTimes(1)
        const event = listener.mock.calls[0][0] as CustomEvent
        expect(event.detail).toEqual({ goal: "purchase" })
        window.removeEventListener("lucy-metrika-goal", listener)
    })
})
