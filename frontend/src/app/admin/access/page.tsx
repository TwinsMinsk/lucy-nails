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
import {
    adminChangeEntitlementState,
    adminExtendEntitlement,
    adminGetEntitlements,
    adminRevokeEntitlement,
    AdminEntitlement,
} from "@/lib/api"

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
            const response = await adminGetEntitlements({
                search,
                status: status === "all" ? undefined : status,
                limit: 200,
            })
            setItems(response.items)
            setTotal(response.total)
        } catch (error) {
            toast.error("Не удалось загрузить доступы", {
                description: error instanceof Error ? error.message : undefined,
            })
        } finally {
            setLoading(false)
        }
    }, [search, status])

    useEffect(() => { void load() }, [load])

    const submit = (event: FormEvent) => {
        event.preventDefault()
        void load()
    }

    const confirmRevoke = async () => {
        if (!revoke || reason.trim().length < 5) return
        await adminRevokeEntitlement(revoke.id, reason.trim())
        toast.success("Доступ отозван")
        setRevoke(null)
        setReason("")
        await load()
    }

    const extend = async (item: AdminEntitlement) => {
        const rawDays = window.prompt("На сколько дней продлить доступ?", "30")
        if (!rawDays) return
        const days = Number(rawDays)
        if (!Number.isInteger(days) || days < 1 || days > 3650) {
            toast.error("Укажите целое число дней от 1 до 3650")
            return
        }
        const actionReason = window.prompt("Укажите причину продления")?.trim()
        if (!actionReason || actionReason.length < 5) return
        await adminExtendEntitlement(item.id, days, actionReason)
        toast.success("Доступ продлён")
        await load()
    }

    const changeState = async (item: AdminEntitlement, action: "suspend" | "restore") => {
        const actionReason = window.prompt(
            action === "suspend"
                ? "Укажите причину приостановки"
                : "Укажите причину восстановления",
        )?.trim()
        if (!actionReason || actionReason.length < 5) return
        await adminChangeEntitlementState(item.id, action, actionReason)
        toast.success(action === "suspend" ? "Доступ приостановлен" : "Доступ восстановлен")
        await load()
    }

    return (
        <div className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
            <div>
                <h1 className="flex items-center gap-2 text-3xl font-bold">
                    <KeyRound className="h-7 w-7" />Доступы
                </h1>
                <p className="mt-1 text-muted-foreground">
                    Продление, приостановка, восстановление и отзыв с обязательной причиной и audit trail.
                </p>
            </div>
            <Card>
                <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <CardTitle>{total} записей</CardTitle>
                    <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
                        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Email ученика" className="sm:w-72" />
                        <Select value={status} onValueChange={setStatus}>
                            <SelectTrigger className="sm:w-48"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="active">Активные</SelectItem>
                                <SelectItem value="suspended">Приостановленные</SelectItem>
                                <SelectItem value="expired">Истёкшие</SelectItem>
                                <SelectItem value="revoked">Отозванные</SelectItem>
                                <SelectItem value="all">Все</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button type="submit" variant="outline"><Search className="h-4 w-4" /></Button>
                    </form>
                </CardHeader>
                <CardContent>
                    {loading ? (
                        <Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" />
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Ученик</th><th className="p-3">Курс</th><th className="p-3">Источник</th><th className="p-3">Статус</th><th className="p-3">Начало</th><th className="p-3">Окончание</th><th className="p-3 text-right">Действия</th></tr></thead>
                                <tbody>{items.map((item) => (
                                    <tr key={item.id} className="border-b">
                                        <td className="p-3 font-medium">{item.user_email}</td>
                                        <td className="p-3">{item.course_title}</td>
                                        <td className="p-3">{item.source}</td>
                                        <td className="p-3"><Badge variant={item.status === "active" ? "default" : "secondary"}>{item.status}</Badge></td>
                                        <td className="p-3">{date(item.starts_at)}</td>
                                        <td className="p-3">{date(item.expires_at)}</td>
                                        <td className="p-3">
                                            <div className="flex justify-end gap-2">
                                                {item.status !== "revoked" && <Button size="sm" variant="outline" onClick={() => void extend(item)}>Продлить</Button>}
                                                {item.status === "active" && <Button size="sm" variant="outline" onClick={() => void changeState(item, "suspend")}>Приостановить</Button>}
                                                {item.status === "suspended" && <Button size="sm" variant="outline" onClick={() => void changeState(item, "restore")}>Восстановить</Button>}
                                                {["active", "suspended"].includes(item.status) && <Button size="sm" variant="destructive" onClick={() => setRevoke(item)}>Отозвать</Button>}
                                            </div>
                                        </td>
                                    </tr>
                                ))}</tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
            <Dialog open={Boolean(revoke)} onOpenChange={(open) => { if (!open) setRevoke(null) }}>
                <DialogContent>
                    <DialogHeader><DialogTitle>Отозвать доступ</DialogTitle></DialogHeader>
                    <p className="text-sm text-muted-foreground">{revoke?.user_email} · {revoke?.course_title}</p>
                    <Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Укажите причину (обязательно)" />
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setRevoke(null)}>Отмена</Button>
                        <Button variant="destructive" disabled={reason.trim().length < 5} onClick={confirmRevoke}>Отозвать</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
