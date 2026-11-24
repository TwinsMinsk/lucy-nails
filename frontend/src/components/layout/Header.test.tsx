import { act, cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { Header } from "./Header"

const state = vi.hoisted(() => ({
    pathname: "/",
    push: vi.fn(),
    refresh: vi.fn(),
    getMe: vi.fn(),
    logout: vi.fn(),
    toastError: vi.fn(),
}))

vi.mock("next/navigation", () => ({
    usePathname: () => state.pathname,
    useRouter: () => ({ push: state.push, refresh: state.refresh }),
}))
vi.mock("@/lib/api", () => ({ getMe: state.getMe, logout: state.logout }))
vi.mock("sonner", () => ({ toast: { error: state.toastError } }))

const admin = {
    id: "u1",
    email: "lucy@example.com",
    role: "admin" as const,
    created_at: "2026-01-01T00:00:00Z",
    email_verified_at: null,
}

beforeEach(() => {
    state.pathname = "/"
    state.getMe.mockRejectedValue(new Error("401"))
    state.logout.mockResolvedValue(undefined)
})

afterEach(() => {
    cleanup()
    vi.clearAllMocks()
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

    it("keeps the user signed in and explains it when logout fails", async () => {
        state.getMe.mockResolvedValue(admin)
        state.logout.mockRejectedValue(new TypeError("Failed to fetch"))
        render(<Header />)
        const { user, dialog } = await openMenu()
        await screen.findByText("Администратор")

        await user.click(screen.getByRole("button", { name: "Выйти" }))

        await waitFor(() => expect(state.toastError).toHaveBeenCalledTimes(1))
        expect(screen.getByRole("dialog")).toBe(dialog)
        expect(screen.getByText("lucy@example.com")).toBeInTheDocument()
        expect(screen.getByRole("button", { name: "Выйти" })).toBeEnabled()
        expect(state.push).not.toHaveBeenCalled()
    })

    it("signs out and closes the menu when logout succeeds", async () => {
        state.getMe.mockResolvedValue(admin)
        render(<Header />)
        const { user } = await openMenu()
        await screen.findByText("Администратор")

        await user.click(screen.getByRole("button", { name: "Выйти" }))

        await waitFor(() => expect(state.push).toHaveBeenCalledWith("/"))
        await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
        expect(state.toastError).not.toHaveBeenCalled()
    })
})
