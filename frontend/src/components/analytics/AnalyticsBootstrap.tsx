"use client"

import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"

import { trackPublicEvent } from "@/lib/analytics-client"
import { captureCheckoutAttribution, readConsent } from "@/lib/attribution"


const METRIKA_SCRIPT_ID = "lucy-yandex-metrika"
const isTrackedPublicPage = (pathname: string) => pathname === "/" || /^\/courses\/[^/]+$/.test(pathname)

function removeMetrika() {
    document.getElementById(METRIKA_SCRIPT_ID)?.remove()
    delete window.ym
    for (const name of ["_ym_uid", "_ym_d", "_ym_isad", "_yasc"]) {
        document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`
    }
}

function startMetrika(counterId: number) {
    if (document.getElementById(METRIKA_SCRIPT_ID)) return
    window.ym = window.ym || function (...args: unknown[]) {
        const queued = (window.ym as unknown as { a?: unknown[] }).a || []
        queued.push(args)
        ;(window.ym as unknown as { a: unknown[] }).a = queued
    }
    window.ym(counterId, "init", {
        clickmap: true,
        trackLinks: true,
        accurateTrackBounce: true,
        ecommerce: "dataLayer",
    })
    const script = document.createElement("script")
    script.id = METRIKA_SCRIPT_ID
    script.async = true
    script.src = "https://mc.yandex.ru/metrika/tag.js"
    document.head.appendChild(script)
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
        if (!analyticsAllowed || !isTrackedPublicPage(pathname)) {
            removeMetrika()
            return
        }
        captureCheckoutAttribution()
        if (counterId) startMetrika(counterId)
        const key = `lucy-page-event:${pathname}`
        if (pathname === "/" && !sessionStorage.getItem(key)) {
            sessionStorage.setItem(key, "1")
            void trackPublicEvent("landing_view", { path: pathname })
        }
    }, [analyticsAllowed, pathname])

    return null
}
