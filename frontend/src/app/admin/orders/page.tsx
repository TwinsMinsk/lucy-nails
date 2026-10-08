"use client"

import { useAdminPermission } from "@/app/admin/permissions"
import { formatApiDateTime } from "@/lib/format"
import { Suspense, useCallback, useEffect, useRef, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { AlertTriangle, Loader2, ReceiptText, RotateCcw } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
    adminCreateRefund,
    adminGetOrders,
    adminGetPaymentEvents,
    adminGetReconciliation,
    adminGetRefunds,
    adminUpdateRefund,
    AdminOrder,
    AdminPaymentEvent,
    AdminReconciliation,
    AdminRefund,
} from "@/lib/api"

const money = (value: number) => `${(value / 100).toLocaleString("ru-RU")} ₽`

const date = formatApiDateTime

export default function AdminOrdersPage() {
    return <Suspense fallback={<Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" />}><Orders /></Suspense>
}

function Orders() {
    const canManageRefunds = useAdminPermission("refunds.manage")
    const router = useRouter()
    const pathname = usePathname()
    const params = useSearchParams()
    const search = params.get("search") || ""
    const status = params.get("status") || "all"
    const offset = Math.max(0, Number(params.get("offset")) || 0)
    const [searchInput, setSearchInput] = useState(search)
    const [total, setTotal] = useState(0)
    useEffect(() => { setSearchInput(search) }, [search])
    const navigate = (query: string, filter: string, pageOffset: number) => {
        const next = new URLSearchParams()
        if (query) next.set("search", query)
        if (filter !== "all") next.set("status", filter)
        if (pageOffset) next.set("offset", String(pageOffset))
        router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false })
    }
    const [orders, setOrders] = useState<AdminOrder[]>([])
    const [events, setEvents] = useState<AdminPaymentEvent[]>([])
    const [refunds, setRefunds] = useState<AdminRefund[]>([])
    const [reconciliation, setReconciliation] = useState<AdminReconciliation | null>(null)
    const [loading, setLoading] = useState(true)
    const [refundOrder, setRefundOrder] = useState<AdminOrder | null>(null)
    const [refundAmount, setRefundAmount] = useState(0)
    const [refundReason, setRefundReason] = useState("")
    const generation = useRef(0)

    const load = useCallback(async () => {
        const request = ++generation.current
        setLoading(true)
        const results = await Promise.allSettled([
            adminGetOrders({ search, status: status === "all" ? undefined : status, limit: 50, offset }).then((page) => { if (request === generation.current) { setOrders(page.items); setTotal(page.total) } }),
            adminGetPaymentEvents({ limit: 100 }).then((page) => { if (request === generation.current) setEvents(page.items) }),
            adminGetReconciliation().then((value) => { if (request === generation.current) setReconciliation(value) }),
            ...(canManageRefunds ? [adminGetRefunds().then((value) => { if (request === generation.current) setRefunds(value) })] : []),
        ])
        if (request !== generation.current) return
        if (results.some((result) => result.status === "rejected")) toast.error("Часть платежных данных недоступна")
        setLoading(false)
    }, [canManageRefunds, search, status, offset])
    useEffect(() => { void load(); return () => { generation.current += 1 } }, [load])

    const openRefund = (order: AdminOrder) => {
        setRefundOrder(order); setRefundAmount(order.amount_kopecks); setRefundReason("")
    }
    const createRefund = async () => {
        if (!canManageRefunds || !refundOrder?.purchase_id || refundReason.trim().length < 5) return
        await adminCreateRefund({ purchase_id: refundOrder.purchase_id, amount_kopecks: refundAmount, reason: refundReason.trim() })
        setRefundOrder(null); toast.success("Заявка на возврат создана"); await load()
    }
    const moveRefund = async (refund: AdminRefund, target: AdminRefund["status"]) => {
        if (!canManageRefunds) return
        const providerReference = target === "processed" ? window.prompt("Укажите номер/ссылку операции в Prodamus") || undefined : undefined
        if (target === "processed" && !providerReference) return
        if (!window.confirm(`Перевести возврат в статус «${target}»?`)) return
        const reason = window.prompt("Укажите причину изменения статуса возврата")?.trim()
        if (!reason || reason.length < 5) return
        await adminUpdateRefund(refund.id, { status: target, provider_reference: providerReference, reason })
        toast.success("Статус возврата обновлён"); await load()
    }

    if (loading) return <div className="flex min-h-[50vh] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin" /></div>
    const issueCards = reconciliation ? [
        ["Зависшие pending", reconciliation.stale_pending_orders],
        ["Текущие платежи без созданного доступа", reconciliation.successful_purchases_without_active_entitlement],
        ["Ошибки webhook", reconciliation.processed_payment_errors],
        ["Dead letter", reconciliation.dead_letter_notifications],
    ] : []

    return (
        <div className="container max-w-[1500px] space-y-7 px-4 py-8 md:px-6">
            <div><h1 className="flex items-center gap-2 text-3xl font-bold"><ReceiptText className="h-7 w-7" />Заказы и оплаты</h1><p className="mt-1 text-muted-foreground">Снимки цены заказа, события Prodamus, расхождения и внутренний процесс возврата.</p></div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{issueCards.map(([label, value]) => <Card key={label}><CardContent className="flex items-center justify-between p-4"><span className="text-sm">{label}</span><b className={Number(value) ? "text-destructive" : "text-muted-foreground"}>{value}</b></CardContent></Card>)}</div>
            <Card><CardHeader><CardTitle>Заказы ({total})</CardTitle><form className="flex flex-wrap gap-2" onSubmit={(event) => { event.preventDefault(); navigate(searchInput.trim(), status, 0) }}><Input className="w-64" placeholder="Email клиента" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} /><select aria-label="Статус заказа" className="rounded-md border p-2 text-sm" value={status} onChange={(event) => navigate(search, event.target.value, 0)}>{["all", "pending", "paid", "failed", "refunded", "partially_refunded"].map((value) => <option key={value} value={value}>{value === "all" ? "Все статусы" : value}</option>)}</select><Button type="submit" variant="outline">Найти</Button></form><p className="text-xs text-muted-foreground">Время: Москва (UTC+3)</p></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Дата</th><th className="p-3">Клиент</th><th className="p-3">Курс / тариф</th><th className="p-3">Снимок суммы</th><th className="p-3">Статус</th><th className="p-3">Доступ</th><th className="p-3 text-right">Действие</th></tr></thead><tbody>{orders.map((order) => <tr key={order.id} className="border-b"><td className="p-3">{date(order.created_at)}</td><td className="p-3"><b>{order.customer_email}</b><p className="text-xs text-muted-foreground">{order.customer_phone}</p></td><td className="p-3">{order.course_title}<p className="text-xs text-muted-foreground">{order.tariff}</p></td><td className="p-3 font-medium">{money(order.amount_kopecks)} {order.currency}</td><td className="p-3"><Badge variant={order.status === "paid" ? "default" : "secondary"}>{order.status}</Badge></td><td className="p-3">{order.access_days} дней</td><td className="p-3 text-right">{canManageRefunds && order.purchase_id && <Button size="sm" variant="outline" onClick={() => openRefund(order)}><RotateCcw className="mr-2 h-3 w-3" />Возврат</Button>}</td></tr>)}</tbody></table></div><div className="mt-4 flex items-center gap-3"><Button variant="outline" disabled={offset === 0} onClick={() => navigate(search, status, Math.max(0, offset - 50))}>Назад</Button><span className="text-sm">{total ? offset + 1 : 0}–{Math.min(offset + orders.length, total)} из {total}</span><Button variant="outline" disabled={offset + 50 >= total} onClick={() => navigate(search, status, offset + 50)}>Далее</Button></div></CardContent></Card>
            <div className="grid gap-6 xl:grid-cols-2">
                {canManageRefunds && <Card><CardHeader><CardTitle>Возвраты</CardTitle></CardHeader><CardContent className="space-y-3">{refunds.map((refund) => <div key={refund.id} className="rounded-lg border p-3 text-sm"><div className="flex items-center justify-between"><b>{money(refund.amount_kopecks)}</b><Badge variant="outline">{refund.status}</Badge></div><p className="mt-2">{refund.reason}</p><p className="mt-1 text-xs text-muted-foreground">Purchase {refund.purchase_id.slice(0, 8)}… · {date(refund.created_at)}</p><div className="mt-3 flex gap-2">{refund.status === "requested" && <Button size="sm" variant="outline" onClick={() => moveRefund(refund, "submitted")}>Отмечен в Prodamus</Button>}{refund.status === "submitted" && <Button size="sm" onClick={() => moveRefund(refund, "processed")}>Подтвердить возврат</Button>}</div></div>)}{!refunds.length && <p className="text-sm text-muted-foreground">Заявок нет</p>}</CardContent></Card>}
                <Card><CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5" />Журнал webhook</CardTitle></CardHeader><CardContent className="max-h-[520px] space-y-2 overflow-y-auto">{events.map((event) => <div key={event.id} className="rounded-lg border p-3 text-sm"><div className="flex justify-between"><b>{event.event_type}</b><Badge variant={["error", "rejected", "financial_incident"].includes(event.processing_status) ? "destructive" : "outline"}>{event.processing_status === "financial_incident" ? "Финансовый инцидент" : event.processing_status}</Badge></div><p className="mt-1 text-xs text-muted-foreground">{date(event.received_at)} · {event.order_reference || "без order reference"}</p>{event.error_detail && <p className="mt-2 text-destructive">{event.error_code}: {event.error_detail}</p>}</div>)}</CardContent></Card>
            </div>
            <Dialog open={Boolean(refundOrder)} onOpenChange={(open) => { if (!open) setRefundOrder(null) }}><DialogContent><DialogHeader><DialogTitle>Создать заявку на возврат</DialogTitle></DialogHeader><p className="text-sm">{refundOrder?.customer_email} · {refundOrder?.course_title}</p><Input type="number" min={1} max={refundOrder?.amount_kopecks} value={refundAmount} onChange={(event) => setRefundAmount(Number(event.target.value))} /><Textarea value={refundReason} onChange={(event) => setRefundReason(event.target.value)} placeholder="Причина возврата" /><p className="text-xs text-muted-foreground">Деньги возвращаются в официальном кабинете Prodamus. Здесь фиксируется заявка, история и итоговый статус.</p><DialogFooter><Button variant="outline" onClick={() => setRefundOrder(null)}>Отмена</Button><Button disabled={refundReason.trim().length < 5 || refundAmount < 1} onClick={createRefund}>Создать заявку</Button></DialogFooter></DialogContent></Dialog>
        </div>
    )
}
