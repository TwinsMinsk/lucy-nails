"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { useCallback, useEffect, useMemo, useState } from "react"
import { ArrowLeft, CalendarDays, Check, Loader2, RefreshCcw } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { adminGetAdCampaign, adminUpdateAdTask, AdCalendarEntry, AdCampaign, AdMaterial, AdTask } from "@/lib/api"
import { formatApiDate } from "@/lib/format"
import { cn } from "@/lib/utils"
import { useAdminPermission } from "@/app/admin/permissions"
import { errorText } from "@/components/ads/ad-utils"
import { InlineText, RichText } from "@/components/ads/AdText"
import { ReelCard } from "@/components/ads/ReelCard"
import { CommentsSection, ReelSheet } from "@/components/ads/ReelSheet"

type Tab = "reels" | "calendar" | "tasks" | "comments" | "about"

const TODAY = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow" }).format(new Date())

function dayLabel(day: string) {
    const date = new Date(`${day}T12:00:00`)
    const weekday = date.toLocaleDateString("ru-RU", { weekday: "short" })
    return `${weekday[0].toUpperCase()}${weekday.slice(1)}, ${date.toLocaleDateString("ru-RU", { day: "numeric", month: "long" })}`
}

export default function AdminAdCampaignPage() {
    const { id } = useParams<{ id: string }>()
    const canManage = useAdminPermission("ads.manage")
    const [campaign, setCampaign] = useState<AdCampaign | null>(null)
    const [failed, setFailed] = useState(false)
    const [tab, setTab] = useState<Tab>("reels")
    const [openId, setOpenId] = useState<string | null>(null)

    const load = useCallback(async () => {
        try {
            setCampaign(await adminGetAdCampaign(id))
            setFailed(false)
        } catch (error) {
            setFailed(true)
            toast.error("Не удалось загрузить кампанию", { description: errorText(error) })
        }
    }, [id])

    useEffect(() => { void load() }, [load])

    const materials = useMemo(() => new Map(campaign?.materials.map((m) => [m.id, m]) ?? []), [campaign])
    const materialTitle = useCallback((materialId: string | null) => {
        const material = materialId ? materials.get(materialId) : undefined
        return material ? `${material.code.toUpperCase()} «${material.title}»` : null
    }, [materials])

    if (failed && !campaign) {
        return (
            <div className="container max-w-5xl px-4 py-16 text-center">
                <p className="text-muted-foreground">Кампания не загрузилась.</p>
                <Button variant="outline" className="mt-4 h-11" onClick={() => void load()}><RefreshCcw />Повторить</Button>
            </div>
        )
    }
    if (!campaign) return <Loader2 className="mx-auto my-24 h-7 w-7 animate-spin" />

    const published = campaign.materials.filter((m) => m.status === "published").length
    const ready = campaign.materials.filter((m) => m.status === "ready").length
    const tasksDone = campaign.tasks.filter((t) => t.done_at).length
    const today = TODAY()
    const next = campaign.calendar.find((entry) => entry.day >= today)
    const tabs: { key: Tab; label: string; hidden?: boolean }[] = [
        { key: "reels", label: `Ролики · ${campaign.materials.length}` },
        { key: "calendar", label: "Календарь", hidden: campaign.calendar.length === 0 },
        { key: "tasks", label: `Задачи · ${tasksDone}/${campaign.tasks.length}`, hidden: campaign.tasks.length === 0 },
        { key: "comments", label: campaign.comments.length ? `Комментарии · ${campaign.comments.length}` : "Комментарии" },
        { key: "about", label: "О кампании", hidden: campaign.about.length === 0 },
    ]

    return (
        <div className="container max-w-5xl space-y-6 px-4 py-6 md:px-6 md:py-8">
            <div className="space-y-3">
                <Link href="/admin/ads" className="inline-flex min-h-11 items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" />Все кампании</Link>
                <h1 className="text-2xl font-bold leading-tight md:text-3xl">{campaign.title}</h1>
                {campaign.summary && <p className="text-muted-foreground">{campaign.summary}</p>}
                <p className="text-sm text-muted-foreground">
                    {campaign.starts_on && <>Старт {formatApiDate(campaign.starts_on)} · </>}
                    Опубликовано {published} из {campaign.materials.length}{ready > 0 && <> · готовы к публикации {ready}</>}
                </p>
                {next && (
                    <button
                        type="button"
                        onClick={() => (next.material_id ? setOpenId(next.material_id) : setTab("calendar"))}
                        className="flex w-full items-start gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4 text-left transition-colors hover:bg-primary/10"
                    >
                        <CalendarDays className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                        <span className="min-w-0">
                            <span className="block text-sm font-medium text-primary">
                                {next.day === today ? "Сегодня" : "Ближайшая публикация"} · {dayLabel(next.day)}{next.time && `, ${next.time}`}
                            </span>
                            <span className="mt-0.5 block"><InlineText text={next.title} /></span>
                        </span>
                    </button>
                )}
            </div>

            <nav className="-mx-4 flex gap-1 overflow-x-auto border-b px-4 md:mx-0 md:px-0" aria-label="Разделы кампании">
                {tabs.filter((t) => !t.hidden).map((t) => (
                    <button
                        key={t.key}
                        type="button"
                        onClick={() => setTab(t.key)}
                        aria-current={tab === t.key ? "page" : undefined}
                        className={cn(
                            "-mb-px min-h-11 shrink-0 border-b-2 px-3 text-sm font-medium whitespace-nowrap transition-colors",
                            tab === t.key ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
                        )}
                    >
                        {t.label}
                    </button>
                ))}
            </nav>

            {tab === "reels" && <ReelsTab campaign={campaign} onOpen={setOpenId} />}
            {tab === "calendar" && <CalendarTab entries={campaign.calendar} today={today} materials={materials} onOpen={setOpenId} />}
            {tab === "tasks" && <TasksTab tasks={campaign.tasks} canManage={canManage} onChanged={load} />}
            {tab === "comments" && (
                <div className="-mx-4 rounded-xl border bg-background md:mx-0 [&>section]:border-t-0">
                    <CommentsSection
                        title="Комментарии к кампании"
                        campaignId={campaign.id}
                        materialId={null}
                        comments={campaign.comments}
                        canManage={canManage}
                        onChanged={load}
                        materialTitle={materialTitle}
                    />
                </div>
            )}
            {tab === "about" && (
                <div className="space-y-4">
                    {campaign.about.map((section) => (
                        <section key={section.title} className="rounded-xl border bg-background p-4 md:p-6">
                            <h2 className="mb-3 text-lg font-semibold">{section.title}</h2>
                            <RichText text={section.body} />
                        </section>
                    ))}
                </div>
            )}

            <ReelSheet
                campaignId={campaign.id}
                material={openId ? materials.get(openId) ?? null : null}
                comments={campaign.comments}
                canManage={canManage}
                onOpenChange={(open) => !open && setOpenId(null)}
                onChanged={load}
            />
        </div>
    )
}

