import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiFetch, isAuthError } from "@/lib/api"


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

    it("shares one token refresh between concurrent 401 responses", async () => {
        let sessionValid = false
        const fetchMock = vi.fn(async (url: string) => {
            if (url.endsWith("/auth/refresh")) {
                // Keep the refresh in flight while the other callers hit 401.
                await new Promise((resolve) => setTimeout(resolve, 10))
                sessionValid = true
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({ access_token: "new", refresh_token: "new", token_type: "bearer" }),
                }
            }
            if (!sessionValid) {
                return { ok: false, status: 401, json: async () => ({ detail: "Not authenticated" }) }
            }
            return { ok: true, status: 200, json: async () => ({ url }) }
        })
        vi.stubGlobal("fetch", fetchMock)
        const refreshCalls = () => fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh")).length

        const results = await Promise.all([
            apiFetch<{ url: string }>("/auth/me"),
            apiFetch<{ url: string }>("/purchases/my"),
            apiFetch<{ url: string }>("/purchases/my/expired"),
            apiFetch<{ url: string }>("/auth/me"),
        ])

        expect(refreshCalls()).toBe(1)
        expect(results.map((result) => new URL(result.url).pathname)).toEqual([
            "/api/auth/me",
            "/api/purchases/my",
            "/api/purchases/my/expired",
            "/api/auth/me",
        ])

        // The shared refresh is released once settled, so a later expiry refreshes again.
        sessionValid = false
        await apiFetch("/auth/me")
        expect(refreshCalls()).toBe(2)
    })

    it("fails every waiting caller with the auth error when the shared refresh is rejected", async () => {
        const fetchMock = vi.fn(async (url: string) => {
            if (url.endsWith("/auth/refresh")) {
                await new Promise((resolve) => setTimeout(resolve, 10))
                return { ok: false, status: 401, json: async () => ({ detail: "Session revoked" }) }
            }
            return { ok: false, status: 401, json: async () => ({ detail: "Not authenticated" }) }
        })
        vi.stubGlobal("fetch", fetchMock)

        const outcomes = await Promise.allSettled([
            apiFetch("/auth/me"),
            apiFetch("/purchases/my"),
            apiFetch("/purchases/my/expired"),
        ])

        expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1)
        for (const outcome of outcomes) {
            expect(outcome.status).toBe("rejected")
            expect(isAuthError((outcome as PromiseRejectedResult).reason)).toBe(true)
        }
    })
})
