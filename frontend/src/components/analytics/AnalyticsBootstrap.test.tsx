import { act, cleanup, render, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AnalyticsBootstrap } from "./AnalyticsBootstrap"
import { saveConsent } from "@/lib/attribution"

const state = vi.hoisted(() => ({ pathname: "/courses/course-1", track: vi.fn() }))
vi.mock("next/navigation", () => ({ usePathname: () => state.pathname }))
vi.mock("@/lib/analytics-client", () => ({ trackPublicEvent: state.track }))

beforeEach(() => {
    cleanup()
    // A purchase test starts the counter outside the tracked pages; a real
    // page load would not carry it over.
    delete window.__lucyMetrika
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
    const constructor = vi.fn(function () { return { destruct: vi.fn(), hit: vi.fn(), reachGoal: vi.fn() } })
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
    const counter = { destruct: vi.fn(), hit: vi.fn(), reachGoal }
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
    window.Ya = { Metrika2: vi.fn(function () { return { destruct: vi.fn(), hit: vi.fn(), reachGoal } }) }
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

it("keeps one counter across public navigations and reports each page as a hit", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/")
    state.pathname = "/"
    const counter = { destruct: vi.fn(), hit: vi.fn(), reachGoal: vi.fn() }
    const constructor = vi.fn(function () { return counter })
    window.Ya = { Metrika2: constructor }
    saveConsent(true)
    const view = render(<AnalyticsBootstrap />)
    await waitFor(() => expect(constructor).toHaveBeenCalledWith(expect.objectContaining({ id: 12345, webvisor: true, clickmap: true, trackLinks: true })))
    window.history.replaceState({}, "", "/courses/course-1")
    state.pathname = "/courses/course-1"
    view.rerender(<AnalyticsBootstrap />)
    expect(counter.hit).toHaveBeenCalledWith(
        `${window.location.origin}/courses/course-1`,
        expect.objectContaining({ referer: `${window.location.origin}/` }),
    )
    expect(constructor).toHaveBeenCalledTimes(1)
    expect(counter.destruct).not.toHaveBeenCalled()
    window.history.replaceState({}, "", "/dashboard")
    state.pathname = "/dashboard"
    view.rerender(<AnalyticsBootstrap />)
    expect(counter.destruct).toHaveBeenCalledTimes(1)
    delete window.Ya
    window.history.replaceState({}, "", "/")
})

it("reports purchase revenue as goal params and an e-commerce purchase", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/payment-success")
    state.pathname = "/payment-success"
    const reachGoal = vi.fn()
    window.Ya = { Metrika2: vi.fn(function () { return { destruct: vi.fn(), hit: vi.fn(), reachGoal } }) }
    window.dataLayer = []
    saveConsent(true)
    render(<AnalyticsBootstrap />)
    const purchase = { amount: 5000, currency: "RUB", courseId: "course-1", courseTitle: "Маникюр", tariff: "self" }
    const orderId = "6c1c8e64-8a8e-4f0a-9d6b-1d2f3a4b5c6d"
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal: "purchase", dedupeKey: orderId, purchase } })))
    await waitFor(() => expect(reachGoal).toHaveBeenCalledWith("purchase", { order_price: 5000, currency: "RUB" }))
    expect(window.dataLayer).toEqual([{
        ecommerce: {
            currencyCode: "RUB",
            purchase: {
                actionField: { id: orderId, revenue: 5000 },
                products: [{ id: "course-1", name: "Маникюр", variant: "self", price: 5000, quantity: 1 }],
            },
        },
    }])
    delete window.Ya
    delete window.dataLayer
    window.history.replaceState({}, "", "/")
})

it("uses the order UUID from the checkout reference as the e-commerce id", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/payment-success")
    state.pathname = "/payment-success"
    const reachGoal = vi.fn()
    window.Ya = { Metrika2: vi.fn(function () { return { destruct: vi.fn(), hit: vi.fn(), reachGoal } }) }
    window.dataLayer = []
    window.sessionStorage.clear()
    saveConsent(true)
    render(<AnalyticsBootstrap />)
    const purchase = { amount: 5900, currency: "RUB", courseId: "course-1", courseTitle: "Маникюр", tariff: "self" }
    const detail = { goal: "purchase", dedupeKey: "order|7D9A5B2C-1E3F-4A6B-8C7D-9E0F1A2B3C4D", purchase }
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail })))
    await waitFor(() => expect(reachGoal).toHaveBeenCalledTimes(1))
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail })))
    await act(async () => { await Promise.resolve() })
    expect(reachGoal).toHaveBeenCalledTimes(1)
    expect(window.dataLayer).toHaveLength(1)
    expect(window.dataLayer?.[0]).toMatchObject({
        ecommerce: { purchase: { actionField: { id: "7d9a5b2c-1e3f-4a6b-8c7d-9e0f1a2b3c4d", revenue: 5900 } } },
    })
    delete window.Ya
    delete window.dataLayer
    window.history.replaceState({}, "", "/")
})

it("keeps the visitor's Metrika cookie when a consenting visitor loads a page", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/")
    state.pathname = "/"
    const constructor = vi.fn(function () { return { destruct: vi.fn(), hit: vi.fn(), reachGoal: vi.fn() } })
    window.Ya = { Metrika2: constructor }
    saveConsent(true)
    document.cookie = "_ym_uid=1700000000123456789; Path=/"
    render(<AnalyticsBootstrap />)
    await waitFor(() => expect(constructor).toHaveBeenCalledTimes(1))
    expect(document.cookie).toContain("_ym_uid=1700000000123456789")
    act(() => saveConsent(false))
    expect(document.cookie).not.toContain("_ym_uid")
    delete window.Ya
})

it("accepts funnel goals on public pages but not in the cabinet", async () => {
    vi.stubEnv("NEXT_PUBLIC_YANDEX_METRIKA_ID", "12345")
    window.history.replaceState({}, "", "/")
    state.pathname = "/"
    const reachGoal = vi.fn()
    window.Ya = { Metrika2: vi.fn(function () { return { destruct: vi.fn(), hit: vi.fn(), reachGoal } }) }
    saveConsent(true)
    render(<AnalyticsBootstrap />)
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal: "pricing_view" } })))
    await waitFor(() => expect(reachGoal).toHaveBeenCalledWith("pricing_view"))
    window.history.replaceState({}, "", "/dashboard")
    act(() => window.dispatchEvent(new CustomEvent("lucy-metrika-goal", { detail: { goal: "checkout_open" } })))
    await act(async () => { await Promise.resolve() })
    expect(reachGoal).toHaveBeenCalledTimes(1)
    delete window.Ya
    window.history.replaceState({}, "", "/")
})
