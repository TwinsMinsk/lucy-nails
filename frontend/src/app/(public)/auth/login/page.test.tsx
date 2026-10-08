import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import LoginPage from "./page"
import * as api from "@/lib/api"

const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => router }))
vi.mock("@/lib/api", async (original) => ({
    ...await original<typeof api>(),
    login: vi.fn(), getMe: vi.fn(), resendVerification: vi.fn(),
}))

beforeEach(() => {
    vi.mocked(api.login).mockResolvedValue({ access_token: "access", refresh_token: "refresh", token_type: "bearer" })
    vi.mocked(api.resendVerification).mockResolvedValue({ message: "If verification is needed, a link has been sent" })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

async function submit() {
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "owner@example.com" } })
    fireEvent.change(screen.getByLabelText("Пароль"), { target: { value: "password123" } })
    fireEvent.click(screen.getByRole("button", { name: "Войти" }))
}

describe("mailbox verification login", () => {
    it("explains paid access and enables generic resend for unverified students", async () => {
        vi.mocked(api.getMe).mockResolvedValue({ email_verified_at: null, role: "student" } as api.UserResponse)
        render(<LoginPage />)
        await submit()
        expect(await screen.findByRole("heading", { name: "Подтвердите ваш email" })).toBeVisible()
        expect(router.push).not.toHaveBeenCalled()
        fireEvent.click(screen.getByRole("button", { name: "Отправить письмо повторно" }))
        await waitFor(() => expect(api.resendVerification).toHaveBeenCalledWith("owner@example.com"))
    })

    it.each([
        { email_verified_at: "2026-10-08T00:00:00Z", role: "student" },
        { email_verified_at: null, role: "admin" },
    ])("continues login for permitted $role", async (user) => {
        vi.mocked(api.getMe).mockResolvedValue(user as api.UserResponse)
        render(<LoginPage />)
        await submit()
        await waitFor(() => expect(router.push).toHaveBeenCalledWith("/dashboard"))
    })
})
