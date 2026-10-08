"use client"

import { usePathname } from "next/navigation"
import { useEffect, useRef, useState } from "react"

import { trackPublicEvent } from "@/lib/analytics-client"
import { captureCheckoutAttribution, readConsent } from "@/lib/attribution"


const METRIKA_SCRIPT_ID = "lucy-yandex-metrika"
const isTrackedPublicPage = (pathname: string) => pathname === "/" || /^\/courses\/[^/]+$/.test(pathname)

function isSafeMetrikaLocation() {
    const urls = [window.location.href, document.referrer].filter(Boolean)
    return urls.every((rawUrl) => {
        const url = new URL(rawUrl)
        return Array.from(url.searchParams).every(([key, value]) =>
            !/email|phone|token|password|signature|customer|auth/i.test(key)
            && !/@|(?:\+?\d[\s().-]*){10,}/.test(value)
        ) && (!url.hash || /^#(?:about|program|gallery|pricing)$/.test(url.hash))
    }) && (isTrackedPublicPage(window.location.pathname)
        || (window.location.pathname === "/payment-success" && !window.location.search))
}

interface MetrikaCounter {
    destruct: () => void
    reachGoal: (goal: string) => void
}

interface MetrikaConstructor {
    new (options: Record<string, unknown>): MetrikaCounter
}

declare global {
    interface Window {
        Ya?: { Metrika2?: MetrikaConstructor }
        __lucyMetrika?: MetrikaCounter
    }
}

let startGeneration = 0

function setMetrikaDisabled(counterId: number, disabled: boolean) {
    ;(window as unknown as Record<string, unknown>)[`disableYaCounter${counterId}`] = disabled
}

function clearMetrikaCookies() {
    const labels = window.location.hostname.split(".")
    const registrableDomain = labels.length >= 2 ? `.${labels.slice(-2).join(".")}` : undefined
    for (const name of ["_ym_uid", "_ym_d", "_ym_isad", "_yasc"]) {
        document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`
        if (registrableDomain) {
            document.cookie = `${name}=; Path=/; Domain=${registrableDomain}; Max-Age=0; SameSite=Lax`
        }
    }
}

function stopMetrika(counterId: number) {
    startGeneration += 1
    setMetrikaDisabled(counterId, true)
    window.__lucyMetrika?.destruct()
    delete window.__lucyMetrika
    document.getElementById(METRIKA_SCRIPT_ID)?.remove()
    clearMetrikaCookies()
}

async function loadMetrikaLibrary(): Promise<void> {
    if (window.Ya?.Metrika2) return
    const existing = document.getElementById(METRIKA_SCRIPT_ID) as HTMLScriptElement | null
    if (existing) {
        await new Promise<void>((resolve, reject) => {
            existing.addEventListener("load", () => resolve(), { once: true })
            existing.addEventListener("error", () => reject(new Error("Metrika load failed")), { once: true })
        })
        return
    }
    await new Promise<void>((resolve, reject) => {
        const script = document.createElement("script")
        script.id = METRIKA_SCRIPT_ID
        script.async = true
        script.src = "https://mc.yandex.ru/metrika/tag.js"
        script.addEventListener("load", () => resolve(), { once: true })
        script.addEventListener("error", () => reject(new Error("Metrika load failed")), { once: true })
        document.head.appendChild(script)
    })
}

async function startMetrika(counterId: number): Promise<MetrikaCounter | undefined> {
    if (!isSafeMetrikaLocation()) return undefined
    if (window.__lucyMetrika) return window.__lucyMetrika
    const generation = ++startGeneration
    setMetrikaDisabled(counterId, false)
    try {
        await loadMetrikaLibrary()
    } catch {
        return undefined
    }
    if (
        generation !== startGeneration
        || !readConsent()?.analytics
        || !isSafeMetrikaLocation()
        || !window.Ya?.Metrika2
    ) return undefined
    window.__lucyMetrika = new window.Ya.Metrika2({
        id: counterId,
        clickmap: false,
        trackLinks: false,
        accurateTrackBounce: true,
        ecommerce: "dataLayer",
        webvisor: false,
        sendTitle: false,
    })
    return window.__lucyMetrika
}

export function AnalyticsBootstrap() {
    const pathname = usePathname()
    const trackedPath = useRef<string | null>(null)
    const [analyticsAllowed, setAnalyticsAllowed] = useState(false)

    useEffect(() => {
        const syncConsent = () => setAnalyticsAllowed(Boolean(readConsent()?.analytics))
        syncConsent()
        window.addEventListener("lucy-consent-updated", syncConsent)
        return () => window.removeEventListener("lucy-consent-updated", syncConsent)
    }, [])

    useEffect(() => {
        const counterId = Number(process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID)
        const handleGoal = (rawEvent: Event) => {
            const event = rawEvent as CustomEvent<{ goal?: "checkout" | "purchase"; dedupeKey?: string }>
            const goal = event.detail?.goal
            if (!counterId || !goal || !readConsent()?.analytics) return
            if (goal === "checkout" && !isTrackedPublicPage(window.location.pathname)) return
            // A purchase conversion may initialize the counter on the success
            // route only after the component has removed its opaque token.
            if (goal === "purchase" && (window.location.pathname !== "/payment-success" || window.location.search)) return
            void startMetrika(counterId).then((counter) => {
                if (!counter || !readConsent()?.analytics || window.__lucyMetrika !== counter || !isSafeMetrikaLocation()) return
                const dedupeKey = event.detail?.dedupeKey
                const storageKey = goal === "purchase" && dedupeKey && /^[0-9a-f-]{36}$/i.test(dedupeKey)
                    ? `lucy-metrika-purchase:${dedupeKey}` : undefined
                if (storageKey && sessionStorage.getItem(storageKey)) return
                counter.reachGoal(goal)
                if (storageKey) sessionStorage.setItem(storageKey, "1")
            }).catch(() => undefined)
        }
        window.addEventListener("lucy-metrika-goal", handleGoal)
        return () => window.removeEventListener("lucy-metrika-goal", handleGoal)
    }, [])

    useEffect(() => {
        const counterId = Number(process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID)
        if (!analyticsAllowed || !isTrackedPublicPage(pathname)) {
            trackedPath.current = null
            if (counterId) stopMetrika(counterId)
            return
        }
        captureCheckoutAttribution()
        if (counterId) void startMetrika(counterId)
        if (trackedPath.current !== pathname) {
            trackedPath.current = pathname
            const courseId = pathname === "/" ? undefined : pathname.split("/")[2]
            void trackPublicEvent("landing_view", { path: pathname }, courseId)
        }
        return () => {
            if (counterId) stopMetrika(counterId)
        }
    }, [analyticsAllowed, pathname])

    return null
}
