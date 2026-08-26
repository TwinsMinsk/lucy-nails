"use client"

import { useEffect, useState } from "react"
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
const date = (value?: string | null) => value ? new Date(value).toLocaleString("ru-RU") : "—"

export default function AdminOrdersPage() {
    const [orders, setOrders] = useState<AdminOrder[]>([])
    const [events, setEvents] = useState<AdminPaymentEvent[]>([])
    const [refunds, setRefunds] = useState<AdminRefund[]>([])
    const [reconciliation, setReconciliation] = useState<AdminReconciliation | null>(null)
    const [loading, setLoading] = useState(true)
    const [refundOrder, setRefundOrder] = useState<AdminOrder | null>(null)
    const [refundAmount, setRefundAmount] = useState(0)
    const [refundReason, setRefundReason] = useState("")

    const load = async () => {
        setLoading(true)
        try {
            const [orderPage, eventPage, refundItems, recon] = await Promise.all([
                adminGetOrders({ limit: 200 }),
                adminGetPaymentEvents({ limit: 100 }),
                adminGetRefunds(),
                adminGetReconciliation(),
            ])
            setOrders(orderPage.items); setEvents(eventPage.items); setRefunds(refundItems); setReconciliation(recon)
        } catch (error) {
            toast.error("Не удалось загрузить платежный контур", { description: error instanceof Error ? error.message : undefined })
        } finally { setLoading(false) }
    }
    useEffect(() => { void load() }, [])

    const openRefund = (order: AdminOrder) => {
        setRefundOrder(order); setRefundAmount(order.amount_kopecks); setRefundReason("")
    }
    const createRefund = async () => {
        if (!refundOrder?.purchase_id || refundReason.trim().length < 5) return
        await adminCreateRefund({ purchase_id: refundOrder.purchase_id, amount_kopecks: refundAmount, reason: refundReason.trim() })
        setRefundOrder(null); toast.success("Заявка на возврат создана"); await load()
    }
    const moveRefund = async (refund: AdminRefund, target: AdminRefund["status"]) => {
        const providerReference = target === "processed" ? window.prompt("Укажите номер/ссылку операции в Prodamus") || undefined : undefined
        if (target === "processed" && !providerReference) return
        if (!window.confirm(`Перевести возврат в статус «${target}»?`)) return
        await adminUpdateRefund(refund.id, { status: target, provider_reference: providerReference })
        toast.success("Статус возврата обновлён"); await load()
    }

    if (loading) return <div className="flex min-h-[50vh] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin" /></div>
    const issueCards = reconciliation ? [
        ["Зависшие pending", reconciliation.stale_pending_orders],
        ["Платежи без доступа", reconciliation.successful_purchases_without_active_entitlement],
        ["Ошибки webhook", reconciliation.processed_payment_errors],
        ["Dead letter", reconciliation.dead_letter_notifications],
    ] : []

    return (
        <div className="container max-w-[1500px] space-y-7 px-4 py-8 md:px-6">
            <div><h1 className="flex items-center gap-2 text-3xl font-bold"><ReceiptText className="h-7 w-7" />Заказы и оплаты</h1><p className="mt-1 text-muted-foreground">Снимки цены заказа, события Prodamus, расхождения и внутренний процесс возврата.</p></div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{issueCards.map(([label, value]) => <Card key={label}><CardContent className="flex items-center justify-between p-4"><span className="text-sm">{label}</span><b className={Number(value) ? "text-destructive" : "text-muted-foreground"}>{value}</b></CardContent></Card>)}</div>
            <Card><CardHeader><CardTitle>Заказы ({orders.length})</CardTitle></CardHeader><CardContent><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Дата</th><th className="p-3">Клиент</th><th className="p-3">Курс / тариф</th><th className="p-3">Снимок суммы</th><th className="p-3">Статус</th><th className="p-3">Доступ</th><th className="p-3 text-right">Действие</th></tr></thead><tbody>{orders.map((order) => <tr key={order.id} className="border-b"><td className="p-3">{date(order.created_at)}</td><td className="p-3"><b>{order.customer_email}</b><p className="text-xs text-muted-foreground">{order.customer_phone}</p></td><td className="p-3">{order.course_title}<p className="text-xs text-muted-foreground">{order.tariff}</p></td><td className="p-3 font-medium">{money(order.amount_kopecks)} {order.currency}</td><td className="p-3"><Badge variant={order.status === "paid" ? "default" : "secondary"}>{order.status}</Badge></td><td className="p-3">{order.access_days} дней</td><td className="p-3 text-right">{order.purchase_id && <Button size="sm" variant="outline" onClick={() => openRefund(order)}><RotateCcw className="mr-2 h-3 w-3" />Возврат</Button>}</td></tr>)}</tbody></table></div></CardContent></Card>
            <div className="grid gap-6 xl:grid-cols-2">
                <Card><CardHeader><CardTitle>Возвраты</CardTitle></CardHeader><CardContent className="space-y-3">{refunds.map((refund) => <div key={refund.id} className="rounded-lg border p-3 text-sm"><div className="flex items-center justify-between"><b>{money(refund.amount_kopecks)}</b><Badge variant="outline">{refund.status}</Badge></div><p className="mt-2">{refund.reason}</p><p className="mt-1 text-xs text-muted-foreground">Purchase {refund.purchase_id.slice(0, 8)}… · {date(refund.created_at)}</p><div className="mt-3 flex gap-2">{refund.status === "requested" && <Button size="sm" variant="outline" onClick={() => moveRefund(refund, "submitted")}>Отмечен в Prodamus</Button>}{refund.status === "submitted" && <Button size="sm" onClick={() => moveRefund(refund, "processed")}>Подтвердить возврат</Button>}</div></div>)}{!refunds.length && <p className="text-sm text-muted-foreground">Заявок нет</p>}</CardContent></Card>
                <Card><CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="h-5 w-5" />Журнал webhook</CardTitle></CardHeader><CardContent className="max-h-[520px] space-y-2 overflow-y-auto">{events.map((event) => <div key={event.id} className="rounded-lg border p-3 text-sm"><div className="flex justify-between"><b>{event.event_type}</b><Badge variant={event.processing_status === "error" ? "destructive" : "outline"}>{event.processing_status}</Badge></div><p className="mt-1 text-xs text-muted-foreground">{date(event.received_at)} · {event.order_reference || "без order reference"}</p>{event.error_detail && <p className="mt-2 text-destructive">{event.error_code}: {event.error_detail}</p>}</div>)}</CardContent></Card>
            </div>
            <Dialog open={Boolean(refundOrder)} onOpenChange={(open) => { if (!open) setRefundOrder(null) }}><DialogContent><DialogHeader><DialogTitle>Создать заявку на возврат</DialogTitle></DialogHeader><p className="text-sm">{refundOrder?.customer_email} · {refundOrder?.course_title}</p><Input type="number" min={1} max={refundOrder?.amount_kopecks} value={refundAmount} onChange={(event) => setRefundAmount(Number(event.target.value))} /><Textarea value={refundReason} onChange={(event) => setRefundReason(event.target.value)} placeholder="Причина возврата" /><p className="text-xs text-muted-foreground">Деньги возвращаются в официальном кабинете Prodamus. Здесь фиксируется заявка, история и итоговый статус.</p><DialogFooter><Button variant="outline" onClick={() => setRefundOrder(null)}>Отмена</Button><Button disabled={refundReason.trim().length < 5 || refundAmount < 1} onClick={createRefund}>Создать заявку</Button></DialogFooter></DialogContent></Dialog>
        </div>
    )
}
