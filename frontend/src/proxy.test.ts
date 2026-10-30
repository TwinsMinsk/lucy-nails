import { NextRequest } from "next/server"
import { afterEach, describe, expect, it, vi } from "vitest"

import { proxy } from "./proxy"


function request(url: string, host: string, cookie?: string) {
    const headers = new Headers({ host })
    if (cookie) headers.set("cookie", cookie)
    return new NextRequest(url, { headers })
}

afterEach(() => vi.unstubAllEnvs())

describe("canonical host", () => {
    it("permanently redirects www to the canonical site with path and query", () => {
        vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://lucysmirnova.ru")
        const response = proxy(request("http://internal:8080/courses/abc?utm_source=vk", "www.lucysmirnova.ru"))
        expect(response.status).toBe(301)
        expect(response.headers.get("location")).toBe("https://lucysmirnova.ru/courses/abc?utm_source=vk")
    })

    it("redirects www before the cabinet login check", () => {
        vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://lucysmirnova.ru")
        const response = proxy(request("http://internal:8080/dashboard", "www.lucysmirnova.ru"))
        expect(response.status).toBe(301)
        expect(response.headers.get("location")).toBe("https://lucysmirnova.ru/dashboard")
    })

    it("does not redirect the canonical host or foreign www hosts", () => {
        vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://lucysmirnova.ru")
        expect(proxy(request("http://internal:8080/", "lucysmirnova.ru")).headers.get("location")).toBeNull()
        expect(proxy(request("http://internal:8080/", "www.example.com")).headers.get("location")).toBeNull()
    })

    it("keeps the cabinet login redirect on the canonical host", () => {
        vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://lucysmirnova.ru")
        const response = proxy(request("https://lucysmirnova.ru/dashboard", "lucysmirnova.ru"))
        expect(response.headers.get("location")).toBe("https://lucysmirnova.ru/auth/login?next=%2Fdashboard")
    })
})
