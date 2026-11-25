"use client"

import { useEffect } from "react"

import { sendYandexGoal, type YandexGoal } from "@/lib/analytics-client"
import { readConsent } from "@/lib/attribution"


/**
 * Sends a Metrika goal once per page view when the target section is on screen.
 *
 * Without analytics consent the goal would be dropped, so the observer keeps
 * watching; if the visitor accepts cookies while the section is still in view,
 * the goal is sent then.
 */
export function GoalOnView({ targetId, goal }: { targetId: string; goal: YandexGoal }) {
    useEffect(() => {
        const target = document.getElementById(targetId)
        if (!target || typeof IntersectionObserver === "undefined") return
        let inView = false
        let sent = false
        const observer = new IntersectionObserver((entries) => {
            inView = entries.some((entry) => entry.isIntersecting)
            trySend()
        }, { threshold: 0.4 })
        const trySend = () => {
            if (sent || !inView || !readConsent()?.analytics) return
            sent = true
            sendYandexGoal(goal)
            observer.disconnect()
            window.removeEventListener("lucy-consent-updated", trySend)
        }
        observer.observe(target)
        window.addEventListener("lucy-consent-updated", trySend)
        return () => {
            observer.disconnect()
            window.removeEventListener("lucy-consent-updated", trySend)
        }
    }, [goal, targetId])

    return null
}
