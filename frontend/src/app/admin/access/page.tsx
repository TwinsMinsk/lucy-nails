"use client"

import { FormEvent, useCallback, useEffect, useState } from "react"
import { KeyRound, Loader2, Search } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { adminGetEntitlements, adminRevokeEntitlement, AdminEntitlement } from "@/lib/api"

const date = (value: string) => new Date(value).toLocaleString("ru-RU")

export default function AdminAccessPage() {
    const [items, setItems] = useState<AdminEntitlement[]>([])
    const [total, setTotal] = useState(0)
    const [search, setSearch] = useState("")
    const [status, setStatus] = useState("active")
    const [loading, setLoading] = useState(true)
    const [revoke, setRevoke] = useState<AdminEntitlement | null>(null)
    const [reason, setReason] = useState("")

    const load = useCallback(async () => {
        setLoading(true)
        try {
            const response = await adminGetEntitlements({ search, status: status === "all" ? undefined : status, limit: 200 })
            setItems(response.items)
            setTotal(response.total)
        } catch (error) {
            toast.error("Не удалось загрузить доступы", { description: error instanceof Error ? error.message : undefined })
        } finally { setLoading(false) }
    }, [search, status])

    useEffect(() => { void load() }, [load])
    const submit = (event: FormEvent) => { event.preventDefault(); void load() }

    const confirmRevoke = async () => {
        if (!revoke || reason.trim().length < 5) return
        await adminRevokeEntitlement(revoke.id, reason.trim())
        toast.success("Доступ отозван")
        setRevoke(null); setReason(""); await load()
    }

    return (
        <div className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
            <div><h1 className="flex items-center gap-2 text-3xl font-bold"><KeyRound className="h-7 w-7" />Доступы</h1><p className="mt-1 text-muted-foreground">Выдача выполняется из карточки ученика. Здесь — контроль сроков и отзыв с обязательной причиной.</p></div>
            <Card>
                <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <CardTitle>{total} записей</CardTitle>
                    <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
                        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Email ученика" className="sm:w-72" />
                        <Select value={status} onValueChange={setStatus}><SelectTrigger className="sm:w-40"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="active">Активные</SelectItem><SelectItem value="revoked">Отозванные</SelectItem><SelectItem value="all">Все</SelectItem></SelectContent></Select>
                        <Button type="submit" variant="outline"><Search className="h-4 w-4" /></Button>
                    </form>
                </CardHeader>
                <CardContent>
                    {loading ? <Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" /> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Ученик</th><th className="p-3">Курс</th><th className="p-3">Источник</th><th className="p-3">Статус</th><th className="p-3">Начало</th><th className="p-3">Окончание</th><th className="p-3 text-right">Действие</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} className="border-b"><td className="p-3 font-medium">{item.user_email}</td><td className="p-3">{item.course_title}</td><td className="p-3">{item.source}</td><td className="p-3"><Badge variant={item.status === "active" ? "default" : "secondary"}>{item.status}</Badge></td><td className="p-3">{date(item.starts_at)}</td><td className="p-3">{date(item.expires_at)}</td><td className="p-3 text-right">{item.status === "active" && <Button size="sm" variant="outline" onClick={() => setRevoke(item)}>Отозвать</Button>}</td></tr>)}</tbody></table></div>}
                </CardContent>
            </Card>
            <Dialog open={Boolean(revoke)} onOpenChange={(open) => { if (!open) setRevoke(null) }}><DialogContent><DialogHeader><DialogTitle>Отозвать доступ</DialogTitle></DialogHeader><p className="text-sm text-muted-foreground">{revoke?.user_email} · {revoke?.course_title}</p><Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Укажите причину (обязательно)" /><DialogFooter><Button variant="outline" onClick={() => setRevoke(null)}>Отмена</Button><Button variant="destructive" disabled={reason.trim().length < 5} onClick={confirmRevoke}>Отозвать</Button></DialogFooter></DialogContent></Dialog>
        </div>
    )
}
