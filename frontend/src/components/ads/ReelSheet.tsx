"use client"

import { ChangeEvent, FormEvent, ReactNode, useRef, useState } from "react"
import { Check, Copy, Download, ExternalLink, FileAudio, Loader2, Mic, ScrollText, Send, Trash2, Upload } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import {
    adminCreateAdComment,
    adminDeleteAdComment,
    adminDeleteAdFile,
    adminUpdateAdMaterial,
    adminUploadAdFile,
    adsFileUrl,
    AdComment,
    AdMaterial,
    AdMaterialStatus,
} from "@/lib/api"
import { formatApiDate, formatApiDateTime } from "@/lib/format"
import { cn } from "@/lib/utils"
import {
    copyText,
    errorText,
    formatSeconds,
    formatSize,
    hookVariants,
    mainFile,
    STATUS_LABELS,
    teamFiles,
} from "@/components/ads/ad-utils"
import { STATUS_BADGE } from "@/components/ads/ReelCard"
import { Teleprompter } from "@/components/ads/Teleprompter"

const UPLOAD_ACCEPT = "audio/*,.m4a,.wav,.mp3,.aac,.ogg,.opus,.flac,video/mp4,.mov,image/jpeg,image/png,image/webp,.pdf"

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
    return (
        <section className="space-y-3 border-t px-4 py-5 sm:px-6">
            <div className="flex items-center justify-between gap-3">
                <h3 className="text-base font-semibold">{title}</h3>
                {action}
            </div>
            {children}
        </section>
    )
}

export function ReelSheet({
    campaignId,
    material,
    comments,
    canManage,
    onOpenChange,
    onChanged,
}: {
    campaignId: string
    material: AdMaterial | null
    comments: AdComment[]
    canManage: boolean
    onOpenChange: (open: boolean) => void
    onChanged: () => Promise<void>
}) {
    return (
        <Sheet open={material !== null} onOpenChange={onOpenChange}>
            <SheetContent className="w-full gap-0 overflow-y-auto p-0 sm:max-w-xl">
                {material && (
                    <ReelDetails
                        key={material.id}
                        campaignId={campaignId}
                        material={material}
                        comments={comments.filter((comment) => comment.material_id === material.id)}
                        canManage={canManage}
                        onChanged={onChanged}
                    />
                )}
            </SheetContent>
        </Sheet>
    )
}

