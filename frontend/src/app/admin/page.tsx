"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { AlertTriangle, Banknote, KeyRound, Loader2, MailWarning, ReceiptText, Users } from "lucide-react"
import { toast } from "sonner"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { adminGetDashboard, adminGetReconciliation, AdminDashboardResponse, AdminReconciliation } from "@/lib/api"

const money = (kopecks: number) => `${(kopecks / 100).toLocaleString("ru-RU")} ₽`

export default function AdminDashboardPage() {
    const [data, setData] = useState<AdminDashboardResponse | null>(null)
    const [reconciliation, setReconciliation] = useState<AdminReconciliation | null>(null)

    useEffect(() => {
        Promise.all([adminGetDashboard(), adminGetReconciliation()])
            .then(([dashboard, reconciliationData]) => {
                setData(dashboard)
                setReconciliation(reconciliationData)
            })
            .catch((error) => toast.error("Не удалось загрузить операционный обзор", { description: error.message }))
    }, [])

    if (!data) return <div className="flex min-h-[50vh] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin" /></div>

    const cards = [
        { title: "Ученики", value: data.total_students, icon: Users, href: "/admin/users" },
        { title: "Активные доступы", value: data.active_entitlements, icon: KeyRound, href: "/admin/access" },
        { title: "Чистая выручка", value: money(data.net_revenue_kopecks), icon: Banknote, href: "/admin/orders" },
        { title: "Заказы ожидают", value: data.pending_orders, icon: ReceiptText, href: "/admin/orders" },
        { title: "Ошибки платежей", value: data.payment_errors, icon: AlertTriangle, href: "/admin/orders" },
        { title: "Не доставлено", value: data.notification_dead_letters, icon: MailWarning, href: "/admin/notifications" },
    ]

    const issues = reconciliation ? [
        ["Заказы без ответа более 2 часов", reconciliation.stale_pending_orders],
        ["Текущие платежи без созданного доступа", reconciliation.successful_purchases_without_active_entitlement],
        ["Ошибки обработки webhook", reconciliation.processed_payment_errors],
        ["Сообщения в dead letter", reconciliation.dead_letter_notifications],
    ] as const : []

    return (
        <div className="container max-w-7xl space-y-7 px-4 py-8 md:px-6">
            <div>
                <h1 className="text-3xl font-bold">Операционный центр</h1>
                <p className="mt-1 text-muted-foreground">Продажи, доступы и проблемы, требующие внимания прямо сейчас.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {cards.map((item) => (
                    <Link href={item.href} key={item.title}>
                        <Card className="h-full transition-colors hover:border-primary/50">
                            <CardHeader className="flex flex-row items-center justify-between pb-2">
                                <CardTitle className="text-sm text-muted-foreground">{item.title}</CardTitle>
                                <item.icon className="h-4 w-4 text-primary" />
                            </CardHeader>
                            <CardContent><p className="text-3xl font-bold">{item.value}</p></CardContent>
                        </Card>
                    </Link>
                ))}
            </div>
            <div className="grid gap-5 lg:grid-cols-2">
                <Card>
                    <CardHeader><CardTitle>Финансы</CardTitle></CardHeader>
                    <CardContent className="space-y-3 text-sm">
                        <div className="flex justify-between"><span>Подтверждённая выручка</span><b>{money(data.gross_revenue_kopecks)}</b></div>
                        <div className="flex justify-between"><span>Подтверждённые возвраты</span><b>{money(data.refunded_kopecks)}</b></div>
                        <div className="flex justify-between border-t pt-3"><span>Чистая выручка</span><b>{money(data.net_revenue_kopecks)}</b></div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader><CardTitle>Контроль расхождений</CardTitle></CardHeader>
                    <CardContent className="space-y-3">
                        {issues.map(([label, value]) => (
                            <div key={label} className="flex items-center justify-between text-sm">
                                <span>{label}</span>
                                <span className={value ? "font-bold text-destructive" : "text-muted-foreground"}>{value}</span>
                            </div>
                        ))}
                        <div className="flex items-center justify-between border-t pt-3 text-sm">
                            <span>Доступы заканчиваются за 7 дней</span><b>{data.expiring_entitlements_7d}</b>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
