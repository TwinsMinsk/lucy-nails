import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiFetch, isAuthError, adminGetAccessCourses, adminGetNotifications, adminGetReportSources, adminReportSourcesCsvUrl, resendVerification } from "@/lib/api"


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
})
