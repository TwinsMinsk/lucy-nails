import { act, cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { ConsentBanner } from "@/components/analytics/ConsentBanner"
import { CONSENT_POLICY_VERSION, CONSENT_STORAGE_KEY } from "@/lib/attribution"

vi.mock("next/navigation", () => ({ usePathname: () => "/courses/11111111-1111-4111-8111-111111111111" }))
beforeEach(() => { window.localStorage.clear() })
afterEach(() => { cleanup(); document.body.innerHTML = "" })

const isMarkedOpen = () => document.documentElement.hasAttribute("data-consent-open")

it("marks the document while the banner is open and clears the mark after a choice", async () => {
    render(<ConsentBanner />)
    expect(await screen.findByRole("region", { name: "Согласие на cookies" })).toBeInTheDocument()
    expect(isMarkedOpen()).toBe(true)
    await userEvent.click(screen.getByRole("button", { name: "Только необходимые" }))
    expect(isMarkedOpen()).toBe(false)
    // Reopening the settings marks the document again.
    await userEvent.click(screen.getByRole("button", { name: "Настройки cookies" }))
    expect(isMarkedOpen()).toBe(true)
})

it("closes the banner and clears the mark when consent is given in another tab", async () => {
    render(<ConsentBanner />)
    await screen.findByRole("region", { name: "Согласие на cookies" })
    expect(isMarkedOpen()).toBe(true)
    // The other tab writes the shared storage; this tab only receives the storage event.
    const value = JSON.stringify({ necessary: true, analytics: true, policy_version: CONSENT_POLICY_VERSION, updated_at: new Date().toISOString() })
    window.localStorage.setItem(CONSENT_STORAGE_KEY, value)
    act(() => { window.dispatchEvent(new StorageEvent("storage", { key: CONSENT_STORAGE_KEY, newValue: value })) })
    expect(screen.queryByRole("region", { name: "Согласие на cookies" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Настройки cookies" })).toBeInTheDocument()
    expect(isMarkedOpen()).toBe(false)
})

it("clears the mark when the banner unmounts", async () => {
    const { unmount } = render(<ConsentBanner />)
    await screen.findByRole("region", { name: "Согласие на cookies" })
    unmount()
    expect(isMarkedOpen()).toBe(false)
})

it("lifts the cookie settings button above a buy bar and leaves it low without one", async () => {
    const choose = async () => {
        await userEvent.click(await screen.findByRole("button", { name: "Только необходимые" }))
        return screen.getByRole("button", { name: "Настройки cookies" })
    }
    const bar = document.createElement("div")
    bar.setAttribute("data-mobile-buy-bar", "")
    document.body.append(bar)
    const withBar = render(<ConsentBanner />)
    expect(await choose()).toHaveClass("bottom-24", "lg:bottom-3")
    withBar.unmount()
    bar.remove()
    window.localStorage.clear()
    render(<ConsentBanner />)
    const button = await choose()
    expect(button).toHaveClass("bottom-3")
    expect(button).not.toHaveClass("bottom-24")
})
