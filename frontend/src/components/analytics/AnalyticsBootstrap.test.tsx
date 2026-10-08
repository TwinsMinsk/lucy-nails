import { act, cleanup, render, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AnalyticsBootstrap } from "./AnalyticsBootstrap"
import { saveConsent } from "@/lib/attribution"

const state = vi.hoisted(() => ({ pathname: "/courses/course-1", track: vi.fn() }))
vi.mock("next/navigation", () => ({ usePathname: () => state.pathname }))
vi.mock("@/lib/analytics-client", () => ({ trackPublicEvent: state.track }))

beforeEach(() => {
    cleanup()
    window.localStorage.clear()
    state.track.mockClear()
    state.pathname = "/courses/course-1"
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "")
})

describe("public acquisition tracking", () => {
    it("records direct course acquisition and repeat page visits", async () => {
        saveConsent(true)
        const view = render(<AnalyticsBootstrap />)
        await waitFor(() => expect(state.track).toHaveBeenCalledWith("landing_view", { path: "/courses/course-1" }, "course-1"))
        state.pathname = "/"
        view.rerender(<AnalyticsBootstrap />)
        state.pathname = "/courses/course-1"
        view.rerender(<AnalyticsBootstrap />)
        await waitFor(() => expect(state.track).toHaveBeenCalledTimes(3))
    })

    it("tracks no public events after analytics opt-out", async () => {
        saveConsent(false)
        render(<AnalyticsBootstrap />)
        expect(state.track).not.toHaveBeenCalled()
        act(() => saveConsent(true))
        await waitFor(() => expect(state.track).toHaveBeenCalledTimes(1))
        act(() => saveConsent(false))
        expect(state.track).toHaveBeenCalledTimes(1)
    })

    it("does not record protected or admin pages", () => {
        saveConsent(true)
        state.pathname = "/admin"
        render(<AnalyticsBootstrap />)
        expect(state.track).not.toHaveBeenCalled()
    })
})

it("does not initialize Metrika on public URLs containing secrets", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/?token=private-value")
    state.pathname = "/"
    const constructor = vi.fn(function () { return { destruct: vi.fn(), reachGoal: vi.fn() } })
    window.Ya = { Metrika2: constructor }
    saveConsent(true)
    render(<AnalyticsBootstrap />)
    await act(async () => { await Promise.resolve() })
    expect(constructor).not.toHaveBeenCalled()
    window.history.replaceState({}, "", "/")
    delete window.Ya
})

it("uses configured counter goals only on safe public or confirmed success routes", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    const reachGoal = vi.fn()
    const counter = { destruct: vi.fn(), reachGoal }
    const constructor = vi.fn(function () { return counter })
    window.Ya = { Metrika2: constructor }
    window.history.replaceState({}, "", "/")
    state.pathname = "/"
    saveConsent(true)
    render(<AnalyticsBootstrap />)
    await waitFor(() => expect(constructor).toHaveBeenCalledWith(expect.objectContaining({ id: 12345 })))
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal: "checkout" } })))
    await waitFor(() => expect(reachGoal).toHaveBeenCalledWith("checkout"))
    window.history.replaceState({}, "", "/payment-success?token=private")
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal: "purchase" } })))
    await act(async () => { await Promise.resolve() })
    expect(reachGoal).toHaveBeenCalledTimes(1)
    window.history.replaceState({}, "", "/payment-success")
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal: "purchase" } })))
    await waitFor(() => expect(reachGoal).toHaveBeenCalledWith("purchase"))
    act(() => saveConsent(false))
    expect(counter.destruct).toHaveBeenCalled()
    delete window.Ya
    window.history.replaceState({}, "", "/")
})

it("deduplicates confirmed purchase goals for the same order", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/payment-success")
    state.pathname = "/payment-success"
    const reachGoal = vi.fn()
    window.Ya = { Metrika2: vi.fn(function () { return { destruct: vi.fn(), reachGoal } }) }
    saveConsent(true)
    render(<AnalyticsBootstrap />)
    const detail = { goal: "purchase", dedupeKey: "50eea2bb-0025-4b26-970d-b2692266490c" }
    act(() => {
        window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail }))
    })
    await waitFor(() => expect(reachGoal).toHaveBeenCalledTimes(1))
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail })))
    await act(async () => { await Promise.resolve() })
    expect(reachGoal).toHaveBeenCalledTimes(1)
    delete window.Ya
    window.history.replaceState({}, "", "/")
})