function ReelDetails({
    campaignId,
    material,
    comments,
    canManage,
    onChanged,
}: {
    campaignId: string
    material: AdMaterial
    comments: AdComment[]
    canManage: boolean
    onChanged: () => Promise<void>
}) {
    const video = mainFile(material, "video")
    const cover = mainFile(material, "cover")
    const variants = hookVariants(material)
    const lines = (material.voiceover ?? "").split("\n").map((line) => line.trim()).filter(Boolean)
    const [prompter, setPrompter] = useState(false)
    const duration = formatSeconds(material.duration_seconds)

    return (
        <>
            <SheetHeader className="px-4 pt-5 pr-12 sm:px-6">
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                    <span className="font-semibold text-foreground">{material.code.toUpperCase()}</span>
                    {duration && <span>{duration}</span>}
                    <Badge variant={STATUS_BADGE[material.status]}>{STATUS_LABELS[material.status]}</Badge>
                </div>
                <SheetTitle className="text-xl leading-snug">{material.title}</SheetTitle>
                <SheetDescription>{material.hook ?? "Ролик кампании"}</SheetDescription>
            </SheetHeader>

            <div className="space-y-4 px-4 pb-5 sm:px-6">
                {video ? (
                    <video
                        key={video.sha256}
                        className="mx-auto aspect-[9/16] max-h-[65dvh] w-full max-w-xs rounded-xl bg-black object-contain"
                        src={adsFileUrl(video.url)}
                        poster={cover ? adsFileUrl(cover.url) : undefined}
                        controls
                        playsInline
                        preload="metadata"
                    />
                ) : (
                    <p className="rounded-lg bg-muted p-4 text-sm text-muted-foreground">Видео появится здесь, когда ролик будет смонтирован.</p>
                )}
                <div className="grid gap-2 sm:grid-cols-2">
                    {video && (
                        <Button asChild className="h-11 sm:col-span-2">
                            <a href={adsFileUrl(video.download_url)}><Download />Скачать видео · {formatSize(video.size_bytes)}</a>
                        </Button>
                    )}
                    {cover && (
                        <Button asChild variant="outline" className="h-11">
                            <a href={adsFileUrl(cover.download_url)}><Download />Скачать обложку</a>
                        </Button>
                    )}
                    {material.caption && (
                        <Button variant="outline" className="h-11" onClick={() => void copyText(material.caption ?? "", "Подпись скопирована")}>
                            <Copy />Скопировать подпись
                        </Button>
                    )}
                </div>
                {video && (
                    <p className="text-xs leading-relaxed text-muted-foreground">
                        На iPhone видео сохраняется в «Файлы»: откройте его там, нажмите «Поделиться» → «Сохранить видео», и оно появится в «Фото».
                    </p>
                )}
            </div>

            {canManage && <StatusSection material={material} onChanged={onChanged} />}

            {material.caption && (
                <Section
                    title="Подпись к посту"
                    action={<Button size="sm" variant="ghost" onClick={() => void copyText(material.caption ?? "", "Подпись скопирована")}><Copy />Копировать</Button>}
                >
                    <p className="whitespace-pre-line rounded-lg bg-muted/60 p-3 text-sm leading-relaxed">{material.caption}</p>
                    {material.link_url && (
                        <div className="space-y-1.5">
                            <p className="text-sm text-muted-foreground">Ссылка для сторис {material.utm_content && <>с меткой <code className="rounded bg-muted px-1">{material.utm_content}</code></>}</p>
                            <div className="flex gap-2">
                                <Input readOnly value={material.link_url} className="h-11 text-base sm:text-sm" onFocus={(event) => event.target.select()} />
                                <Button variant="outline" size="icon-lg" className="h-11 w-11" aria-label="Скопировать ссылку" onClick={() => void copyText(material.link_url ?? "", "Ссылка скопирована")}><Copy /></Button>
                            </div>
                        </div>
                    )}
                </Section>
            )}

            {lines.length > 0 && (
                <Section
                    title="Текст озвучки"
                    action={<Button size="sm" variant="outline" onClick={() => setPrompter(true)}><ScrollText />Суфлёр</Button>}
                >
                    <ol className="list-decimal space-y-1.5 pl-5 text-sm leading-relaxed">
                        {lines.map((line, index) => <li key={index}>{line}</li>)}
                    </ol>
                    <Teleprompter open={prompter} onOpenChange={setPrompter} title={`${material.code.toUpperCase()} · ${material.title}`} lines={lines} />
                </Section>
            )}

            {variants.length > 0 && (
                <Section title="Другие начала ролика">
                    <p className="text-sm text-muted-foreground">Тот же ролик с другим первым кадром и заголовком. Их выкладывают пробными Reels и оставляют тот, что дольше смотрят.</p>
                    <div className="grid grid-cols-2 gap-3">
                        {variants.map(({ variant, video: hookVideo, cover: hookCover }) => (
                            <figure key={variant} className="space-y-2">
                                {hookVideo && (
                                    <video
                                        className="aspect-[9/16] w-full rounded-lg bg-black object-contain"
                                        src={adsFileUrl(hookVideo.url)}
                                        poster={hookCover ? adsFileUrl(hookCover.url) : undefined}
                                        controls
                                        playsInline
                                        preload="none"
                                    />
                                )}
                                <figcaption className="text-sm"><span className="font-semibold">Вариант {variant.toUpperCase()}</span>{hookVideo?.label && <span className="block text-muted-foreground">{hookVideo.label}</span>}</figcaption>
                                {hookVideo && (
                                    <Button asChild variant="outline" className="h-11 w-full">
                                        <a href={adsFileUrl(hookVideo.download_url)}><Download />Скачать</a>
                                    </Button>
                                )}
                            </figure>
                        ))}
                    </div>
                </Section>
            )}

            <VoiceSection material={material} canManage={canManage} onChanged={onChanged} />
            <CommentsSection campaignId={campaignId} materialId={material.id} comments={comments} canManage={canManage} onChanged={onChanged} />
        </>
    )
}