function ReelsTab({ campaign, onOpen }: { campaign: AdCampaign; onOpen: (id: string) => void }) {
    if (campaign.materials.length === 0) {
        return <p className="rounded-xl border bg-background p-8 text-center text-muted-foreground">Роликов пока нет.</p>
    }
    const known = new Set(campaign.groups.map((group) => group.key))
    const sections = [
        ...campaign.groups.map((group) => ({ ...group, items: campaign.materials.filter((m) => m.group_key === group.key) })),
        {
            key: "",
            title: campaign.groups.length ? "Другое" : "",
            note: null,
            items: campaign.materials.filter((m) => !m.group_key || !known.has(m.group_key)),
        },
    ]
    return (
        <div className="space-y-8">
            {sections.filter((section) => section.items.length > 0).map((section) => (
                <section key={section.key || "other"} className="space-y-3">
                    {section.title && (
                        <header>
                            <h2 className="text-lg font-semibold">{section.title}</h2>
                            {section.note && <p className="text-sm text-muted-foreground">{section.note}</p>}
                        </header>
                    )}
                    <div className="grid gap-3 lg:grid-cols-2">
                        {section.items.map((material) => <ReelCard key={material.id} material={material} onOpen={() => onOpen(material.id)} />)}
                    </div>
                </section>
            ))}
        </div>
    )
}

