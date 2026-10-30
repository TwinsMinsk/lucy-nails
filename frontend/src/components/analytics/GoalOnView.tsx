"use client"

import { useEffect } from "react"

import { sendYandexGoal, type YandexGoal } from "@/lib/analytics-client"


/** Sends a Metrika goal once per page view when the target section is on screen. */
export function GoalOnView({ targetId, goal }: { targetId: string; goal: YandexGoal }) {
    useEffect(() => {
        const target = document.getElementById(targetId)
        if (!target || typeof IntersectionObserver === "undefined") return
        const observer = new IntersectionObserver((entries) => {
            if (!entries.some((entry) => entry.isIntersecting)) return
            sendYandexGoal(goal)
            observer.disconnect()
        }, { threshold: 0.4 })
        observer.observe(target)
        return () => observer.disconnect()
    }, [goal, targetId])

    return null
}
