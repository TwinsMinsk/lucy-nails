"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { Cookie } from "lucide-react"

import { Button } from "@/components/ui/button"
import { readConsent, saveConsent } from "@/lib/attribution"


const isPublicPage = (pathname: string) =>
    pathname === "/" ||
    /^\/courses\/[^/]+$/.test(pathname) ||
    pathname === "/privacy" ||
    pathname === "/terms"

export function ConsentBanner() {
    const pathname = usePathname()
    const [ready, setReady] = useState(false)
    const [open, setOpen] = useState(false)

    useEffect(() => {
        setOpen(!readConsent())
        setReady(true)
    }, [])

    if (!ready || !isPublicPage(pathname)) return null

    if (!open) {
        return (
            <button
                type="button"
                className="fixed bottom-3 left-3 z-50 rounded-full border bg-background/95 p-2.5 text-muted-foreground shadow-sm backdrop-blur hover:text-foreground"
                onClick={() => setOpen(true)}
                aria-label="Настройки cookies"
                title="Настройки cookies"
            >
                <Cookie className="h-4 w-4" />
            </button>
        )
    }

    const choose = (analytics: boolean) => {
        saveConsent(analytics)
        setOpen(false)
    }

    return (
        <section className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-3xl rounded-2xl border bg-background/98 p-5 shadow-2xl backdrop-blur" aria-label="Согласие на cookies">
            <div className="flex items-start gap-3">
                <Cookie className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                <div className="min-w-0 flex-1 space-y-3">
                    <div>
                        <h2 className="font-semibold">Настройки аналитики</h2>
                        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                            Необходимые cookies обеспечивают вход и оплату. Аналитика помогает понять путь до покупки; она включается только с вашего согласия и не получает email или платёжные данные.
                        </p>
                        <Link href="/privacy" className="text-xs text-primary hover:underline">Политика конфиденциальности</Link>
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
                        <Button variant="outline" onClick={() => choose(false)}>Только необходимые</Button>
                        <Button onClick={() => choose(true)}>Разрешить аналитику</Button>
                    </div>
                </div>
            </div>
        </section>
    )
}
