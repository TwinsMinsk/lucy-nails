"use client"

import Link from "next/link"
import { useCallback, useEffect, useState } from "react"
import { ChevronRight, Loader2, Megaphone, RefreshCcw } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { adminGetAdCampaigns, adsFileUrl, AdCampaignSummary } from "@/lib/api"
import { formatApiDate } from "@/lib/format"
import { errorText } from "@/components/ads/ad-utils"

const CAMPAIGN_STATUS = { draft: "Готовится", active: "Идёт", finished: "Завершена" } as const

export default function AdminAdsPage() {
    const [campaigns, setCampaigns] = useState<AdCampaignSummary[] | null>(null)
    const [failed, setFailed] = useState(false)

    const load = useCallback(async () => {
        setFailed(false)
        try {
            setCampaigns(await adminGetAdCampaigns())
        } catch (error) {
            setFailed(true)
            toast.error("Не удалось загрузить кампании", { description: errorText(error) })
        }
    }, [])

    useEffect(() => { void load() }, [load])

    return (
        <div className="container max-w-5xl space-y-6 px-4 py-8 md:px-6">
            <div>
                <h1 className="flex items-center gap-2 text-3xl font-bold"><Megaphone className="h-7 w-7" />Реклама</h1>
                <p className="mt-1 text-muted-foreground">Ролики, подписи к постам, календарь публикаций и задачи по каждой кампании.</p>
            </div>

            {failed ? (
                <div className="rounded-xl border bg-background p-8 text-center">
                    <p className="text-muted-foreground">Кампании не загрузились.</p>
                    <Button variant="outline" className="mt-4 h-11" onClick={() => void load()}><RefreshCcw />Повторить</Button>
                </div>
            ) : campaigns === null ? (
                <Loader2 className="mx-auto my-16 h-7 w-7 animate-spin" />
            ) : campaigns.length === 0 ? (
                <div className="rounded-xl border bg-background p-8 text-center text-muted-foreground">Кампаний пока нет: они появятся здесь, когда материалы будут загружены.</div>
            ) : (
                <ul className="space-y-4">
                    {campaigns.map((campaign) => (
                        <li key={campaign.id}>
                            <Link href={`/admin/ads/${campaign.id}`} className="group flex gap-4 rounded-xl border bg-background p-3 transition-colors hover:border-primary/40 sm:p-4">
                                <div className="aspect-[9/16] w-20 shrink-0 overflow-hidden rounded-lg bg-muted sm:w-24">
                                    {campaign.cover_url && (
                                        // eslint-disable-next-line @next/next/no-img-element -- signed API link, next/image would proxy and cache it
                                        <img src={adsFileUrl(campaign.cover_url)} alt="" className="h-full w-full object-cover" />
                                    )}
                                </div>
                                <div className="flex min-w-0 flex-1 flex-col gap-2">
                                    <div className="flex items-start gap-2">
                                        <h2 className="flex-1 text-lg font-semibold leading-snug group-hover:underline">{campaign.title}</h2>
                                        <Badge variant={campaign.status === "active" ? "default" : "outline"}>{CAMPAIGN_STATUS[campaign.status]}</Badge>
                                    </div>
                                    {campaign.summary && <p className="line-clamp-2 text-sm text-muted-foreground">{campaign.summary}</p>}
                                    <div className="mt-auto space-y-1.5 text-sm">
                                        <div className="flex justify-between gap-2">
                                            <span>Опубликовано {campaign.materials_published} из {campaign.materials_total}</span>
                                            {campaign.starts_on && <span className="text-muted-foreground">старт {formatApiDate(campaign.starts_on)}</span>}
                                        </div>
                                        <Progress value={campaign.materials_total ? (campaign.materials_published / campaign.materials_total) * 100 : 0} aria-label="Опубликовано роликов" />
                                        {campaign.tasks_total > 0 && <p className="text-muted-foreground">Задачи: {campaign.tasks_done} из {campaign.tasks_total}</p>}
                                    </div>
                                </div>
                                <ChevronRight className="hidden h-5 w-5 self-center text-muted-foreground sm:block" />
                            </Link>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
