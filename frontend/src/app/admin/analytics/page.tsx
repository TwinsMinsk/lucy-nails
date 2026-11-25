"use client"

import { FormEvent, ReactNode, useEffect, useState } from "react"
import { BarChart3, Download, Loader2, RefreshCcw, Send, TrendingUp, Users } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
    adminDownloadReportSourcesCsv,
    adminGetReportCohorts,
    adminGetReportDelivery,
    adminGetReportFunnel,
    adminGetReportOverview,
    adminGetReportProgress,
    adminGetReportRefunds,
    adminGetReportSources,
    adminGetReportTariffs,
    adminGetReportTimeseries,
    ReportSource,
} from "@/lib/api"

const isoDate = (date: Date) => date.toISOString().slice(0, 10)
const money = (kopecks: number) => `${(kopecks / 100).toLocaleString("ru-RU")} ₽`

interface ReportFilters {
    date_from: string
    date_to: string
    source: string
    campaign: string
    content: string
}

/** Default period, computed when the page opens (not when the module loads). */
function defaultFilters(): ReportFilters {
    const to = new Date()
    const from = new Date(to)
    from.setDate(from.getDate() - 29)
    return { date_from: isoDate(from), date_to: isoDate(to), source: "", campaign: "", content: "" }
}

const dates = (filters: ReportFilters) => ({ date_from: filters.date_from, date_to: filters.date_to })
const attribution = (filters: ReportFilters) => ({
    ...dates(filters),
    ...(filters.source ? { source: filters.source } : {}),
    ...(filters.campaign ? { campaign: filters.campaign } : {}),
    ...(filters.content ? { content: filters.content } : {}),
})

// Module-level fetchers keep a stable identity for the section hook.
const fetchOverview = (filters: ReportFilters) => adminGetReportOverview(dates(filters))
const fetchTimeseries = (filters: ReportFilters) => adminGetReportTimeseries(dates(filters))
const fetchFunnel = (filters: ReportFilters) => adminGetReportFunnel(dates(filters)).then((report) => report.stages)
const fetchPaymentSources = (filters: ReportFilters) => adminGetReportSources({ ...attribution(filters), basis: "payment" })
const fetchAcquisitionSources = (filters: ReportFilters) => adminGetReportSources({ ...attribution(filters), basis: "acquisition" })
const fetchTariffs = (filters: ReportFilters) => adminGetReportTariffs(dates(filters))
const fetchCohorts = (filters: ReportFilters) => adminGetReportCohorts(dates(filters))
const fetchProgress = (filters: ReportFilters) => adminGetReportProgress(dates(filters))
const fetchRefunds = (filters: ReportFilters) => adminGetReportRefunds(dates(filters))
const fetchDelivery = (filters: ReportFilters) => adminGetReportDelivery(dates(filters))

interface SectionState<T> {
    status: "loading" | "ready" | "error"
    data: T | null
    error: string | null
    retry: () => void
}

/**
 * One report section: its own loading, error and data, bound to the applied
 * filters. Data fetched for another period is never returned.
 */
function useReportSection<T>(fetcher: (filters: ReportFilters) => Promise<T>, filters: ReportFilters): SectionState<T> {
    const key = JSON.stringify(filters)
    const [attempt, setAttempt] = useState(0)
    const [state, setState] = useState<{ key: string; status: SectionState<T>["status"]; data: T | null; error: string | null }>(
        { key: "", status: "loading", data: null, error: null },
    )
    useEffect(() => {
        let current = true
        setState({ key, status: "loading", data: null, error: null })
        fetcher(JSON.parse(key) as ReportFilters)
            .then((data) => { if (current) setState({ key, status: "ready", data, error: null }) })
            .catch((error: unknown) => {
                if (current) setState({ key, status: "error", data: null, error: error instanceof Error ? error.message : "Ошибка загрузки" })
            })
        return () => { current = false }
    }, [fetcher, key, attempt])
    const retry = () => setAttempt((value) => value + 1)
    if (state.key !== key) return { status: "loading", data: null, error: null, retry }
    return { status: state.status, data: state.data, error: state.error, retry }
}

