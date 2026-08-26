"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2, RefreshCcw, Send } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { adminGetNotifications, adminRetryNotification, AdminNotification } from "@/lib/api"

const date = (value?: string | null) => value ? new Date(value).toLocaleString("ru-RU") : "—"

export default function AdminNotificationsPage() {
    const [items, setItems] = useState<AdminNotification[]>([])
    const [status, setStatus] = useState("all")
    const [loading, setLoading] = useState(true)
    const [retry, setRetry] = useState<AdminNotification | null>(null)
    const [reason, setReason] = useState("")

    const load = useCallback(async (filter = "all") => {
        setLoading(true)
        try { setItems((await adminGetNotifications({ status: filter === "all" ? undefined : filter, limit: 200 })).items) }
        catch (error) { toast.error("Не удалось загрузить очередь", { description: error instanceof Error ? error.message : undefined }) }
        finally { setLoading(false) }
    }, [])
    useEffect(() => { void load("all") }, [load])
    const changeStatus = (value: string) => { setStatus(value); void load(value) }
    const confirmRetry = async () => {
        if (!retry || reason.trim().length < 5) return
        await adminRetryNotification(retry.id, reason.trim())
        toast.success("Сообщение возвращено в очередь"); setRetry(null); setReason(""); await load(status)
    }

    return (
        <div className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
            <div><h1 className="flex items-center gap-2 text-3xl font-bold"><Send className="h-7 w-7" />Уведомления</h1><p className="mt-1 text-muted-foreground">Email и Telegram outbox, повторы, ошибки и ручная повторная отправка.</p></div>
            <Card><CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between"><CardTitle>Очередь</CardTitle><Select value={status} onValueChange={changeStatus}><SelectTrigger className="w-48"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Все</SelectItem><SelectItem value="pending">Ожидают</SelectItem><SelectItem value="sent">Отправлены</SelectItem><SelectItem value="dead_letter">Dead letter</SelectItem></SelectContent></Select></CardHeader><CardContent>
                {loading ? <Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" /> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Создано</th><th className="p-3">Тип</th><th className="p-3">Канал</th><th className="p-3">Получатель</th><th className="p-3">Статус</th><th className="p-3">Попытки</th><th className="p-3">Ошибка</th><th className="p-3 text-right">Действие</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className="border-b align-top"><td className="p-3">{date(item.created_at)}</td><td className="p-3">{item.kind}</td><td className="p-3">{item.channel}</td><td className="p-3">{item.recipient}</td><td className="p-3"><Badge variant={item.status === "dead_letter" ? "destructive" : "outline"}>{item.status}</Badge></td><td className="p-3">{item.attempts}/{item.max_attempts}</td><td className="max-w-xs p-3 text-xs text-destructive">{item.last_error || "—"}</td><td className="p-3 text-right">{item.status !== "sent" && <Button size="sm" variant="outline" onClick={() => setRetry(item)}><RefreshCcw className="mr-2 h-3 w-3" />Повторить</Button>}</td></tr>)}</tbody></table></div>}
            </CardContent></Card>
            <Dialog open={Boolean(retry)} onOpenChange={(open) => { if (!open) setRetry(null) }}><DialogContent><DialogHeader><DialogTitle>Повторить отправку</DialogTitle></DialogHeader><p className="text-sm text-muted-foreground">{retry?.recipient} · {retry?.kind}</p><Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Причина ручного повтора" /><DialogFooter><Button variant="outline" onClick={() => setRetry(null)}>Отмена</Button><Button disabled={reason.trim().length < 5} onClick={confirmRetry}>Вернуть в очередь</Button></DialogFooter></DialogContent></Dialog>
        </div>
    )
}
