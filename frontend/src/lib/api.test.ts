import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiFetch } from "@/lib/api"


describe("apiFetch", () => {
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it("preserves structured API errors for MFA and other workflows", async () => {
        vi.spyOn(console, "error").mockImplementation(() => undefined)
        vi.stubGlobal("localStorage", {
            getItem: vi.fn().mockReturnValue(null),
            removeItem: vi.fn(),
            setItem: vi.fn(),
        })
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: vi.fn().mockResolvedValue({
                detail: { code: "mfa_setup_required", setup_token: "setup-token" },
            }),
        }))

        const error = await apiFetch("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email: "owner@example.com", password: "secret" }),
        }).catch((caught) => caught)

        expect(error).toBeInstanceOf(ApiError)
        expect(error).toMatchObject({
            status: 403,
            detail: { code: "mfa_setup_required", setup_token: "setup-token" },
        })
    })
})