function SectionBody<T>({ section, children }: { section: SectionState<T>; children: (data: T) => ReactNode }) {
    if (section.status === "loading") return <div className="flex min-h-24 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin" /></div>
    if (section.status === "error" || section.data === null) {
        return (
            <div role="alert" className="flex flex-col items-start gap-2 text-sm">
                <p className="text-destructive">Отчёт не загрузился: {section.error ?? "нет данных"}</p>
                <Button size="sm" variant="outline" onClick={section.retry}>Повторить</Button>
            </div>
        )
    }
    return <>{children(section.data)}</>
}

export default function AdminAnalyticsPage() {
    const [form, setForm] = useState<ReportFilters>(defaultFilters)
    const [applied, setApplied] = useState<ReportFilters>(() => form)
    const [downloading, setDownloading] = useState(false)

    const overview = useReportSection(fetchOverview, applied)
    const timeseries = useReportSection(fetchTimeseries, applied)
    const funnel = useReportSection(fetchFunnel, applied)
    const sources = useReportSection(fetchPaymentSources, applied)
    const acquisitionSources = useReportSection(fetchAcquisitionSources, applied)
    const tariffs = useReportSection(fetchTariffs, applied)
    const cohorts = useReportSection(fetchCohorts, applied)
    const progress = useReportSection(fetchProgress, applied)
    const refunds = useReportSection(fetchRefunds, applied)
    const delivery = useReportSection(fetchDelivery, applied)
    const anyLoading = [overview, timeseries, funnel, sources, acquisitionSources, tariffs, cohorts, progress, refunds, delivery]
        .some((section) => section.status === "loading")

    const submit = (event: FormEvent) => {
        event.preventDefault()
        setApplied({ ...form, source: form.source.trim(), campaign: form.campaign.trim(), content: form.content.trim() })
    }
    const field = (name: keyof ReportFilters) => ({
        value: form[name],
        onChange: (event: React.ChangeEvent<HTMLInputElement>) => setForm((current) => ({ ...current, [name]: event.target.value })),
    })

    // The CSV follows the applied filter (what the tables show), not unsaved form input.
    const downloadCsv = async () => {
        setDownloading(true)
        try {
            const blob = await adminDownloadReportSourcesCsv({ ...attribution(applied), basis: "payment" })
            const url = URL.createObjectURL(blob)
            const link = document.createElement("a")
            link.href = url
            link.download = `analytics-sources-${applied.date_from}-${applied.date_to}.csv`
            document.body.appendChild(link)
            link.click()
            link.remove()
            URL.revokeObjectURL(url)
        } catch (error) {
            toast.error("Не удалось скачать CSV", { description: error instanceof Error ? error.message : undefined })
        } finally {
            setDownloading(false)
        }
    }

    const sourceTable = (title: string, section: SectionState<ReportSource[]>, acquisition: boolean) => (
        <Card key={title}><CardHeader><CardTitle>{title}</CardTitle><p className="text-xs text-muted-foreground">{acquisition ? "Все оплаты заказов, созданных за период, включая оплаты позже периода. Это когортный результат." : "Подтверждённые оплаты за период; реальные исторические платежи без заказа включены в direct."}</p></CardHeader><CardContent><SectionBody section={section}>{(rows) => <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Источник</th><th className="p-3">Кампания</th><th className="p-3">Объявление</th>{acquisition && <th className="p-3">Заказы</th>}<th className="p-3">Оплачено</th>{acquisition && <th className="p-3">Конверсия</th>}<th className="p-3 text-right">Выручка</th></tr></thead><tbody>{rows.map((item) => <tr key={JSON.stringify([item.source, item.campaign, item.content])} className="border-b"><td className="p-3 font-medium">{item.source}</td><td className="p-3">{item.campaign}</td><td className="p-3">{item.content}</td>{acquisition && <td className="p-3">{item.orders}</td>}<td className="p-3">{item.paid_orders}</td>{acquisition && <td className="p-3">{item.conversion_pct ?? "—"}%</td>}<td className="p-3 text-right">{money(item.gross_revenue_kopecks)}</td></tr>)}</tbody></table>{rows.length === 0 && <p className="py-3 text-sm text-muted-foreground">Нет данных за выбранный период.</p>}</div>}</SectionBody></CardContent></Card>
    )

    return (
        <div className="container max-w-7xl space-y-7 px-4 py-8 md:px-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div><h1 className="flex items-center gap-2 text-3xl font-bold"><BarChart3 className="h-7 w-7" />Аналитика</h1><p className="mt-1 text-muted-foreground">Подтверждённые деньги, воронка, источники, обучение, когорты и доставка сообщений. Все даты — UTC.</p><p className="mt-1 text-sm">Период отчётов: <b>{applied.date_from} — {applied.date_to}</b></p></div>
                <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
                    <label className="text-xs text-muted-foreground">С даты<Input type="date" {...field("date_from")} className="mt-1" /></label>
                    <label className="text-xs text-muted-foreground">По дату<Input type="date" {...field("date_to")} className="mt-1" /></label>
                    <label className="text-xs text-muted-foreground">Источник<Input {...field("source")} placeholder="Все источники" className="mt-1" /></label>
                    <label className="text-xs text-muted-foreground">Кампания<Input {...field("campaign")} placeholder="Все кампании" className="mt-1" /></label>
                    <label className="text-xs text-muted-foreground">Объявление<Input {...field("content")} placeholder="Все объявления" className="mt-1" /></label>
                    <span className="w-full text-xs text-muted-foreground">Источник, кампания и объявление фильтруют таблицы атрибуции.</span>
                    <Button type="submit" disabled={anyLoading}><RefreshCcw className="mr-2 h-4 w-4" />Обновить</Button>
                    <Button type="button" variant="outline" disabled={downloading} onClick={() => void downloadCsv()}>{downloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}CSV источников</Button>
                </form>
            </div>

            <Card><CardContent className="pt-5"><SectionBody section={overview}>{(data) => <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                {[
                    ["Gross revenue", money(data.gross_revenue_kopecks)],
                    ["Возвраты", money(data.refunded_kopecks)],
                    ["Net revenue", money(data.net_revenue_kopecks)],
                    ["Оплачено", data.paid_orders.toLocaleString("ru-RU")],
                    ["Новые ученики", data.new_students.toLocaleString("ru-RU")],
                ].map(([label, value]) => <div key={label}><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></div>)}
            </div>}</SectionBody></CardContent></Card>

            <div className="grid gap-6 xl:grid-cols-2">
                <Card><CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5" />Выручка по дням</CardTitle></CardHeader><CardContent><SectionBody section={timeseries}>{(points) => {
                    const maxRevenue = Math.max(...points.map((item) => item.gross_revenue_kopecks), 1)
                    return <><div className="flex h-64 items-end gap-1 overflow-x-auto border-b pb-1">{points.map((point) => <div key={point.date} className="group relative flex h-full min-w-3 flex-1 items-end" title={`${point.date}: ${money(point.gross_revenue_kopecks)}`}><div className="w-full rounded-t bg-primary/80 transition-colors group-hover:bg-primary" style={{ height: `${Math.max(point.gross_revenue_kopecks / maxRevenue * 100, point.gross_revenue_kopecks ? 3 : 0)}%` }} /></div>)}</div><div className="mt-2 flex justify-between text-xs text-muted-foreground"><span>{points[0]?.date}</span><span>{points.at(-1)?.date}</span></div></>
                }}</SectionBody></CardContent></Card>
                <Card><CardHeader><CardTitle>Платёжная воронка</CardTitle><p className="text-xs text-muted-foreground">Последовательные пути заказов и посетители без checkout; общий публичный вход может привести к нескольким заказам. Каждый заказ учитывается один раз.</p></CardHeader><CardContent className="space-y-4"><SectionBody section={funnel}>{(stages) => {
                    const maxFunnel = Math.max(...stages.map((item) => item.count), 1)
                    return <>{stages.map((stage) => <div key={stage.event_name}><div className="mb-1 flex justify-between text-sm"><span>{stage.label}</span><span className="font-medium">{stage.count} {stage.conversion_from_previous_pct != null && <span className="text-muted-foreground">· {stage.conversion_from_previous_pct}%</span>}</span></div><div className="h-3 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${stage.count / maxFunnel * 100}%` }} /></div></div>)}</>
                }}</SectionBody></CardContent></Card>
            </div>

            <div className="grid gap-6 xl:grid-cols-3">
                <div className="space-y-6 xl:col-span-2">
                    {sourceTable("Деньги по дате оплаты · first-touch", sources, false)}
                    {sourceTable("Когорта заказов по дате создания · first-touch", acquisitionSources, true)}
                </div>
                <Card><CardHeader><CardTitle>Тарифы</CardTitle></CardHeader><CardContent className="space-y-3"><SectionBody section={tariffs}>{(rows) => <>{rows.map((tariff) => <div key={tariff.tariff} className="rounded-lg border p-3"><div className="flex justify-between"><Badge variant="secondary">{tariff.tariff}</Badge><b>{tariff.paid_orders}</b></div><p className="mt-2 text-lg font-semibold">{money(tariff.gross_revenue_kopecks)}</p></div>)}{rows.length === 0 && <p className="text-sm text-muted-foreground">Нет оплат за период.</p>}</>}</SectionBody></CardContent></Card>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                <Card><CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-5 w-5" />Обучение</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><SectionBody section={progress}>{(data) => <><div className="flex justify-between"><span>Активные ученики</span><b>{data.active_students}</b></div><div className="flex justify-between"><span>Завершённые уроки</span><b>{data.completed_lessons}</b></div><div className="flex justify-between"><span>Выданные сертификаты</span><b>{data.certificates_issued}</b></div></>}</SectionBody></CardContent></Card>
                <Card><CardHeader><CardTitle className="flex items-center gap-2"><Send className="h-5 w-5" />Доставка</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><SectionBody section={delivery}>{(data) => <><div className="flex justify-between"><span>Успешно</span><b>{data.sent}/{data.total}</b></div><div className="flex justify-between"><span>Success rate</span><b>{data.success_rate_pct}%</b></div><div className="flex justify-between"><span>Ожидают / retry</span><b>{data.pending + data.retry}</b></div><div className="flex justify-between text-destructive"><span>Dead letter</span><b>{data.dead_letter}</b></div></>}</SectionBody></CardContent></Card>
                <Card><CardHeader><CardTitle>Заявки на возврат · дата создания</CardTitle></CardHeader><CardContent className="space-y-3"><SectionBody section={refunds}>{(rows) => <>{rows.map((refund) => <div key={refund.status} className="flex items-center justify-between text-sm"><span><Badge variant={refund.status === "processed" ? "destructive" : "outline"}>{refund.status}</Badge> · {refund.requests}</span><b>{money(refund.amount_kopecks)}</b></div>)}{rows.length === 0 && <p className="text-sm text-muted-foreground">Нет заявок за период.</p>}</>}</SectionBody></CardContent></Card>
            </div>

            <Card><CardHeader><CardTitle>Когорты регистрации</CardTitle></CardHeader><CardContent><SectionBody section={cohorts}>{(rows) => <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Когорта</th><th className="p-3">Ученики</th><th className="p-3">Покупатели</th><th className="p-3">С сертификатом</th></tr></thead><tbody>{rows.map((cohort) => <tr key={cohort.cohort} className="border-b"><td className="p-3 font-medium">{cohort.cohort}</td><td className="p-3">{cohort.students}</td><td className="p-3">{cohort.purchasers}</td><td className="p-3">{cohort.certified_students}</td></tr>)}</tbody></table></div>}</SectionBody></CardContent></Card>
        </div>
    )
}
