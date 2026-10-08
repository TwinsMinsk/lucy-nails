"use client"

import { formatApiDateTime } from "@/lib/format"
import { useAdminPermission } from "@/app/admin/permissions"
import { FormEvent, Suspense, useCallback, useEffect, useRef, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
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

const date = formatApiDateTime

export default function AdminAccessPage() {
    return <Suspense fallback={<Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" />}><Access /></Suspense>
}

function Access() {
    const router = useRouter()
    const pathname = usePathname()
    const params = useSearchParams()
    const search = params.get("search") || ""
    const status = params.get("status") || "active"
    const offset = Math.max(0, Number(params.get("offset")) || 0)
    const [searchInput, setSearchInput] = useState(search)
    useEffect(() => { setSearchInput(search) }, [search])
    const navigate = (query: string, filter: string, pageOffset: number) => {
        const next = new URLSearchParams()
        if (query) next.set("search", query)
        if (filter !== "active") next.set("status", filter)
        if (pageOffset) next.set("offset", String(pageOffset))
        router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false })
    }
    const canManageAccess = useAdminPermission("access.manage")
    const [items, setItems] = useState<AdminEntitlement[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [revoke, setRevoke] = useState<AdminEntitlement | null>(null)
    const [reason, setReason] = useState("")
    const generation = useRef(0)

    const load = useCallback(async () => {
        const request = ++generation.current
        setLoading(true)
        try {
            const response = await adminGetEntitlements({
                search,
                status: status === "all" ? undefined : status,
                limit: 50,
                offset,
            })
            if (request !== generation.current) return
            setItems(response.items)
            setTotal(response.total)
        } catch (error) {
            if (request !== generation.current) return
            toast.error("Не удалось загрузить доступы", {
                description: error instanceof Error ? error.message : undefined,
            })
        } finally {
            if (request === generation.current) setLoading(false)
        }
    }, [search, status, offset])

    useEffect(() => { void load(); return () => { generation.current += 1 } }, [load])

    const submit = (event: FormEvent) => {
        event.preventDefault()
        navigate(searchInput.trim(), status, 0)
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
                        <Input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Email ученика" className="sm:w-72" />
                        <Select value={status} onValueChange={(value) => navigate(search, value, 0)}>
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
                                                {canManageAccess && item.status !== "revoked" && <Button size="sm" variant="outline" onClick={() => void extend(item)}>Продлить</Button>}
                                                {canManageAccess && item.status === "active" && <Button size="sm" variant="outline" onClick={() => void changeState(item, "suspend")}>Приостановить</Button>}
                                                {canManageAccess && item.status === "suspended" && <Button size="sm" variant="outline" onClick={() => void changeState(item, "restore")}>Восстановить</Button>}
                                                {canManageAccess && ["active", "suspended"].includes(item.status) && <Button size="sm" variant="destructive" onClick={() => setRevoke(item)}>Отозвать</Button>}
                                            </div>
                                        </td>
                                    </tr>
                                ))}</tbody>
                            </table>
                        </div>
                    )}
                    <div className="mt-4 flex items-center gap-3"><Button variant="outline" disabled={offset === 0} onClick={() => navigate(search, status, Math.max(0, offset - 50))}>Назад</Button><span className="text-sm">{total ? offset + 1 : 0}–{Math.min(offset + items.length, total)} из {total}</span><Button variant="outline" disabled={offset + 50 >= total} onClick={() => navigate(search, status, offset + 50)}>Далее</Button></div>
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