function StatusSection({ material, onChanged }: { material: AdMaterial; onChanged: () => Promise<void> }) {
    const [url, setUrl] = useState(material.published_url ?? "")
    const [saving, setSaving] = useState<AdMaterialStatus | "url" | null>(null)

    const save = async (data: { status?: AdMaterialStatus; published_url?: string | null }, marker: AdMaterialStatus | "url") => {
        setSaving(marker)
        try {
            await adminUpdateAdMaterial(material.id, data)
            await onChanged()
            toast.success(marker === "url" ? "Ссылка на пост сохранена" : `Статус: ${STATUS_LABELS[marker].toLowerCase()}`)
        } catch (error) {
            toast.error("Не удалось сохранить", { description: errorText(error) })
        } finally {
            setSaving(null)
        }
    }

    return (
        <Section title="Статус">
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted p-1" role="radiogroup" aria-label="Статус ролика">
                {(["draft", "ready", "published"] as AdMaterialStatus[]).map((status) => (
                    <button
                        key={status}
                        type="button"
                        role="radio"
                        aria-checked={material.status === status}
                        disabled={saving !== null}
                        onClick={() => material.status !== status && void save({ status }, status)}
                        className={cn(
                            "flex min-h-11 items-center justify-center gap-1 rounded-md px-1 text-center text-[13px] font-medium transition-colors sm:text-sm",
                            material.status === status ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground",
                        )}
                    >
                        {saving === status ? <Loader2 className="h-4 w-4 animate-spin" /> : material.status === status && <Check className="hidden h-4 w-4 sm:block" />}
                        {status === "ready" ? "Готов" : STATUS_LABELS[status]}
                    </button>
                ))}
            </div>
            {material.status === "published" && (
                <form
                    className="space-y-1.5"
                    onSubmit={(event: FormEvent) => {
                        event.preventDefault()
                        void save({ published_url: url.trim() || null }, "url")
                    }}
                >
                    <Label htmlFor={`post-${material.id}`}>Ссылка на пост в Instagram</Label>
                    <div className="flex gap-2">
                        <Input id={`post-${material.id}`} type="url" inputMode="url" placeholder="https://www.instagram.com/reel/…" value={url} onChange={(event) => setUrl(event.target.value)} className="h-11 text-base sm:text-sm" />
                        <Button type="submit" className="h-11" disabled={saving !== null || url.trim() === (material.published_url ?? "")}>{saving === "url" ? <Loader2 className="animate-spin" /> : "Сохранить"}</Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                        Опубликован {formatApiDate(material.published_at)}
                        {material.published_url && <> · <a className="inline-flex items-center gap-1 text-primary underline underline-offset-2" href={material.published_url} target="_blank" rel="noreferrer">открыть пост<ExternalLink className="h-3 w-3" /></a></>}
                    </p>
                </form>
            )}
        </Section>
    )
}

function VoiceSection({ material, canManage, onChanged }: { material: AdMaterial; canManage: boolean; onChanged: () => Promise<void> }) {
    const files = teamFiles(material)
    const input = useRef<HTMLInputElement>(null)
    const [uploading, setUploading] = useState<string | null>(null)
    const [deleting, setDeleting] = useState<string | null>(null)

    const upload = async (event: ChangeEvent<HTMLInputElement>) => {
        const picked = Array.from(event.target.files ?? [])
        event.target.value = ""
        for (const file of picked) {
            setUploading(file.name)
            try {
                await adminUploadAdFile(material.id, file)
                toast.success(`Файл «${file.name}» загружен`)
            } catch (error) {
                toast.error(`Не удалось загрузить «${file.name}»`, { description: errorText(error) })
            }
        }
        setUploading(null)
        await onChanged()
    }

    const remove = async (fileId: string) => {
        setDeleting(fileId)
        try {
            await adminDeleteAdFile(fileId)
            await onChanged()
            toast.success("Файл удалён")
        } catch (error) {
            toast.error("Не удалось удалить файл", { description: errorText(error) })
        } finally {
            setDeleting(null)
        }
    }

    if (!canManage && files.length === 0) return null
    return (
        <Section title="Запись голоса и файлы">
            {canManage && (
                <>
                    <p className="text-sm text-muted-foreground">Запишите текст на телефон (например, в «Диктофоне») и загрузите сюда: ролик пересоберут с вашим голосом. Можно несколько дублей.</p>
                    <input ref={input} type="file" accept={UPLOAD_ACCEPT} multiple className="hidden" onChange={(event) => void upload(event)} />
                    <Button className="h-11 w-full" variant="outline" disabled={uploading !== null} onClick={() => input.current?.click()}>
                        {uploading ? <><Loader2 className="animate-spin" />Загружаю «{uploading}»…</> : <><Upload />Загрузить запись</>}
                    </Button>
                </>
            )}
            {files.length > 0 && (
                <ul className="space-y-3">
                    {files.map((file) => (
                        <li key={file.id} className="space-y-2 rounded-lg border p-3">
                            <div className="flex items-start gap-3">
                                {file.role === "voice" ? <Mic className="mt-0.5 h-4 w-4 shrink-0 text-primary" /> : <FileAudio className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />}
                                <div className="min-w-0 flex-1">
                                    <p className="break-all text-sm font-medium">{file.filename}</p>
                                    <p className="text-xs text-muted-foreground">{formatSize(file.size_bytes)} · {file.uploaded_by?.name ?? "команда"} · {formatApiDateTime(file.created_at)}</p>
                                </div>
                                <Button asChild size="icon-lg" variant="ghost" aria-label={`Скачать ${file.filename}`}><a href={adsFileUrl(file.download_url)}><Download /></a></Button>
                                {canManage && (
                                    <Button size="icon-lg" variant="ghost" aria-label={`Удалить ${file.filename}`} disabled={deleting === file.id} onClick={() => void remove(file.id)}>
                                        {deleting === file.id ? <Loader2 className="animate-spin" /> : <Trash2 />}
                                    </Button>
                                )}
                            </div>
                            {file.role === "voice" && <audio className="w-full" src={adsFileUrl(file.url)} controls preload="none" />}
                        </li>
                    ))}
                </ul>
            )}
        </Section>
    )
}

