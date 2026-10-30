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
        <section className="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-3xl max-h-[60svh] overflow-y-auto rounded-2xl border bg-background/98 p-4 shadow-2xl backdrop-blur sm:p-5" aria-label="Согласие на cookies">
            <div className="flex items-start gap-3">
                <Cookie className="mt-0.5 hidden h-5 w-5 shrink-0 text-primary sm:block" aria-hidden="true" />
                <div className="min-w-0 flex-1 space-y-3">
                    <div>
                        <h2 className="font-semibold">Настройки аналитики</h2>
                        <p className="mt-1 text-sm leading-snug text-muted-foreground sm:leading-relaxed">
                            Необходимые cookies нужны для входа и оплаты. С вашего согласия включим Яндекс Метрику с Вебвизором, чтобы понять путь до покупки: она записывает переходы, клики и прокрутку на открытых страницах — не в кабинете и без email, телефона и платёжных данных.
                        </p>
                        <Link href="/privacy" className="inline-block py-1 text-sm text-primary underline underline-offset-4 hover:no-underline">Политика конфиденциальности</Link>
                    </div>
                    {/* Side by side even on phones: the banner covered half of the first screen */}
                    <div className="grid grid-cols-2 gap-2 sm:flex sm:justify-end">
                        <Button variant="outline" className="h-11 whitespace-normal leading-tight sm:h-9" onClick={() => choose(false)}>Только необходимые</Button>
                        <Button className="h-11 whitespace-normal leading-tight sm:h-9" onClick={() => choose(true)}>Разрешить аналитику</Button>
                    </div>
                </div>
            </div>
        </section>
    )
}
