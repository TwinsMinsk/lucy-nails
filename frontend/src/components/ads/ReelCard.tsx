"use client"

import { Copy, Download, Play } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { adsFileUrl, AdMaterial } from "@/lib/api"
import { copyText, formatSeconds, mainFile, STATUS_SHORT } from "@/components/ads/ad-utils"

export const STATUS_BADGE = {
    draft: "outline",
    ready: "secondary",
    published: "default",
} as const

/** One reel in the campaign list: the two everyday actions are right on the card. */
export function ReelCard({ material, onOpen }: { material: AdMaterial; onOpen: () => void }) {
    const video = mainFile(material, "video")
    const cover = mainFile(material, "cover")
    const duration = formatSeconds(material.duration_seconds)
    return (
        <article className="flex gap-4 rounded-xl border bg-background p-3">
            <button
                type="button"
                onClick={onOpen}
                className="group relative aspect-[9/16] w-28 shrink-0 overflow-hidden rounded-lg bg-muted sm:w-32"
                aria-label={`Открыть ${material.code.toUpperCase()} «${material.title}»`}
            >
                {cover && (
                    // eslint-disable-next-line @next/next/no-img-element -- signed API link, next/image would proxy and cache it
                    <img src={adsFileUrl(cover.url)} alt="" loading="lazy" className="h-full w-full object-cover" />
                )}
                <span className="absolute inset-0 flex items-center justify-center bg-black/10 transition-colors group-hover:bg-black/25">
                    <span className="rounded-full bg-white/90 p-2.5 text-foreground shadow"><Play className="h-4 w-4 fill-current" /></span>
                </span>
            </button>
            <div className="flex min-w-0 flex-1 flex-col">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">{material.code.toUpperCase()}</span>
                    {duration && <span>{duration}</span>}
                    <Badge variant={STATUS_BADGE[material.status]} className="ml-auto">{STATUS_SHORT[material.status]}</Badge>
                </div>
                <button type="button" onClick={onOpen} className="mt-1 text-left text-base font-semibold leading-snug hover:underline">
                    {material.title}
                </button>
                {material.hook && <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{material.hook}</p>}
                <div className="mt-auto flex flex-col gap-2 pt-3">
                    {video ? (
                        <Button asChild className="h-11 w-full">
                            <a href={adsFileUrl(video.download_url)}><Download />Скачать видео</a>
                        </Button>
                    ) : (
                        <Button className="h-11 w-full" disabled>Видео ещё нет</Button>
                    )}
                    <Button
                        variant="outline"
                        className="h-11 w-full"
                        disabled={!material.caption}
                        onClick={() => material.caption && void copyText(material.caption, "Подпись скопирована")}
                    >
                        <Copy />Скопировать подпись
                    </Button>
                </div>
            </div>
        </article>
    )
}