function CalendarTab({
    entries,
    today,
    materials,
    onOpen,
}: {
    entries: AdCalendarEntry[]
    today: string
    materials: Map<string, AdMaterial>
    onOpen: (id: string) => void
}) {
    const weeks = new Map<string, AdCalendarEntry[]>()
    for (const entry of entries) {
        const key = entry.week ? `Неделя ${entry.week}` : "Без недели"
        weeks.set(key, [...(weeks.get(key) ?? []), entry])
    }
    return (
        <div className="space-y-6">
            {[...weeks.entries()].map(([week, items]) => (
                <section key={week} className="space-y-2">
                    <h2 className="text-lg font-semibold">{week}</h2>
                    <ol className="divide-y rounded-xl border bg-background">
                        {items.map((entry) => {
                            const material = entry.material_id ? materials.get(entry.material_id) : undefined
                            const past = entry.day < today
                            return (
                                <li key={entry.id} className={cn("flex flex-col gap-2 p-4 sm:flex-row sm:gap-4", past && "opacity-60", entry.day === today && "bg-primary/5")}>
                                    <div className="w-40 shrink-0 text-sm">
                                        <span className="font-medium">{dayLabel(entry.day)}</span>
                                        {entry.time && <span className="text-muted-foreground">, {entry.time}</span>}
                                        {entry.day === today && <Badge className="ml-2">Сегодня</Badge>}
                                    </div>
                                    <div className="min-w-0 flex-1 space-y-1">
                                        <p className="leading-relaxed"><InlineText text={entry.title} /></p>
                                        {entry.note && <p className="text-sm text-muted-foreground">Сторис: <InlineText text={entry.note} /></p>}
                                        {material && (
                                            <Button variant="link" className="h-auto min-h-11 px-0" onClick={() => onOpen(material.id)}>
                                                Открыть {material.code.toUpperCase()} «{material.title}»{material.status === "published" && " · опубликован"}
                                            </Button>
                                        )}
                                    </div>
                                </li>
                            )
                        })}
                    </ol>
                </section>
            ))}
        </div>
    )
}

function TasksTab({ tasks, canManage, onChanged }: { tasks: AdTask[]; canManage: boolean; onChanged: () => Promise<void> }) {
    const [pending, setPending] = useState<string | null>(null)

    const toggle = async (task: AdTask) => {
        setPending(task.id)
        try {
            await adminUpdateAdTask(task.id, !task.done_at)
            await onChanged()
        } catch (error) {
            toast.error("Не удалось отметить задачу", { description: errorText(error) })
        } finally {
            setPending(null)
        }
    }

    return (
        <ul className="divide-y rounded-xl border bg-background">
            {tasks.map((task) => {
                const done = Boolean(task.done_at)
                return (
                    <li key={task.id}>
                        <button
                            type="button"
                            role="checkbox"
                            aria-checked={done}
                            disabled={!canManage || pending !== null}
                            onClick={() => void toggle(task)}
                            className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-muted/50 disabled:cursor-default disabled:hover:bg-transparent"
                        >
                            <span className={cn("mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2", done ? "border-primary bg-primary text-primary-foreground" : "border-input")}>
                                {pending === task.id ? <Loader2 className="h-4 w-4 animate-spin" /> : done && <Check className="h-4 w-4" />}
                            </span>
                            <span className="min-w-0 flex-1">
                                <span className={cn("block font-medium leading-snug", done && "text-muted-foreground line-through")}>{task.title}</span>
                                {task.note && <span className="mt-1 block text-sm text-muted-foreground"><InlineText text={task.note} /></span>}
                                {done && <span className="mt-1 block text-xs text-muted-foreground">Готово · {task.done_by?.name ?? "команда"}, {formatApiDate(task.done_at)}</span>}
                            </span>
                        </button>
                    </li>
                )
            })}
        </ul>
    )
}
