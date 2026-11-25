import { act, cleanup, render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { GoalOnView } from "@/components/analytics/GoalOnView"
import { saveConsent } from "@/lib/attribution"

type Callback = (entries: Array<{ isIntersecting: boolean }>) => void
let observerCallback: Callback = () => {}
const disconnect = vi.fn()

class FakeObserver {
    constructor(callback: Callback) { observerCallback = callback }
    observe() {}
    disconnect() { disconnect() }
}

const goals: string[] = []
const listener = (event: Event) => goals.push((event as CustomEvent<{ goal: string }>).detail.goal)

beforeEach(() => {
    goals.length = 0
    window.localStorage.clear()
    vi.stubGlobal("IntersectionObserver", FakeObserver)
    window.addEventListener("lucy-metrika-goal", listener)
    const target = document.createElement("section")
    target.id = "pricing"
    document.body.appendChild(target)
})
afterEach(() => {
    cleanup()
    window.removeEventListener("lucy-metrika-goal", listener)
    document.getElementById("pricing")?.remove()
    vi.unstubAllGlobals()
    disconnect.mockReset()
})

const scroll = (isIntersecting: boolean) => act(() => observerCallback([{ isIntersecting }]))

describe("GoalOnView", () => {
    it("sends the goal when consent is given while the target is still in view", () => {
        render(<GoalOnView targetId="pricing" goal="pricing_view" />)
        scroll(true)
        expect(goals).toEqual([])
        expect(disconnect).not.toHaveBeenCalled()
        act(() => { saveConsent(true) })
        expect(goals).toEqual(["pricing_view"])
    })

    it("waits for the target to come back into view after consent", () => {
        render(<GoalOnView targetId="pricing" goal="pricing_view" />)
        scroll(true)
        scroll(false)
        act(() => { saveConsent(true) })
        expect(goals).toEqual([])
        scroll(true)
        expect(goals).toEqual(["pricing_view"])
    })

    it("fires at most once per page view", () => {
        saveConsent(true)
        render(<GoalOnView targetId="pricing" goal="pricing_view" />)
        scroll(true)
        scroll(false)
        scroll(true)
        act(() => { saveConsent(true) })
        expect(goals).toEqual(["pricing_view"])
        expect(disconnect).toHaveBeenCalled()
    })

    it("does not fire when analytics was declined", () => {
        saveConsent(false)
        render(<GoalOnView targetId="pricing" goal="pricing_view" />)
        scroll(true)
        expect(goals).toEqual([])
    })
})
