"use client"

import { useState } from "react"
import { Minus, Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog"

const SIZES = [24, 30, 36, 44]

/** Full-screen voice-over text for reading while recording on the phone. */
export function Teleprompter({
    open,
    onOpenChange,
    title,
    lines,
}: {
    open: boolean
    onOpenChange: (open: boolean) => void
    title: string
    lines: string[]
}) {
    const [size, setSize] = useState(1)
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="flex h-[100dvh] max-h-none w-screen max-w-none flex-col gap-0 rounded-none border-0 p-0 sm:max-w-none">
                <div className="flex items-center justify-between gap-3 border-b px-4 py-3 pr-12">
                    <div className="min-w-0">
                        <DialogTitle className="truncate text-base">{title}</DialogTitle>
                        <DialogDescription className="text-xs">Читайте спокойно, паузы между фразами вырежем при монтаже.</DialogDescription>
                    </div>
                    <div className="flex shrink-0 gap-1">
                        <Button variant="outline" size="icon-lg" aria-label="Мельче" disabled={size === 0} onClick={() => setSize(size - 1)}><Minus /></Button>
                        <Button variant="outline" size="icon-lg" aria-label="Крупнее" disabled={size === SIZES.length - 1} onClick={() => setSize(size + 1)}><Plus /></Button>
                    </div>
                </div>
                <ol className="mx-auto w-full max-w-3xl flex-1 space-y-[1.2em] overflow-y-auto px-5 py-8 leading-snug" style={{ fontSize: SIZES[size] }}>
                    {lines.map((line, index) => (
                        <li key={index} className="flex gap-4">
                            <span className="w-6 shrink-0 pt-[0.35em] text-right text-sm text-muted-foreground tabular-nums">{index + 1}</span>
                            <span>{line}</span>
                        </li>
                    ))}
                </ol>
            </DialogContent>
        </Dialog>
    )
}
