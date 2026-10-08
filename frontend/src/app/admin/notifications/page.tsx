"use client"

import { formatApiDateTime } from "@/lib/format"
import { Suspense, useCallback, useEffect, useRef, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Input } from "@/components/ui/input"
import { Loader2, RefreshCcw, Send } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { adminGetNotifications, adminRetryNotification, AdminNotification } from "@/lib/api"

const date = formatApiDateTime

export default function AdminNotificationsPage() {
    return <Suspense fallback={<Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" />}><Notifications /></Suspense>
}

function Notifications() {
    const router = useRouter()
    const pathname = usePathname()
    const params = useSearchParams()
    const search = params.get("search") || ""
    const status = params.get("status") || "all"
    const channel = params.get("channel") || "all"
    const offset = Math.max(0, Number(params.get("offset")) || 0)
    const [searchInput, setSearchInput] = useState(search)
    const [total, setTotal] = useState(0)
    useEffect(() => { setSearchInput(search) }, [search])
    const navigate = (query: string, filter: string, medium: string, pageOffset: number) => {
        const next = new URLSearchParams()
        if (query) next.set("search", query)
        if (filter !== "all") next.set("status", filter)
        if (medium !== "all") next.set("channel", medium)
        if (pageOffset) next.set("offset", String(pageOffset))
        router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false })
    }
    const [items, setItems] = useState<AdminNotification[]>([])
    const [loading, setLoading] = useState(true)
    const [retry, setRetry] = useState<AdminNotification | null>(null)
    const [reason, setReason] = useState("")
    const generation = useRef(0)

    const load = useCallback(async () => {
        const request = ++generation.current
        setLoading(true)
        try {
            const page = await adminGetNotifications({ search, status: status === "all" ? undefined : status, channel: channel === "all" ? undefined : channel, limit: 50, offset })
            if (request !== generation.current) return
            setItems(page.items); setTotal(page.total)
        }
        catch (error) { if (request === generation.current) toast.error("Не удалось загрузить очередь", { description: error instanceof Error ? error.message : undefined }) }
        finally { if (request === generation.current) setLoading(false) }
    }, [search, status, channel, offset])
    useEffect(() => { void load(); return () => { generation.current += 1 } }, [load])
    const changeStatus = (value: string) => navigate(search, value, channel, 0)
    const confirmRetry = async () => {
        if (!retry || reason.trim().length < 5) return
        await adminRetryNotification(retry.id, reason.trim())
        toast.success("Сообщение возвращено в очередь"); setRetry(null); setReason(""); await load()
    }

    return (
        <div className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
            <div><h1 className="flex items-center gap-2 text-3xl font-bold"><Send className="h-7 w-7" />Уведомления</h1><p className="mt-1 text-muted-foreground">Email и Telegram outbox, повторы, ошибки и ручная повторная отправка.</p></div>
            <Card><CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between"><CardTitle>Очередь ({total})</CardTitle><form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); navigate(searchInput.trim(), status, channel, 0) }}><Input placeholder="Получатель или тип сообщения" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} /><Button type="submit" variant="outline">Найти</Button></form><Select value={channel} onValueChange={(value) => navigate(search, status, value, 0)}><SelectTrigger className="w-36" aria-label="Канал"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Все каналы</SelectItem><SelectItem value="email">Email</SelectItem><SelectItem value="telegram">Telegram</SelectItem></SelectContent></Select><Select value={status} onValueChange={changeStatus}><SelectTrigger className="w-48"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">Все</SelectItem><SelectItem value="pending">Ожидают</SelectItem><SelectItem value="retry">Повтор</SelectItem><SelectItem value="sent">Отправлены</SelectItem><SelectItem value="dead_letter">Dead letter</SelectItem></SelectContent></Select></CardHeader><CardContent><p className="mb-3 text-xs text-muted-foreground">Время: Москва (UTC+3)</p>
                {loading ? <Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" /> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Создано</th><th className="p-3">Тип</th><th className="p-3">Канал</th><th className="p-3">Получатель</th><th className="p-3">Статус</th><th className="p-3">Попытки</th><th className="p-3">Ошибка</th><th className="p-3 text-right">Действие</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className="border-b align-top"><td className="p-3">{date(item.created_at)}</td><td className="p-3">{item.kind}</td><td className="p-3">{item.channel}</td><td className="p-3">{item.recipient}</td><td className="p-3"><Badge variant={item.status === "dead_letter" ? "destructive" : "outline"}>{item.status}</Badge></td><td className="p-3">{item.attempts}/{item.max_attempts}</td><td className="max-w-xs p-3 text-xs text-destructive">{item.last_error || "—"}</td><td className="p-3 text-right">{item.status !== "sent" && <Button size="sm" variant="outline" onClick={() => setRetry(item)}><RefreshCcw className="mr-2 h-3 w-3" />Повторить</Button>}</td></tr>)}</tbody></table></div>}
                <div className="mt-4 flex items-center gap-3"><Button variant="outline" disabled={loading || offset === 0} onClick={() => navigate(search, status, channel, Math.max(0, offset - 50))}>Назад</Button><span className="text-sm">{total ? offset + 1 : 0}–{Math.min(offset + items.length, total)} из {total}</span><Button variant="outline" disabled={loading || offset + 50 >= total} onClick={() => navigate(search, status, channel, offset + 50)}>Далее</Button></div>
            </CardContent></Card>
            <Dialog open={Boolean(retry)} onOpenChange={(open) => { if (!open) setRetry(null) }}><DialogContent><DialogHeader><DialogTitle>Повторить отправку</DialogTitle></DialogHeader><p className="text-sm text-muted-foreground">{retry?.recipient} · {retry?.kind}</p><Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Причина ручного повтора" /><DialogFooter><Button variant="outline" onClick={() => setRetry(null)}>Отмена</Button><Button disabled={reason.trim().length < 5} onClick={confirmRetry}>Вернуть в очередь</Button></DialogFooter></DialogContent></Dialog>
        </div>
    )
}
