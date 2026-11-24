import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiFetch, isAuthError, adminGetAccessCourses, adminGetNotifications, adminGetReportSources, adminReportSourcesCsvUrl, logout, resendVerification } from "@/lib/api"


describe("apiFetch", () => {
    afterEach(() => {
        vi.unstubAllGlobals()
    })

    it("uses permission-safe course lookup and serializes operational filters", async () => {
        const request = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ items: [], total: 0 }) })
        vi.stubGlobal("fetch", request)
        await adminGetAccessCourses()
        await adminGetNotifications({ search: "buyer@test", status: "dead_letter", channel: "email", offset: 200, limit: 50 })
        expect(new URL(request.mock.calls[0][0]).pathname).toBe("/api/admin/access-courses")
        expect(new URL(request.mock.calls[1][0]).searchParams.get("search")).toBe("buyer@test")
        expect(new URL(request.mock.calls[1][0]).searchParams.get("offset")).toBe("200")
    })

    it("sends verification email and report attribution filters through API contracts", async () => {
        const request = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ message: "OK" }) })
        vi.stubGlobal("fetch", request)
        await resendVerification("learner@example.test")
        expect(request.mock.calls[0][1]).toMatchObject({ method: "POST", body: JSON.stringify({ email: "learner@example.test" }) })
        await adminGetReportSources({ source: "search", campaign: "fall", content: "video", basis: "acquisition" })
        const csv = new URL(adminReportSourcesCsvUrl({ campaign: "fall", basis: "acquisition" }))
        expect(csv.searchParams.get("campaign")).toBe("fall")
        expect(csv.searchParams.get("basis")).toBe("acquisition")
        expect(csv.searchParams.get("format")).toBe("csv")
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

    it.each([429, 502, 503])("keeps the session when the refresh answers %i", async (status) => {
        const storage = new Map<string, string>([["access_token", "old"], ["refresh_token", "refresh"]])
        vi.stubGlobal("localStorage", {
            getItem: vi.fn((key: string) => storage.get(key) ?? null),
            removeItem: vi.fn((key: string) => storage.delete(key)),
            setItem: vi.fn((key: string, value: string) => storage.set(key, value)),
        })
        vi.spyOn(console, "error").mockImplementation(() => undefined)
        vi.stubGlobal("fetch", vi.fn(async (url: string) => (
            url.endsWith("/auth/refresh")
                ? { ok: false, status, json: async () => ({ detail: "Bad gateway" }) }
                : { ok: false, status: 401, json: async () => ({ detail: "Not authenticated" }) }
        )))

        const error = await apiFetch("/auth/me").catch((caught) => caught)

        expect(isAuthError(error)).toBe(false)
        expect(error).toBeInstanceOf(ApiError)
        expect(error).toMatchObject({ status })
        expect(storage.get("refresh_token")).toBe("refresh")
    })
})

describe("logout", () => {
    const hasSessionMarker = () => document.cookie.split("; ").includes("auth_session=1")
    const answer = (status: number) => ({ ok: status < 400, status, json: async () => ({ detail: `HTTP ${status}` }) })

    afterEach(() => {
        vi.unstubAllGlobals()
        document.cookie = "auth_session=; Path=/; Max-Age=0"
    })

    it.each([
        ["a network error", () => Promise.reject(new TypeError("Failed to fetch"))],
        ["a 500 answer", async () => answer(500)],
    ])("keeps the session marker and rejects on %s", async (_case, respond) => {
        document.cookie = "auth_session=1; Path=/"
        vi.spyOn(console, "error").mockImplementation(() => undefined)
        vi.stubGlobal("fetch", vi.fn(respond))

        await expect(logout()).rejects.toBeDefined()

        expect(hasSessionMarker()).toBe(true)
    })

    it.each([200, 401, 403])("clears the session marker when the server answers %i", async (status) => {
        document.cookie = "auth_session=1; Path=/"
        vi.spyOn(console, "error").mockImplementation(() => undefined)
        // A single answer: any further request (such as a token refresh) would fail the logout.
        const request = vi.fn()
            .mockResolvedValueOnce(answer(status))
            .mockRejectedValue(new TypeError("Unexpected second request"))
        vi.stubGlobal("fetch", request)

        await expect(logout()).resolves.toBeUndefined()

        expect(hasSessionMarker()).toBe(false)
        expect(request).toHaveBeenCalledTimes(1)
        expect(request.mock.calls.some(([url]) => String(url).endsWith("/auth/refresh"))).toBe(false)
    })
})
