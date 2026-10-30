"use client"

import { usePathname } from "next/navigation"
import { useEffect, useRef, useState } from "react"

import { trackPublicEvent, type YandexGoal, type YandexPurchase } from "@/lib/analytics-client"
import { captureCheckoutAttribution, readConsent } from "@/lib/attribution"


const METRIKA_SCRIPT_ID = "lucy-yandex-metrika"
const isTrackedPublicPage = (pathname: string) => pathname === "/" || /^\/courses\/[^/]+$/.test(pathname)
const PUBLIC_PAGE_GOALS: ReadonlySet<YandexGoal> = new Set(["pricing_view", "checkout_open", "checkout"])

function isSafeMetrikaUrl(rawUrl: string) {
    const url = new URL(rawUrl)
    return Array.from(url.searchParams).every(([key, value]) =>
        !/email|phone|token|password|signature|customer|auth/i.test(key)
        && !/@|(?:\+?\d[\s().-]*){10,}/.test(value)
    ) && (!url.hash || /^#(?:about|program|gallery|pricing)$/.test(url.hash))
}

function isSafeMetrikaLocation() {
    return [window.location.href, document.referrer].filter(Boolean).every(isSafeMetrikaUrl)
        && (isTrackedPublicPage(window.location.pathname)
            || (window.location.pathname === "/payment-success" && !window.location.search))
}

interface MetrikaCounter {
    destruct: () => void
    hit: (url: string, options?: { referer?: string; title?: string }) => void
    reachGoal: (goal: string, params?: Record<string, unknown>) => void
}

interface MetrikaConstructor {
    new (options: Record<string, unknown>): MetrikaCounter
}

declare global {
    interface Window {
        Ya?: { Metrika2?: MetrikaConstructor }
        __lucyMetrika?: MetrikaCounter
        dataLayer?: unknown[]
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

async function loadMetrikaLibrary(counterId: number): Promise<void> {
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
        // The per-counter build carries the counter's server-side settings
        // (auto goals, Webvisor form rules), like the official snippet.
        script.src = `https://mc.yandex.ru/metrika/tag.js?id=${counterId}`
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
        await loadMetrikaLibrary(counterId)
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
        clickmap: true,
        trackLinks: true,
        accurateTrackBounce: true,
        ecommerce: "dataLayer",
        // Only public pages reach here; contact fields carry ym-disable-keys.
        webvisor: true,
    })
    return window.__lucyMetrika
}

function reportPurchase(counter: MetrikaCounter, orderId: string | undefined, purchase: YandexPurchase) {
    counter.reachGoal("purchase", { order_price: purchase.amount, currency: purchase.currency })
    window.dataLayer = window.dataLayer || []
    window.dataLayer.push({
        ecommerce: {
            currencyCode: purchase.currency,
            purchase: {
                actionField: { ...(orderId ? { id: orderId } : {}), revenue: purchase.amount },
                products: [{
                    id: purchase.courseId,
                    name: purchase.courseTitle,
                    variant: purchase.tariff,
                    price: purchase.amount,
                    quantity: 1,
                }],
            },
        },
    })
}

export function AnalyticsBootstrap() {
    const pathname = usePathname()
    const trackedPath = useRef<string | null>(null)
    const [analyticsAllowed, setAnalyticsAllowed] = useState(false)
    const tracking = analyticsAllowed && isTrackedPublicPage(pathname)

    useEffect(() => {
        const syncConsent = () => setAnalyticsAllowed(Boolean(readConsent()?.analytics))
        syncConsent()
        window.addEventListener("lucy-consent-updated", syncConsent)
        return () => window.removeEventListener("lucy-consent-updated", syncConsent)
    }, [])

    useEffect(() => {
        const counterId = Number(process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID)
        const handleGoal = (rawEvent: Event) => {
            const event = rawEvent as CustomEvent<{ goal?: YandexGoal; dedupeKey?: string; purchase?: YandexPurchase }>
            const goal = event.detail?.goal
            if (!counterId || !goal || !readConsent()?.analytics) return
            if (PUBLIC_PAGE_GOALS.has(goal) && !isTrackedPublicPage(window.location.pathname)) return
            // A purchase conversion may initialize the counter on the success
            // route only after the component has removed its opaque token.
            if (goal === "purchase" && (window.location.pathname !== "/payment-success" || window.location.search)) return
            if (goal !== "purchase" && !PUBLIC_PAGE_GOALS.has(goal)) return
            void startMetrika(counterId).then((counter) => {
                if (!counter || !readConsent()?.analytics || window.__lucyMetrika !== counter || !isSafeMetrikaLocation()) return
                const dedupeKey = event.detail?.dedupeKey
                const storageKey = goal === "purchase" && dedupeKey && /^[0-9a-f-]{36}$/i.test(dedupeKey)
                    ? `lucy-metrika-purchase:${dedupeKey}` : undefined
                if (storageKey && sessionStorage.getItem(storageKey)) return
                const purchase = goal === "purchase" ? event.detail?.purchase : undefined
                if (purchase) reportPurchase(counter, storageKey ? dedupeKey : undefined, purchase)
                else counter.reachGoal(goal)
                if (storageKey) sessionStorage.setItem(storageKey, "1")
            }).catch(() => undefined)
        }
        window.addEventListener("lucy-metrika-goal", handleGoal)
        return () => window.removeEventListener("lucy-metrika-goal", handleGoal)
    }, [])

    // One counter instance for the whole stay on public pages, so a Webvisor
    // session is not split at every client-side navigation.
    useEffect(() => {
        const counterId = Number(process.env.NEXT_PUBLIC_YANDEX_METRIKA_ID)
        if (!counterId) return
        if (!tracking) {
            stopMetrika(counterId)
            return
        }
        void startMetrika(counterId)
        return () => stopMetrika(counterId)
    }, [tracking])

    useEffect(() => {
        if (!tracking) {
            trackedPath.current = null
            return
        }
        captureCheckoutAttribution()
        if (trackedPath.current === pathname) return
        const previousPath = trackedPath.current
        trackedPath.current = pathname
        // The counter's own init hit covers the first page; later public
        // pages are client-side navigations it does not see on its own.
        const counter = window.__lucyMetrika
        if (previousPath !== null && counter && isSafeMetrikaLocation()) {
            const referer = new URL(previousPath, window.location.origin).href
            counter.hit(window.location.href, { referer, title: document.title })
        }
        const courseId = pathname === "/" ? undefined : pathname.split("/")[2]
        void trackPublicEvent("landing_view", { path: pathname }, courseId)
    }, [tracking, pathname])

    return null
}
