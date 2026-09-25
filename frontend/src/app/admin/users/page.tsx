"use client"

import { FormEvent, useEffect, useState } from "react"
import { KeyRound, Loader2, Mail, Search, UserPlus, UserRound } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import {
    adminCreateStudent,
    adminCreateStudentNote,
    adminGetCourses,
    adminGetStudent,
    adminGetStudents,
    adminGrantAccess,
    adminSendStudentLoginLink,
    adminUpdateStudentTags,
    AdminCourseFullResponse,
    AdminStudentDetail,
    AdminStudentListItem,
} from "@/lib/api"

const date = (value?: string | null) => value ? new Date(value).toLocaleString("ru-RU") : "—"
const errorText = (error: unknown) => error instanceof Error ? error.message : undefined

const emptyStudentForm = { email: "", full_name: "", phone: "", course_id: "", access_days: 30, reason: "" }

export default function AdminUsersPage() {
    const [items, setItems] = useState<AdminStudentListItem[]>([])
    const [total, setTotal] = useState(0)
    const [search, setSearch] = useState("")
    const [loading, setLoading] = useState(true)
    const [selected, setSelected] = useState<AdminStudentDetail | null>(null)
    const [courses, setCourses] = useState<AdminCourseFullResponse[]>([])
    const [note, setNote] = useState("")
    const [tags, setTags] = useState("")
    const [tagReason, setTagReason] = useState("")
    const [grantCourse, setGrantCourse] = useState("")
    const [grantDays, setGrantDays] = useState(30)
    const [grantReason, setGrantReason] = useState("")
    const [saving, setSaving] = useState(false)
    const [createOpen, setCreateOpen] = useState(false)
    const [studentForm, setStudentForm] = useState(emptyStudentForm)
    const canCreateStudent = Boolean(studentForm.email.trim())
        && Boolean(studentForm.course_id)
        && Number.isInteger(studentForm.access_days)
        && studentForm.access_days >= 1
        && studentForm.access_days <= 3650
        && studentForm.reason.trim().length >= 5

    const load = async (query = search) => {
        setLoading(true)
        try {
            const response = await adminGetStudents({ search: query, limit: 100 })
            setItems(response.items)
            setTotal(response.total)
        } catch (error) {
            toast.error("Не удалось загрузить учеников", { description: error instanceof Error ? error.message : undefined })
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        void Promise.all([load(""), adminGetCourses().then(setCourses)])
        // Initial load only; search is submitted explicitly.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    const openStudent = async (id: string) => {
        try {
            const detail = await adminGetStudent(id)
            setSelected(detail)
            setTags(detail.tags.join(", "))
        } catch (error) {
            toast.error("Не удалось открыть карточку", { description: error instanceof Error ? error.message : undefined })
        }
    }

    const refreshSelected = async () => {
        if (selected) setSelected(await adminGetStudent(selected.id))
    }

    const saveNote = async () => {
        if (!selected || note.trim().length < 2) return
        setSaving(true)
        try {
            await adminCreateStudentNote(selected.id, note.trim())
            setNote("")
            await refreshSelected()
            toast.success("Заметка добавлена")
        } finally { setSaving(false) }
    }

    const saveTags = async () => {
        if (!selected || tagReason.trim().length < 5) return
        setSaving(true)
        try {
            await adminUpdateStudentTags(selected.id, tags.split(",").map((item) => item.trim()).filter(Boolean), tagReason.trim())
            setTagReason("")
            await refreshSelected()
            toast.success("Теги обновлены")
        } finally { setSaving(false) }
    }

    const grant = async () => {
        if (!selected || !grantCourse || grantReason.trim().length < 5) return
        setSaving(true)
        try {
            await adminGrantAccess(selected.id, grantCourse, "self", grantReason.trim(), grantDays)
            setGrantReason("")
            await Promise.all([refreshSelected(), load()])
            toast.success("Доступ выдан")
        } finally { setSaving(false) }
    }

    const createStudent = async (event: FormEvent) => {
        event.preventDefault()
        if (!canCreateStudent) return
        setSaving(true)
        try {
            await adminCreateStudent({
                email: studentForm.email.trim(),
                full_name: studentForm.full_name.trim() || undefined,
                phone: studentForm.phone.trim() || undefined,
                course_id: studentForm.course_id,
                access_days: studentForm.access_days,
                reason: studentForm.reason.trim(),
            })
            setCreateOpen(false)
            setStudentForm(emptyStudentForm)
            await load()
            toast.success("Ученик добавлен, письмо со ссылкой отправлено")
        } catch (error) {
            toast.error("Не удалось добавить ученика", { description: errorText(error) })
        } finally { setSaving(false) }
    }

    const sendLoginLink = async () => {
        if (!selected) return
        if (!window.confirm(`Отправить на ${selected.email} ссылку для входа? По ней ученик сможет задать новый пароль.`)) return
        setSaving(true)
        try {
            await adminSendStudentLoginLink(selected.id)
            toast.success("Ссылка для входа отправлена", { description: selected.email })
        } catch (error) {
            toast.error("Не удалось отправить ссылку", { description: errorText(error) })
        } finally { setSaving(false) }
    }

    const submitSearch = (event: FormEvent) => { event.preventDefault(); void load() }

    return (
        <div className="container max-w-7xl space-y-6 px-4 py-8 md:px-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Ученики</h1>
                    <p className="mt-1 text-muted-foreground">Серверный поиск, доступы, прогресс, сертификаты, заметки и теги.</p>
                </div>
                <Button className="gap-2" onClick={() => setCreateOpen(true)}><UserPlus className="h-4 w-4" />Добавить ученика</Button>
            </div>
            <Card>
                <CardHeader className="gap-4 md:flex-row md:items-center md:justify-between">
                    <CardTitle>{total} учеников</CardTitle>
                    <form className="flex w-full gap-2 md:w-96" onSubmit={submitSearch}>
                        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Email, имя или телефон" />
                        <Button type="submit" variant="outline"><Search className="h-4 w-4" /></Button>
                    </form>
                </CardHeader>
                <CardContent>
                    {loading ? <Loader2 className="mx-auto my-12 h-7 w-7 animate-spin" /> : (
                        <div className="divide-y rounded-lg border">
                            {items.map((user) => (
                                <button key={user.id} onClick={() => openStudent(user.id)} className="flex w-full items-center gap-4 p-4 text-left hover:bg-muted/60">
                                    <UserRound className="h-5 w-5 text-muted-foreground" />
                                    <div className="min-w-0 flex-1">
                                        <p className="truncate font-medium">{user.full_name || user.email}</p>
                                        <p className="truncate text-sm text-muted-foreground">{user.email}{user.phone ? ` · ${user.phone}` : ""}</p>
                                    </div>
                                    <Badge variant={user.active_entitlements ? "default" : "secondary"}>{user.active_entitlements} доступов</Badge>
                                    <span className="hidden text-xs text-muted-foreground sm:block">{date(user.created_at)}</span>
                                </button>
                            ))}
                            {!items.length && <p className="p-10 text-center text-muted-foreground">Ничего не найдено</p>}
                        </div>
                    )}
                </CardContent>
            </Card>

            <Dialog open={Boolean(selected)} onOpenChange={(open) => { if (!open) setSelected(null) }}>
                <DialogContent className="max-h-[92vh] max-w-4xl overflow-y-auto">
                    {selected && <>
                        <DialogHeader>
                            <DialogTitle>{selected.full_name || selected.email}</DialogTitle>
                            <DialogDescription>{selected.email} · зарегистрирован {date(selected.created_at)}</DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-5 md:grid-cols-2">
                            <section className="space-y-3 rounded-lg border p-4">
                                <h3 className="font-semibold">Прогресс</h3>
                                <p className="text-sm">Завершено уроков: <b>{selected.completed_lessons}</b> из {selected.tracked_lessons} начатых</p>
                                <p className="text-sm text-muted-foreground">Последняя активность: {date(selected.last_activity_at)}</p>
                                <h3 className="pt-2 font-semibold">Доступы</h3>
                                {selected.entitlements.map((item) => <div key={item.id} className="rounded-md bg-muted p-3 text-sm">
                                    <div className="flex justify-between"><b>{item.course_title}</b><Badge variant="outline">{item.status}</Badge></div>
                                    <p className="mt-1 text-muted-foreground">до {date(item.expires_at)} · {item.source}</p>
                                </div>)}
                                {!selected.entitlements.length && <p className="text-sm text-muted-foreground">Доступов нет</p>}
                            </section>
                            <section className="space-y-3 rounded-lg border p-4">
                                <h3 className="flex items-center gap-2 font-semibold"><KeyRound className="h-4 w-4" />Выдать доступ</h3>
                                <Select value={grantCourse} onValueChange={setGrantCourse}><SelectTrigger><SelectValue placeholder="Выберите курс" /></SelectTrigger><SelectContent>{courses.map((course) => <SelectItem key={course.id} value={course.id}>{course.title}</SelectItem>)}</SelectContent></Select>
                                <div><Label>Дней</Label><Input type="number" min={1} max={3650} value={grantDays} onChange={(event) => setGrantDays(Number(event.target.value))} /></div>
                                <Textarea value={grantReason} onChange={(event) => setGrantReason(event.target.value)} placeholder="Обязательная причина" />
                                <Button className="w-full" disabled={saving || !grantCourse || grantReason.trim().length < 5} onClick={grant}>Выдать доступ</Button>
                            </section>
                            <section className="space-y-3 rounded-lg border p-4">
                                <h3 className="font-semibold">Заметки</h3>
                                <Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Внутренняя заметка о студенте" />
                                <Button variant="outline" disabled={saving || note.trim().length < 2} onClick={saveNote}>Добавить заметку</Button>
                                <div className="max-h-44 space-y-2 overflow-y-auto">{selected.notes.map((item) => <div key={item.id} className="rounded-md bg-muted p-2 text-sm"><p>{item.body}</p><p className="mt-1 text-xs text-muted-foreground">{date(item.created_at)}</p></div>)}</div>
                            </section>
                            <section className="space-y-3 rounded-lg border p-4">
                                <h3 className="font-semibold">Теги</h3>
                                <Input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="vip, needs-follow-up" />
                                <Textarea value={tagReason} onChange={(event) => setTagReason(event.target.value)} placeholder="Причина изменения тегов" />
                                <Button variant="outline" disabled={saving || tagReason.trim().length < 5} onClick={saveTags}>Сохранить теги</Button>
                                <div className="flex flex-wrap gap-2">{selected.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}</div>
                            </section>
                        </div>
                        <DialogFooter className="gap-2">
                            <Button variant="outline" className="gap-2" disabled={saving} onClick={sendLoginLink}><Mail className="h-4 w-4" />Отправить ссылку для входа</Button>
                            <Button variant="outline" onClick={() => setSelected(null)}>Закрыть</Button>
                        </DialogFooter>
                    </>}
                </DialogContent>
            </Dialog>

            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                <DialogContent className="max-w-lg">
                    <form className="space-y-4" onSubmit={createStudent}>
                        <DialogHeader>
                            <DialogTitle>Добавить ученика</DialogTitle>
                            <DialogDescription>Для ручной продажи или подарка. Если аккаунта ещё нет, он будет создан, а на почту уйдёт ссылка для установки пароля.</DialogDescription>
                        </DialogHeader>
                        <div className="space-y-1.5">
                            <Label htmlFor="student-email">Email *</Label>
                            <Input id="student-email" type="email" required value={studentForm.email} onChange={(event) => setStudentForm({ ...studentForm, email: event.target.value })} placeholder="student@example.com" />
                        </div>
                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-1.5">
                                <Label htmlFor="student-name">Имя</Label>
                                <Input id="student-name" value={studentForm.full_name} onChange={(event) => setStudentForm({ ...studentForm, full_name: event.target.value })} />
                            </div>
                            <div className="space-y-1.5">
                                <Label htmlFor="student-phone">Телефон</Label>
                                <Input id="student-phone" type="tel" value={studentForm.phone} onChange={(event) => setStudentForm({ ...studentForm, phone: event.target.value })} />
                            </div>
                        </div>
                        <div className="space-y-1.5">
                            <Label>Курс *</Label>
                            <Select value={studentForm.course_id} onValueChange={(value) => setStudentForm({ ...studentForm, course_id: value })}>
                                <SelectTrigger><SelectValue placeholder="Выберите курс" /></SelectTrigger>
                                <SelectContent>{courses.map((course) => <SelectItem key={course.id} value={course.id}>{course.title}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="student-days">Дней доступа</Label>
                            <Input id="student-days" type="number" min={1} max={3650} value={studentForm.access_days} onChange={(event) => setStudentForm({ ...studentForm, access_days: Number(event.target.value) })} />
                        </div>
                        <div className="space-y-1.5">
                            <Label htmlFor="student-reason">Причина *</Label>
                            <Textarea id="student-reason" value={studentForm.reason} onChange={(event) => setStudentForm({ ...studentForm, reason: event.target.value })} placeholder="Например: оплата переводом, подарок" />
                        </div>
                        <DialogFooter>
                            <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>Отмена</Button>
                            <Button type="submit" disabled={saving || !canCreateStudent}>
                                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Добавить
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        </div>
    )
}
