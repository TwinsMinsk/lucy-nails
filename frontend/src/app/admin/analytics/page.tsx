"use client"

import { FormEvent, useCallback, useEffect, useState } from "react"
import { BarChart3, Download, Loader2, RefreshCcw, Send, TrendingUp, Users } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import {
    adminGetReportCohorts,
    adminGetReportDelivery,
    adminGetReportFunnel,
    adminGetReportOverview,
    adminGetReportProgress,
    adminGetReportRefunds,
    adminGetReportSources,
    adminGetReportTariffs,
    adminGetReportTimeseries,
    adminReportSourcesCsvUrl,
    ReportCohort,
    ReportDelivery,
    ReportFunnelStage,
    ReportOverview,
    ReportProgress,
    ReportRefund,
    ReportSource,
    ReportTariff,
    ReportTimeseriesPoint,
} from "@/lib/api"

const isoDate = (date: Date) => date.toISOString().slice(0, 10)
const money = (kopecks: number) => `${(kopecks / 100).toLocaleString("ru-RU")} ₽`
const defaultTo = new Date()
const defaultFrom = new Date(defaultTo)
defaultFrom.setDate(defaultFrom.getDate() - 29)
const DEFAULT_DATE_FROM = isoDate(defaultFrom)
const DEFAULT_DATE_TO = isoDate(defaultTo)

interface AnalyticsData {
    overview: ReportOverview
    timeseries: ReportTimeseriesPoint[]
    funnel: ReportFunnelStage[]
    sources: ReportSource[]
    tariffs: ReportTariff[]
    cohorts: ReportCohort[]
    progress: ReportProgress
    refunds: ReportRefund[]
    delivery: ReportDelivery
}

