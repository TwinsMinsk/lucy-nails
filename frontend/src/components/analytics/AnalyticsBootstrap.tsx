"use client"

import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"

import { trackPublicEvent } from "@/lib/analytics-client"
import { captureCheckoutAttribution, readConsent } from "@/lib/attribution"


const METRIKA_SCRIPT_ID = "lucy-yandex-metrika"
const isTrackedPublicPage = (pathname: string) => pathname === "/" || /^\/courses\/[^/]+$/.test(pathname)

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
        || !window.Ya?.Metrika2
    ) return undefined
    window.__lucyMetrika = new window.Ya.Metrika2({
        id: counterId,
        clickmap: true,
        trackLinks: true,
        accurateTrackBounce: true,
        ecommerce: "dataLayer",
        webvisor: false,
        sendTitle: false,
    })
    return window.__lucyMetrika
}

export function AnalyticsBootstrap() {
    const pathname = usePathname()
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
            const event = rawEvent as CustomEvent<{ goal?: "checkout" | "purchase" }>
            const goal = event.detail?.goal
            if (!counterId || !goal || !readConsent()?.analytics) return
            // A purchase conversion may initialize the counter on the success
            // route only after the component has removed its opaque token.
            if (goal === "purchase" && (window.location.pathname !== "/payment-success" || window.location.search)) return
            void startMetrika(counterId).then((counter) => counter?.reachGoal(goal))
        }
        window.addEventListener("lucy-metrika-goal", handleGoal)
        return () => window.removeEventListener("lucy-metrika-goal", handleGoal)
    }, [])

    useEffect(() => {
        const counterId = Number(process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID)
        if (!analyticsAllowed || !isTrackedPublicPage(pathname)) {
            if (counterId) stopMetrika(counterId)
            return
        }
        captureCheckoutAttribution()
        if (counterId) void startMetrika(counterId)
        const key = `lucy-page-event:${pathname}`
        if (pathname === "/" && !sessionStorage.getItem(key)) {
            sessionStorage.setItem(key, "1")
            void trackPublicEvent("landing_view", { path: pathname })
        }
        return () => {
            if (counterId) stopMetrika(counterId)
        }
    }, [analyticsAllowed, pathname])

    return null
}