export function CommentsSection({
    campaignId,
    materialId,
    comments,
    canManage,
    onChanged,
    materialTitle,
    title = "Комментарии",
}: {
    campaignId: string
    materialId: string | null
    comments: AdComment[]
    canManage: boolean
    onChanged: () => Promise<void>
    materialTitle?: (materialId: string | null) => string | null
    title?: string
}) {
    const [body, setBody] = useState("")
    const [sending, setSending] = useState(false)

    const submit = async (event: FormEvent) => {
        event.preventDefault()
        if (!body.trim()) return
        setSending(true)
        try {
            await adminCreateAdComment(campaignId, body.trim(), materialId)
            setBody("")
            await onChanged()
        } catch (error) {
            toast.error("Комментарий не отправлен", { description: errorText(error) })
        } finally {
            setSending(false)
        }
    }

    const remove = async (commentId: string) => {
        try {
            await adminDeleteAdComment(commentId)
            await onChanged()
        } catch (error) {
            toast.error("Не удалось удалить комментарий", { description: errorText(error) })
        }
    }

    return (
        <Section title={title}>
            {comments.length === 0 && <p className="text-sm text-muted-foreground">Пока пусто. Напишите, что поправить: текст, кадр, подпись.</p>}
            <ul className="space-y-3">
                {comments.map((comment) => (
                    <li key={comment.id} className="rounded-lg bg-muted/60 p-3">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="font-medium text-foreground">{comment.author?.name ?? "Удалённый пользователь"}</span>
                            <span>{formatApiDateTime(comment.created_at)}</span>
                            {materialTitle?.(comment.material_id) && <span className="truncate">· {materialTitle(comment.material_id)}</span>}
                            {comment.is_mine && canManage && (
                                <Button size="icon-sm" variant="ghost" className="ml-auto" aria-label="Удалить комментарий" onClick={() => void remove(comment.id)}><Trash2 /></Button>
                            )}
                        </div>
                        <p className="mt-1 whitespace-pre-line text-sm leading-relaxed">{comment.body}</p>
                    </li>
                ))}
            </ul>
            {canManage && (
                <form className="space-y-2" onSubmit={(event) => void submit(event)}>
                    <Label htmlFor={`comment-${materialId ?? "campaign"}`} className="sr-only">Новый комментарий</Label>
                    <Textarea id={`comment-${materialId ?? "campaign"}`} rows={3} placeholder="Что поправить или уточнить" value={body} onChange={(event) => setBody(event.target.value)} className="text-base sm:text-sm" maxLength={5000} />
                    <Button type="submit" className="h-11 w-full sm:w-auto" disabled={sending || !body.trim()}>
                        {sending ? <Loader2 className="animate-spin" /> : <Send />}Отправить
                    </Button>
                </form>
            )}
        </Section>
    )
}