export default function AdminAnalyticsPage() {
    const [dateFrom, setDateFrom] = useState(DEFAULT_DATE_FROM)
    const [dateTo, setDateTo] = useState(DEFAULT_DATE_TO)
    const [data, setData] = useState<AnalyticsData | null>(null)
    const [loading, setLoading] = useState(true)

    const load = useCallback(async (from: string, to: string) => {
        setLoading(true)
        const params = { date_from: from, date_to: to }
        try {
            const [overview, timeseries, funnel, sources, tariffs, cohorts, progress, refunds, delivery] = await Promise.all([
                adminGetReportOverview(params),
                adminGetReportTimeseries(params),
                adminGetReportFunnel(params),
                adminGetReportSources(params),
                adminGetReportTariffs(params),
                adminGetReportCohorts(params),
                adminGetReportProgress(params),
                adminGetReportRefunds(params),
                adminGetReportDelivery(params),
            ])
            setData({ overview, timeseries, funnel: funnel.stages, sources, tariffs, cohorts, progress, refunds, delivery })
        } catch (error) {
            toast.error("Не удалось загрузить управленческие отчёты", {
                description: error instanceof Error ? error.message : undefined,
            })
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { void load(DEFAULT_DATE_FROM, DEFAULT_DATE_TO) }, [load])
    const submit = (event: FormEvent) => { event.preventDefault(); void load(dateFrom, dateTo) }

    const maxRevenue = Math.max(...(data?.timeseries.map((item) => item.gross_revenue_kopecks) ?? [0]), 1)
    const maxFunnel = Math.max(...(data?.funnel.map((item) => item.count) ?? [0]), 1)

    return (
        <div className="container max-w-7xl space-y-7 px-4 py-8 md:px-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div><h1 className="flex items-center gap-2 text-3xl font-bold"><BarChart3 className="h-7 w-7" />Аналитика</h1><p className="mt-1 text-muted-foreground">Подтверждённые деньги, воронка, источники, обучение, когорты и доставка сообщений.</p></div>
                <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
                    <label className="text-xs text-muted-foreground">С даты<Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1" /></label>
                    <label className="text-xs text-muted-foreground">По дату<Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1" /></label>
                    <Button type="submit" disabled={loading}><RefreshCcw className="mr-2 h-4 w-4" />Обновить</Button>
                    <Button variant="outline" asChild><a href={adminReportSourcesCsvUrl({ date_from: dateFrom, date_to: dateTo })}><Download className="mr-2 h-4 w-4" />CSV источников</a></Button>
                </form>
            </div>

            {loading && !data ? <div className="flex min-h-[50vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div> : data && <>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                    {[
                        ["Gross revenue", money(data.overview.gross_revenue_kopecks)],
                        ["Возвраты", money(data.overview.refunded_kopecks)],
                        ["Net revenue", money(data.overview.net_revenue_kopecks)],
                        ["Оплачено", data.overview.paid_orders.toLocaleString("ru-RU")],
                        ["Новые ученики", data.overview.new_students.toLocaleString("ru-RU")],
                    ].map(([label, value]) => <Card key={label}><CardContent className="pt-5"><p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-2 text-2xl font-bold">{value}</p></CardContent></Card>)}
                </div>

                <div className="grid gap-6 xl:grid-cols-2">
                    <Card><CardHeader><CardTitle className="flex items-center gap-2"><TrendingUp className="h-5 w-5" />Выручка по дням</CardTitle></CardHeader><CardContent><div className="flex h-64 items-end gap-1 overflow-x-auto border-b pb-1">{data.timeseries.map((point) => <div key={point.date} className="group relative flex h-full min-w-3 flex-1 items-end" title={`${point.date}: ${money(point.gross_revenue_kopecks)}`}><div className="w-full rounded-t bg-primary/80 transition-colors group-hover:bg-primary" style={{ height: `${Math.max(point.gross_revenue_kopecks / maxRevenue * 100, point.gross_revenue_kopecks ? 3 : 0)}%` }} /></div>)}</div><div className="mt-2 flex justify-between text-xs text-muted-foreground"><span>{data.timeseries[0]?.date}</span><span>{data.timeseries.at(-1)?.date}</span></div></CardContent></Card>
                    <Card><CardHeader><CardTitle>Платёжная воронка</CardTitle></CardHeader><CardContent className="space-y-4">{data.funnel.map((stage) => <div key={stage.event_name}><div className="mb-1 flex justify-between text-sm"><span>{stage.label}</span><span className="font-medium">{stage.count} {stage.conversion_from_previous_pct != null && <span className="text-muted-foreground">· {stage.conversion_from_previous_pct}%</span>}</span></div><div className="h-3 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${stage.count / maxFunnel * 100}%` }} /></div></div>)}</CardContent></Card>
                </div>

                <div className="grid gap-6 xl:grid-cols-3">
                    <Card className="xl:col-span-2"><CardHeader><CardTitle>Источники first-touch</CardTitle></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Источник</th><th className="p-3">Заказы</th><th className="p-3">Оплачено</th><th className="p-3">Конверсия</th><th className="p-3 text-right">Выручка</th></tr></thead><tbody>{data.sources.map((source) => <tr key={source.source} className="border-b"><td className="p-3 font-medium">{source.source}</td><td className="p-3">{source.orders}</td><td className="p-3">{source.paid_orders}</td><td className="p-3">{source.conversion_pct}%</td><td className="p-3 text-right">{money(source.gross_revenue_kopecks)}</td></tr>)}</tbody></table></div></CardContent></Card>
                    <Card><CardHeader><CardTitle>Тарифы</CardTitle></CardHeader><CardContent className="space-y-3">{data.tariffs.map((tariff) => <div key={tariff.tariff} className="rounded-lg border p-3"><div className="flex justify-between"><Badge variant="secondary">{tariff.tariff}</Badge><b>{tariff.paid_orders}</b></div><p className="mt-2 text-lg font-semibold">{money(tariff.gross_revenue_kopecks)}</p></div>)}{data.tariffs.length === 0 && <p className="text-sm text-muted-foreground">Нет оплат за период.</p>}</CardContent></Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-3">
                    <Card><CardHeader><CardTitle className="flex items-center gap-2"><Users className="h-5 w-5" />Обучение</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><div className="flex justify-between"><span>Активные ученики</span><b>{data.progress.active_students}</b></div><div className="flex justify-between"><span>Завершённые уроки</span><b>{data.progress.completed_lessons}</b></div><div className="flex justify-between"><span>Выданные сертификаты</span><b>{data.progress.certificates_issued}</b></div></CardContent></Card>
                    <Card><CardHeader><CardTitle className="flex items-center gap-2"><Send className="h-5 w-5" />Доставка</CardTitle></CardHeader><CardContent className="space-y-3 text-sm"><div className="flex justify-between"><span>Успешно</span><b>{data.delivery.sent}/{data.delivery.total}</b></div><div className="flex justify-between"><span>Success rate</span><b>{data.delivery.success_rate_pct}%</b></div><div className="flex justify-between"><span>Ожидают / retry</span><b>{data.delivery.pending + data.delivery.retry}</b></div><div className="flex justify-between text-destructive"><span>Dead letter</span><b>{data.delivery.dead_letter}</b></div></CardContent></Card>
                    <Card><CardHeader><CardTitle>Возвраты</CardTitle></CardHeader><CardContent className="space-y-3">{data.refunds.map((refund) => <div key={refund.status} className="flex items-center justify-between text-sm"><span><Badge variant={refund.status === "processed" ? "destructive" : "outline"}>{refund.status}</Badge> · {refund.requests}</span><b>{money(refund.amount_kopecks)}</b></div>)}{data.refunds.length === 0 && <p className="text-sm text-muted-foreground">Нет заявок за период.</p>}</CardContent></Card>
                </div>

                <Card><CardHeader><CardTitle>Когорты регистрации</CardTitle></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Когорта</th><th className="p-3">Ученики</th><th className="p-3">Покупатели</th><th className="p-3">С сертификатом</th></tr></thead><tbody>{data.cohorts.map((cohort) => <tr key={cohort.cohort} className="border-b"><td className="p-3 font-medium">{cohort.cohort}</td><td className="p-3">{cohort.students}</td><td className="p-3">{cohort.purchasers}</td><td className="p-3">{cohort.certified_students}</td></tr>)}</tbody></table></div></CardContent></Card>
            </>}
        </div>
    )
}
