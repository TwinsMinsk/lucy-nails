"use client"

import { useEffect, useState } from "react"
import { CheckCircle2, Loader2, ShieldAlert, XCircle } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import {
    adminGetAuditLogs,
    adminGetRoles,
    adminGetSystemStatus,
    adminGetTeamUsers,
    adminSetCheckoutEnabled,
    adminUpdateTeamRoles,
    AdminAuditLog,
    AdminRole,
    AdminSystemStatus,
    AdminTeamUser,
} from "@/lib/api"

const date = (value?: string | null) => value ? new Date(value).toLocaleString("ru-RU") : "—"

export default function AdminSystemPage() {
    const [status, setStatus] = useState<AdminSystemStatus | null>(null)
    const [roles, setRoles] = useState<AdminRole[]>([])
    const [team, setTeam] = useState<AdminTeamUser[]>([])
    const [audit, setAudit] = useState<AdminAuditLog[]>([])
    const [loading, setLoading] = useState(true)
    const [editing, setEditing] = useState<AdminTeamUser | null>(null)
    const [selectedRoles, setSelectedRoles] = useState<string[]>([])
    const [reason, setReason] = useState("")
    const [switchingCheckout, setSwitchingCheckout] = useState(false)

    const load = async () => {
        setLoading(true)
        const settled = await Promise.allSettled([
            adminGetSystemStatus(), adminGetRoles(), adminGetTeamUsers(), adminGetAuditLogs({ limit: 100 }),
        ])
        if (settled[0].status === "fulfilled") setStatus(settled[0].value)
        if (settled[1].status === "fulfilled") setRoles(settled[1].value)
        if (settled[2].status === "fulfilled") setTeam(settled[2].value)
        if (settled[3].status === "fulfilled") setAudit(settled[3].value)
        if (settled.some((item) => item.status === "rejected")) toast.warning("Часть системных данных скрыта вашими правами")
        setLoading(false)
    }
    useEffect(() => { void load() }, [])
    const openRoles = (user: AdminTeamUser) => { setEditing(user); setSelectedRoles(user.roles); setReason("") }
    const toggleRole = (role: string) => setSelectedRoles((current) => current.includes(role) ? current.filter((item) => item !== role) : [...current, role])
    const saveRoles = async () => {
        if (!editing || reason.trim().length < 5) return
        await adminUpdateTeamRoles(editing.id, selectedRoles, reason.trim())
        toast.success("Роли обновлены"); setEditing(null); await load()
    }
    const toggleCheckout = async () => {
        if (!status) return
        const next = !status.checkout_enabled
        const operation = next ? "включения" : "экстренного отключения"
        const explanation = window.prompt(`Укажите причину ${operation} checkout (минимум 5 символов)`)
        if (!explanation || explanation.trim().length < 5) return
        if (!next && !window.confirm("Новые оплаты будут немедленно заблокированы. Продолжить?")) return
        setSwitchingCheckout(true)
        try {
            await adminSetCheckoutEnabled(next, explanation.trim())
            toast.success(next ? "Checkout включён" : "Checkout экстренно отключён")
            await load()
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Не удалось изменить checkout")
        } finally {
            setSwitchingCheckout(false)
        }
    }

    if (loading) return <div className="flex min-h-[50vh] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin" /></div>
    return (
        <div className="container max-w-7xl space-y-7 px-4 py-8 md:px-6">
            <div><h1 className="flex items-center gap-2 text-3xl font-bold"><ShieldAlert className="h-7 w-7" />Аудит и система</h1><p className="mt-1 text-muted-foreground">Роли команды, MFA, несекретное состояние интеграций и неизменяемый журнал действий.</p></div>
            {status && <Card className={status.checkout_enabled ? "border-green-300" : "border-destructive"}><CardHeader><CardTitle>Экстренное управление оплатами</CardTitle></CardHeader><CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><p className="text-sm text-muted-foreground">Переключатель действует сразу, сохраняется в БД и не требует deploy. Webhook продолжает принимать уже начатые платежи.</p><Button variant={status.checkout_enabled ? "destructive" : "default"} disabled={switchingCheckout} onClick={toggleCheckout}>{switchingCheckout && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{status.checkout_enabled ? "Отключить checkout" : "Включить checkout"}</Button></CardContent></Card>}
            {status && <Card><CardHeader><CardTitle>Состояние production-контура</CardTitle></CardHeader><CardContent><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{Object.entries(status.integrations).map(([name, configured]) => <div key={name} className="flex items-center justify-between rounded-lg border p-3 text-sm"><span className="capitalize">{name}</span>{configured ? <CheckCircle2 className="h-5 w-5 text-green-600" /> : <XCircle className="h-5 w-5 text-destructive" />}</div>)}</div><div className="mt-4 flex flex-wrap gap-3 text-sm"><Badge variant={status.checkout_enabled ? "default" : "destructive"}>Checkout {status.checkout_enabled ? "включён" : "выключен"}</Badge><Badge variant="outline">Среда: {status.environment}</Badge><Badge variant="outline">Outbox pending: {status.outbox_pending}</Badge><Badge variant={status.outbox_dead_letter ? "destructive" : "outline"}>Dead letter: {status.outbox_dead_letter}</Badge><span className="text-muted-foreground">Последний webhook: {date(status.last_payment_event_at)}</span></div></CardContent></Card>}
            {team.length > 0 && <Card><CardHeader><CardTitle>Команда</CardTitle></CardHeader><CardContent className="space-y-2">{team.map((user) => <div key={user.id} className="flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center"><div className="min-w-0 flex-1"><p className="truncate font-medium">{user.full_name || user.email}</p><p className="text-sm text-muted-foreground">{user.email}</p></div><div className="flex flex-wrap gap-1">{user.roles.map((role) => <Badge key={role} variant="secondary">{role}</Badge>)}</div><Badge variant={user.mfa_enabled ? "default" : "destructive"}>MFA {user.mfa_enabled ? "включена" : "не настроена"}</Badge><span className="text-sm text-muted-foreground">Сессий: {user.active_sessions}</span><Button size="sm" variant="outline" onClick={() => openRoles(user)}>Роли</Button></div>)}</CardContent></Card>}
            <Card><CardHeader><CardTitle>Журнал действий</CardTitle></CardHeader><CardContent><div className="max-h-[680px] overflow-auto"><table className="w-full text-sm"><thead><tr className="sticky top-0 border-b bg-background text-left text-muted-foreground"><th className="p-3">Время</th><th className="p-3">Действие</th><th className="p-3">Объект</th><th className="p-3">Причина</th><th className="p-3">Correlation ID</th></tr></thead><tbody>{audit.map((item) => <tr key={item.id} className="border-b align-top"><td className="p-3">{date(item.created_at)}</td><td className="p-3 font-medium">{item.action}</td><td className="p-3">{item.object_type} {item.object_id?.slice(0, 8)}</td><td className="max-w-sm p-3">{item.reason || "—"}</td><td className="p-3 font-mono text-xs">{item.correlation_id}</td></tr>)}</tbody></table></div></CardContent></Card>
            <Dialog open={Boolean(editing)} onOpenChange={(open) => { if (!open) setEditing(null) }}><DialogContent><DialogHeader><DialogTitle>Роли: {editing?.email}</DialogTitle></DialogHeader><div className="space-y-2">{roles.map((role) => <label key={role.name} className="flex cursor-pointer items-start gap-3 rounded-lg border p-3"><input type="checkbox" checked={selectedRoles.includes(role.name)} onChange={() => toggleRole(role.name)} className="mt-1" /><span><b>{role.name}</b><span className="block text-xs text-muted-foreground">{role.description}</span></span></label>)}</div><Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Причина изменения ролей" /><DialogFooter><Button variant="outline" onClick={() => setEditing(null)}>Отмена</Button><Button disabled={reason.trim().length < 5} onClick={saveRoles}>Сохранить</Button></DialogFooter></DialogContent></Dialog>
        </div>
    )
}
