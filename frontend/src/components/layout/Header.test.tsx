import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { Header } from "./Header"

const state = vi.hoisted(() => ({
    pathname: "/",
    push: vi.fn(),
    refresh: vi.fn(),
    getMe: vi.fn(),
    toastError: vi.fn(),
}))

vi.mock("next/navigation", () => ({
    usePathname: () => state.pathname,
    useRouter: () => ({ push: state.push, refresh: state.refresh }),
}))
// The real logout() runs, so its effect on the session marker is part of what is tested.
vi.mock("@/lib/api", async (importOriginal) => ({
    ...(await importOriginal<typeof import("@/lib/api")>()),
    getMe: state.getMe,
}))
vi.mock("sonner", () => ({ toast: { error: state.toastError } }))

const admin = {
    id: "u1",
    email: "lucy@example.com",
    role: "admin" as const,
    created_at: "2026-01-01T00:00:00Z",
    email_verified_at: null,
}

const hasSessionMarker = () => document.cookie.split("; ").includes("auth_session=1")

beforeEach(() => {
    state.pathname = "/"
    state.getMe.mockRejectedValue(new Error("401"))
})

afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    document.cookie = "auth_session=; Path=/; Max-Age=0"
})

async function openMenu() {
    const user = userEvent.setup()
    await user.click(await screen.findByRole("button", { name: "Меню" }))
    return { user, dialog: await screen.findByRole("dialog") }
}

describe("mobile menu", () => {
    it("closes when the page changes, for example on browser Back", async () => {
        const view = render(<Header />)
        await openMenu()

        state.pathname = "/privacy"
        view.rerender(<Header />)

        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    })

    it("closes on a history step that keeps the same page", async () => {
        render(<Header />)
        await openMenu()

        act(() => { window.dispatchEvent(new PopStateEvent("popstate")) })

        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    })

    it("closes when a link in it is tapped", async () => {
        state.pathname = "/privacy"
        render(<Header />)
        const { user, dialog } = await openMenu()

        await user.click(dialog.querySelector('a[href="/auth/login"]')!)

        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    })
})

describe("logout with a temporary network failure", () => {
    beforeEach(() => {
        document.cookie = "auth_session=1; Path=/"
        state.getMe.mockResolvedValue(admin)
        vi.spyOn(console, "error").mockImplementation(() => undefined)
        // The first POST /auth/logout fails at the network level, the retry succeeds.
        vi.stubGlobal("fetch", vi.fn()
            .mockRejectedValueOnce(new TypeError("Failed to fetch"))
            .mockResolvedValue({ ok: true, status: 200, json: async () => ({}) }))
    })

    it("mobile menu: keeps the session and the menu, explains it, and the retry signs out", async () => {
        render(<Header />)
        const { user, dialog } = await openMenu()
        await within(dialog).findByText("Администратор")

        await user.click(within(dialog).getByRole("button", { name: "Выйти" }))

        await waitFor(() => expect(state.toastError).toHaveBeenCalledTimes(1))
        expect(hasSessionMarker()).toBe(true)
        expect(screen.getByRole("dialog")).toBe(dialog)
        expect(within(dialog).getByText("lucy@example.com")).toBeInTheDocument()
        expect(within(dialog).getByRole("button", { name: "Выйти" })).toBeEnabled()
        expect(state.push).not.toHaveBeenCalled()

        await user.click(within(dialog).getByRole("button", { name: "Выйти" }))

        await waitFor(() => expect(state.push).toHaveBeenCalledWith("/"))
        expect(hasSessionMarker()).toBe(false)
        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
        expect(state.toastError).toHaveBeenCalledTimes(1)
    })

    it("desktop dropdown: keeps the session, explains it, and the retry signs out", async () => {
        const user = userEvent.setup()
        render(<Header />)
        const account = await screen.findByRole("button", { name: "L" })

        await user.click(account)
        await user.click(await screen.findByRole("menuitem", { name: "Выйти" }))

        await waitFor(() => expect(state.toastError).toHaveBeenCalledTimes(1))
        expect(hasSessionMarker()).toBe(true)
        expect(state.push).not.toHaveBeenCalled()

        await user.click(screen.getByRole("button", { name: "L" }))
        await user.click(await screen.findByRole("menuitem", { name: "Выйти" }))

        await waitFor(() => expect(state.push).toHaveBeenCalledWith("/"))
        expect(hasSessionMarker()).toBe(false)
        expect(state.toastError).toHaveBeenCalledTimes(1)
    })
})
