"use client"

import { FormEvent, useCallback, useEffect, useState } from "react"
import { Award, Download, Loader2, RefreshCcw, Search, ShieldX } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
    adminGetCertificates,
    adminReissueCertificate,
    adminRevokeCertificate,
    AdminCertificate,
    certificateFileUrl,
} from "@/lib/api"

type CertificateAction = { certificate: AdminCertificate; type: "reissue" | "revoke" }

const formatDate = (value?: string | null) => value ? new Date(value).toLocaleString("ru-RU") : "—"

export default function AdminCertificatesPage() {
    const [items, setItems] = useState<AdminCertificate[]>([])
    const [total, setTotal] = useState(0)
    const [search, setSearch] = useState("")
    const [status, setStatus] = useState("all")
    const [loading, setLoading] = useState(true)
    const [action, setAction] = useState<CertificateAction | null>(null)
    const [reason, setReason] = useState("")
    const [saving, setSaving] = useState(false)

    const load = useCallback(async (query: string, statusFilter: string) => {
        setLoading(true)
        try {
            const response = await adminGetCertificates({
                search: query.trim() || undefined,
                status: statusFilter === "all" ? undefined : statusFilter,
                limit: 200,
            })
            setItems(response.items)
            setTotal(response.total)
        } catch (error) {
            toast.error("Не удалось загрузить сертификаты", {
                description: error instanceof Error ? error.message : undefined,
            })
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { void load("", "all") }, [load])

    const submitSearch = (event: FormEvent) => {
        event.preventDefault()
        void load(search, status)
    }

    const changeStatus = (value: string) => {
        setStatus(value)
        void load(search, value)
    }

    const openAction = (certificate: AdminCertificate, type: CertificateAction["type"]) => {
        setAction({ certificate, type })
        setReason("")
    }

    const confirmAction = async () => {
        if (!action || reason.trim().length < 5) return
        setSaving(true)
        try {
            if (action.type === "reissue") {
                await adminReissueCertificate(action.certificate.id, reason.trim())
                toast.success("Письмо с сертификатом поставлено в очередь")
            } else {
                await adminRevokeCertificate(action.certificate.id, reason.trim())
                toast.success("Сертификат отозван")
            }
            setAction(null)
            await load(search, status)
        } catch (error) {
            toast.error("Операция не выполнена", {
                description: error instanceof Error ? error.message : undefined,
            })
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
            <div>
                <h1 className="flex items-center gap-2 text-3xl font-bold"><Award className="h-7 w-7" />Сертификаты</h1>
                <p className="mt-1 text-muted-foreground">Реестр, скачивание, повторная отправка и отзыв с обязательной причиной.</p>
            </div>

            <Card>
                <CardHeader className="gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <CardTitle>Выдано: {total}</CardTitle>
                    <div className="flex flex-col gap-2 sm:flex-row">
                        <form className="flex gap-2" onSubmit={submitSearch}>
                            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Email, имя или номер" className="sm:w-72" />
                            <Button type="submit" variant="outline" aria-label="Найти"><Search className="h-4 w-4" /></Button>
                        </form>
                        <Select value={status} onValueChange={changeStatus}>
                            <SelectTrigger className="sm:w-44"><SelectValue /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Все статусы</SelectItem>
                                <SelectItem value="active">Действующие</SelectItem>
                                <SelectItem value="revoked">Отозванные</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </CardHeader>
                <CardContent>
                    {loading ? <Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" /> : items.length === 0 ? (
                        <p className="py-12 text-center text-muted-foreground">Сертификаты не найдены.</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">Ученик</th><th className="p-3">Курс</th><th className="p-3">Номер</th><th className="p-3">Выдан</th><th className="p-3">Статус</th><th className="p-3 text-right">Действия</th></tr></thead>
                                <tbody>{items.map((certificate) => (
                                    <tr key={certificate.id} className="border-b align-top">
                                        <td className="p-3"><p className="font-medium">{certificate.student_name}</p><p className="text-xs text-muted-foreground">{certificate.student_email}</p></td>
                                        <td className="p-3">{certificate.course_title}</td>
                                        <td className="p-3 font-mono text-xs">{certificate.certificate_number}</td>
                                        <td className="p-3">{formatDate(certificate.issued_at)}</td>
                                        <td className="p-3"><Badge variant={certificate.status === "revoked" ? "destructive" : "outline"}>{certificate.status === "revoked" ? "Отозван" : "Действует"}</Badge>{certificate.revoke_reason && <p className="mt-1 max-w-52 text-xs text-destructive">{certificate.revoke_reason}</p>}</td>
                                        <td className="p-3"><div className="flex justify-end gap-2">
                                            {certificate.status === "active" && <Button size="sm" variant="outline" asChild><a href={certificateFileUrl(certificate.certificate_number, "pdf")} target="_blank" rel="noreferrer"><Download className="mr-2 h-3 w-3" />PDF</a></Button>}
                                            {certificate.status === "active" && <Button size="sm" variant="outline" onClick={() => openAction(certificate, "reissue")}><RefreshCcw className="mr-2 h-3 w-3" />Отправить</Button>}
                                            {certificate.status === "active" && <Button size="sm" variant="destructive" onClick={() => openAction(certificate, "revoke")}><ShieldX className="mr-2 h-3 w-3" />Отозвать</Button>}
                                        </div></td>
                                    </tr>
                                ))}</tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog open={Boolean(action)} onOpenChange={(open) => { if (!open) setAction(null) }}>
                <DialogContent>
                    <DialogHeader><DialogTitle>{action?.type === "revoke" ? "Отозвать сертификат" : "Повторно отправить сертификат"}</DialogTitle></DialogHeader>
                    <p className="text-sm text-muted-foreground">{action?.certificate.student_email} · {action?.certificate.certificate_number}</p>
                    <Textarea value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Обязательная причина (не менее 5 символов)" />
                    <DialogFooter><Button variant="outline" onClick={() => setAction(null)}>Отмена</Button><Button variant={action?.type === "revoke" ? "destructive" : "default"} disabled={saving || reason.trim().length < 5} onClick={confirmAction}>{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{action?.type === "revoke" ? "Отозвать" : "Отправить"}</Button></DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    )
}
