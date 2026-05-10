"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { ArrowDown, ArrowUp, Loader2, Pencil, Plus, Save, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

import {
    AdminCourseFullResponse,
    GalleryItem,
    GalleryItemCreate,
    HeroStat,
    LandingHeroPayload,
    LandingModulePayload,
    LandingModuleUpdate,
    adminCreateGalleryItem,
    adminDeleteGalleryItem,
    adminGetCourseLandingHero,
    adminGetCourseLandingModules,
    adminGetCourses,
    adminGetGallery,
    adminReorderGallery,
    adminUpdateCourseLandingHero,
    adminUpdateGalleryItem,
    adminUpdateModuleLanding,
    adminUploadFile,
} from "@/lib/api";
import {
    galleryItems as staticGalleryItems,
    landingCourse as staticLandingCourse,
    programModules as staticProgramModules,
} from "@/lib/landing/course-content";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";

const HERO_STAT_SLOTS = 3;
const BENEFIT_SLOTS = 3;

function emptyHero(): LandingHeroPayload {
    return {
        landing_title: "",
        landing_subtitle: "",
        landing_description: "",
        landing_audience: "",
        landing_support_note: "",
        landing_hero_stats: Array.from({ length: HERO_STAT_SLOTS }, () => ({ label: "", value: "" })),
        landing_benefits: Array.from({ length: BENEFIT_SLOTS }, () => ""),
        landing_instructor_image_url: "",
    };
}

function nullIfBlank(value: string | null | undefined): string | null {
    if (value == null) return null;
    const trimmed = value.trim();
    return trimmed.length === 0 ? null : trimmed;
}

function arrayOrNull<T>(items: T[], isEmpty: (item: T) => boolean): T[] | null {
    const filtered = items.filter((item) => !isEmpty(item));
    return filtered.length === 0 ? null : filtered;
}

function parseLines(value: string): string[] {
    return value
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
}

function joinLines(items: string[] | null | undefined): string {
    if (!items) return "";
    return items.join("\n");
}

export default function AdminLandingPage() {
    const [courses, setCourses] = useState<AdminCourseFullResponse[]>([]);
    const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);
    const [isInitialLoading, setIsInitialLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const list = await adminGetCourses();
                setCourses(list);
                const defaultCourse = list.find((c) => c.is_published) ?? list[0];
                if (defaultCourse) {
                    setSelectedCourseId(defaultCourse.id);
                }
            } catch (err) {
                const message = err instanceof Error ? err.message : "Не удалось загрузить курсы";
                toast.error("Ошибка", { description: message });
            } finally {
                setIsInitialLoading(false);
            }
        };
        load();
    }, []);

    if (isInitialLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-8 max-w-6xl mx-auto">
            <div>
                <h1 className="text-3xl font-bold text-text-primary">Лендинг</h1>
                <p className="text-text-secondary mt-1">
                    Тексты главного блока, программа курса и галерея работ. Пустые поля
                    подменяются значениями из <code>course-content.ts</code>.
                </p>
            </div>

            {courses.length > 1 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Курс</CardTitle>
                        <CardDescription>Выберите курс для редактирования hero и программы.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-2 flex-wrap">
                            {courses.map((c) => (
                                <Button
                                    key={c.id}
                                    variant={c.id === selectedCourseId ? "default" : "outline"}
                                    onClick={() => setSelectedCourseId(c.id)}
                                >
                                    {c.title}
                                </Button>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {selectedCourseId && (
                <>
                    <HeroSection courseId={selectedCourseId} />
                    <ProgramSection courseId={selectedCourseId} />
                </>
            )}

            <GallerySection />
        </div>
    );
}

// =====================================================================
// HERO
// =====================================================================

function HeroSection({ courseId }: { courseId: string }) {
    const [hero, setHero] = useState<LandingHeroPayload>(emptyHero());
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        const load = async () => {
            setIsLoading(true);
            try {
                const data = await adminGetCourseLandingHero(courseId);
                setHero({
                    landing_title: data.landing_title ?? staticLandingCourse.title,
                    landing_subtitle: data.landing_subtitle ?? staticLandingCourse.subtitle,
                    landing_description: data.landing_description ?? staticLandingCourse.description,
                    landing_audience: data.landing_audience ?? staticLandingCourse.audience,
                    landing_support_note: data.landing_support_note ?? staticLandingCourse.supportNote,
                    landing_hero_stats:
                        data.landing_hero_stats && data.landing_hero_stats.length > 0
                            ? padHeroStats(data.landing_hero_stats)
                            : padHeroStats(staticLandingCourse.heroStats),
                    landing_benefits:
                        data.landing_benefits && data.landing_benefits.length > 0
                            ? padBenefits(data.landing_benefits)
                            : padBenefits(staticLandingCourse.benefits),
                    landing_instructor_image_url: data.landing_instructor_image_url ?? "",
                });
            } catch (err) {
                const message = err instanceof Error ? err.message : "Не удалось загрузить hero";
                toast.error("Ошибка", { description: message });
            } finally {
                setIsLoading(false);
            }
        };
        load();
    }, [courseId]);

    const handleImageUpload = async (file: File) => {
        setIsUploading(true);
        try {
            const result = await adminUploadFile(file);
            setHero((prev) => ({ ...prev, landing_instructor_image_url: result.url }));
            toast.success("Фото загружено");
        } catch (err) {
            const message = err instanceof Error ? err.message : "Ошибка загрузки";
            toast.error("Ошибка", { description: message });
        } finally {
            setIsUploading(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const payload: LandingHeroPayload = {
                landing_title: nullIfBlank(hero.landing_title),
                landing_subtitle: nullIfBlank(hero.landing_subtitle),
                landing_description: nullIfBlank(hero.landing_description),
                landing_audience: nullIfBlank(hero.landing_audience),
                landing_support_note: nullIfBlank(hero.landing_support_note),
                landing_hero_stats: arrayOrNull(
                    (hero.landing_hero_stats ?? []).map((s) => ({
                        label: s.label.trim(),
                        value: s.value.trim(),
                    })),
                    (s) => !s.label && !s.value,
                ),
                landing_benefits: arrayOrNull(
                    (hero.landing_benefits ?? []).map((b) => b.trim()),
                    (b) => b.length === 0,
                ),
                landing_instructor_image_url: nullIfBlank(hero.landing_instructor_image_url),
            };
            await adminUpdateCourseLandingHero(courseId, payload);
            toast.success("Hero сохранён");
        } catch (err) {
            const message = err instanceof Error ? err.message : "Ошибка сохранения";
            toast.error("Ошибка", { description: message });
        } finally {
            setIsSaving(false);
        }
    };

    if (isLoading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center min-h-[200px]">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Главный блок (Hero)</CardTitle>
                <CardDescription>Заголовок, подзаголовок, фото мастера, статистика, преимущества.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div>
                    <Label htmlFor="hero-title">Заголовок</Label>
                    <Input
                        id="hero-title"
                        value={hero.landing_title ?? ""}
                        onChange={(e) => setHero({ ...hero, landing_title: e.target.value })}
                        placeholder="Оставьте пустым → из course-content.ts"
                    />
                </div>
                <div>
                    <Label htmlFor="hero-subtitle">Подзаголовок</Label>
                    <Input
                        id="hero-subtitle"
                        value={hero.landing_subtitle ?? ""}
                        onChange={(e) => setHero({ ...hero, landing_subtitle: e.target.value })}
                    />
                </div>
                <div>
                    <Label htmlFor="hero-support">Note о поддержке (мелкая строка под кнопкой)</Label>
                    <Input
                        id="hero-support"
                        value={hero.landing_support_note ?? ""}
                        onChange={(e) => setHero({ ...hero, landing_support_note: e.target.value })}
                    />
                </div>

                <div>
                    <Label>Статистика hero (3 карточки)</Label>
                    <div className="space-y-2">
                        {(hero.landing_hero_stats ?? []).map((stat, idx) => (
                            <div key={idx} className="grid grid-cols-2 gap-2">
                                <Input
                                    placeholder="Подпись"
                                    value={stat.label}
                                    onChange={(e) => {
                                        const next = [...(hero.landing_hero_stats ?? [])];
                                        next[idx] = { ...stat, label: e.target.value };
                                        setHero({ ...hero, landing_hero_stats: next });
                                    }}
                                />
                                <Input
                                    placeholder="Значение"
                                    value={stat.value}
                                    onChange={(e) => {
                                        const next = [...(hero.landing_hero_stats ?? [])];
                                        next[idx] = { ...stat, value: e.target.value };
                                        setHero({ ...hero, landing_hero_stats: next });
                                    }}
                                />
                            </div>
                        ))}
                    </div>
                </div>

                <div>
                    <Label>Преимущества (3 пункта)</Label>
                    <div className="space-y-2">
                        {(hero.landing_benefits ?? []).map((benefit, idx) => (
                            <Input
                                key={idx}
                                placeholder={`Преимущество ${idx + 1}`}
                                value={benefit}
                                onChange={(e) => {
                                    const next = [...(hero.landing_benefits ?? [])];
                                    next[idx] = e.target.value;
                                    setHero({ ...hero, landing_benefits: next });
                                }}
                            />
                        ))}
                    </div>
                </div>

                <div>
                    <Label htmlFor="hero-image">Фото мастера</Label>
                    <div className="space-y-2">
                        <Input
                            id="hero-image"
                            value={hero.landing_instructor_image_url ?? ""}
                            onChange={(e) =>
                                setHero({ ...hero, landing_instructor_image_url: e.target.value })
                            }
                            placeholder="URL или загрузите файл ниже"
                        />
                        <div className="flex items-center gap-2">
                            <input
                                type="file"
                                accept="image/*"
                                disabled={isUploading}
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) handleImageUpload(file);
                                    e.target.value = "";
                                }}
                            />
                            {isUploading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
                        </div>
                        {hero.landing_instructor_image_url && (
                            <div className="relative w-32 h-32 rounded-lg overflow-hidden border border-border">
                                <Image
                                    src={hero.landing_instructor_image_url}
                                    alt="Preview"
                                    fill
                                    sizes="128px"
                                    className="object-cover"
                                />
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex justify-end">
                    <Button onClick={handleSave} disabled={isSaving}>
                        {isSaving ? (
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        ) : (
                            <Save className="w-4 h-4 mr-2" />
                        )}
                        Сохранить hero
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}

function padHeroStats(items: HeroStat[]): HeroStat[] {
    const result = items.slice(0, HERO_STAT_SLOTS);
    while (result.length < HERO_STAT_SLOTS) result.push({ label: "", value: "" });
    return result;
}

function padBenefits(items: string[]): string[] {
    const result = items.slice(0, BENEFIT_SLOTS);
    while (result.length < BENEFIT_SLOTS) result.push("");
    return result;
}

// =====================================================================
// PROGRAM
// =====================================================================

function ProgramSection({ courseId }: { courseId: string }) {
    const [modules, setModules] = useState<LandingModulePayload[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [savingId, setSavingId] = useState<string | null>(null);

    useEffect(() => {
        const load = async () => {
            setIsLoading(true);
            try {
                const data = await adminGetCourseLandingModules(courseId);
                const staticByTitle = new Map(staticProgramModules.map((m) => [m.title, m] as const));
                const merged = data.map((mod) => {
                    const fb = staticByTitle.get(mod.title);
                    if (!fb) return mod;
                    return {
                        ...mod,
                        landing_description: mod.landing_description ?? fb.description,
                        landing_outcome: mod.landing_outcome ?? fb.outcome,
                        landing_bullets:
                            mod.landing_bullets && mod.landing_bullets.length > 0
                                ? mod.landing_bullets
                                : fb.bullets,
                        landing_mistakes:
                            mod.landing_mistakes && mod.landing_mistakes.length > 0
                                ? mod.landing_mistakes
                                : fb.mistakes,
                        landing_duration_label: mod.landing_duration_label ?? fb.duration,
                    };
                });
                setModules(merged);
            } catch (err) {
                const message = err instanceof Error ? err.message : "Не удалось загрузить модули";
                toast.error("Ошибка", { description: message });
            } finally {
                setIsLoading(false);
            }
        };
        load();
    }, [courseId]);

    const handleSave = async (mod: LandingModulePayload) => {
        setSavingId(mod.id);
        try {
            const update: LandingModuleUpdate = {
                landing_description: nullIfBlank(mod.landing_description),
                landing_outcome: nullIfBlank(mod.landing_outcome),
                landing_bullets: arrayOrNull(mod.landing_bullets ?? [], (b) => b.trim().length === 0),
                landing_mistakes: arrayOrNull(mod.landing_mistakes ?? [], (m) => m.trim().length === 0),
                landing_duration_label: nullIfBlank(mod.landing_duration_label),
            };
            const updated = await adminUpdateModuleLanding(mod.id, update);
            setModules((prev) => prev.map((m) => (m.id === mod.id ? updated : m)));
            toast.success("Модуль сохранён");
        } catch (err) {
            const message = err instanceof Error ? err.message : "Ошибка сохранения";
            toast.error("Ошибка", { description: message });
        } finally {
            setSavingId(null);
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Программа курса</CardTitle>
                <CardDescription>Описание / результат / буллеты / ошибки для каждого модуля. Сохранение per-модуль.</CardDescription>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="flex items-center justify-center min-h-[120px]">
                        <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    </div>
                ) : modules.length === 0 ? (
                    <p className="text-text-secondary">У курса нет модулей.</p>
                ) : (
                    <Accordion type="multiple" className="w-full">
                        {modules.map((mod) => (
                            <AccordionItem key={mod.id} value={mod.id}>
                                <AccordionTrigger>
                                    {mod.order_index + 1}. {mod.title}
                                </AccordionTrigger>
                                <AccordionContent className="space-y-4 pt-2">
                                    <div>
                                        <Label>Длительность (для лендинга, например «23 мин»)</Label>
                                        <Input
                                            value={mod.landing_duration_label ?? ""}
                                            onChange={(e) =>
                                                setModules((prev) =>
                                                    prev.map((m) =>
                                                        m.id === mod.id ? { ...m, landing_duration_label: e.target.value } : m,
                                                    ),
                                                )
                                            }
                                        />
                                    </div>
                                    <div>
                                        <Label>Описание (что разберёт ученик)</Label>
                                        <Textarea
                                            rows={3}
                                            value={mod.landing_description ?? ""}
                                            onChange={(e) =>
                                                setModules((prev) =>
                                                    prev.map((m) =>
                                                        m.id === mod.id ? { ...m, landing_description: e.target.value } : m,
                                                    ),
                                                )
                                            }
                                        />
                                    </div>
                                    <div>
                                        <Label>Результат (что заберёт)</Label>
                                        <Textarea
                                            rows={2}
                                            value={mod.landing_outcome ?? ""}
                                            onChange={(e) =>
                                                setModules((prev) =>
                                                    prev.map((m) =>
                                                        m.id === mod.id ? { ...m, landing_outcome: e.target.value } : m,
                                                    ),
                                                )
                                            }
                                        />
                                    </div>
                                    <div>
                                        <Label>Буллеты (по строке)</Label>
                                        <Textarea
                                            rows={4}
                                            value={joinLines(mod.landing_bullets)}
                                            onChange={(e) =>
                                                setModules((prev) =>
                                                    prev.map((m) =>
                                                        m.id === mod.id
                                                            ? { ...m, landing_bullets: parseLines(e.target.value) }
                                                            : m,
                                                    ),
                                                )
                                            }
                                        />
                                    </div>
                                    <div>
                                        <Label>Ошибки (по строке)</Label>
                                        <Textarea
                                            rows={4}
                                            value={joinLines(mod.landing_mistakes)}
                                            onChange={(e) =>
                                                setModules((prev) =>
                                                    prev.map((m) =>
                                                        m.id === mod.id
                                                            ? { ...m, landing_mistakes: parseLines(e.target.value) }
                                                            : m,
                                                ),
                                                )
                                            }
                                        />
                                    </div>
                                    <div className="flex justify-end">
                                        <Button onClick={() => handleSave(mod)} disabled={savingId === mod.id}>
                                            {savingId === mod.id ? (
                                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                            ) : (
                                                <Save className="w-4 h-4 mr-2" />
                                            )}
                                            Сохранить модуль
                                        </Button>
                                    </div>
                                </AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                )}
            </CardContent>
        </Card>
    );
}

// =====================================================================
// GALLERY
// =====================================================================

interface GalleryFormState {
    image_url: string;
    title: string;
    caption: string;
    alt: string;
    is_published: boolean;
}

function emptyGalleryForm(): GalleryFormState {
    return { image_url: "", title: "", caption: "", alt: "", is_published: true };
}

function GallerySection() {
    const [items, setItems] = useState<GalleryItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [formData, setFormData] = useState<GalleryFormState>(emptyGalleryForm());
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [deleteCandidate, setDeleteCandidate] = useState<GalleryItem | null>(null);

    const load = async () => {
        try {
            const data = await adminGetGallery();
            setItems(data);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Не удалось загрузить галерею";
            toast.error("Ошибка", { description: message });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const handleImportStatic = async () => {
        setIsImporting(true);
        try {
            const created: GalleryItem[] = [];
            for (let idx = 0; idx < staticGalleryItems.length; idx += 1) {
                const it = staticGalleryItems[idx];
                const item = await adminCreateGalleryItem({
                    image_url: it.src,
                    title: it.technique,
                    caption: it.caption,
                    alt: it.alt,
                    is_published: true,
                    order_index: idx,
                });
                created.push(item);
            }
            setItems((prev) => [...prev, ...created]);
            toast.success(`Импортировано фото: ${created.length}`);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Не удалось импортировать";
            toast.error("Ошибка", { description: message });
        } finally {
            setIsImporting(false);
        }
    };

    const openCreate = () => {
        setEditingId(null);
        setFormData(emptyGalleryForm());
        setIsDialogOpen(true);
    };

    const openEdit = (item: GalleryItem) => {
        setEditingId(item.id);
        setFormData({
            image_url: item.image_url,
            title: item.title,
            caption: item.caption ?? "",
            alt: item.alt ?? "",
            is_published: item.is_published,
        });
        setIsDialogOpen(true);
    };

    const handleUpload = async (file: File) => {
        setIsUploading(true);
        try {
            const result = await adminUploadFile(file);
            setFormData((prev) => ({ ...prev, image_url: result.url }));
            toast.success("Фото загружено");
        } catch (err) {
            const message = err instanceof Error ? err.message : "Ошибка загрузки";
            toast.error("Ошибка", { description: message });
        } finally {
            setIsUploading(false);
        }
    };

    const handleSave = async () => {
        if (!formData.image_url.trim() || !formData.title.trim()) {
            toast.error("Ошибка", { description: "image_url и title обязательны" });
            return;
        }
        setIsSaving(true);
        try {
            if (editingId) {
                const updated = await adminUpdateGalleryItem(editingId, {
                    image_url: formData.image_url.trim(),
                    title: formData.title.trim(),
                    caption: nullIfBlank(formData.caption),
                    alt: nullIfBlank(formData.alt),
                    is_published: formData.is_published,
                });
                setItems((prev) => prev.map((i) => (i.id === editingId ? updated : i)));
                toast.success("Фото обновлено");
            } else {
                const payload: GalleryItemCreate = {
                    image_url: formData.image_url.trim(),
                    title: formData.title.trim(),
                    caption: nullIfBlank(formData.caption),
                    alt: nullIfBlank(formData.alt),
                    is_published: formData.is_published,
                    order_index: items.length,
                };
                const created = await adminCreateGalleryItem(payload);
                setItems((prev) => [...prev, created]);
                toast.success("Фото добавлено");
            }
            setIsDialogOpen(false);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Ошибка сохранения";
            toast.error("Ошибка", { description: message });
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!deleteCandidate) return;
        try {
            await adminDeleteGalleryItem(deleteCandidate.id);
            setItems((prev) => prev.filter((i) => i.id !== deleteCandidate.id));
            toast.success("Фото удалено");
        } catch (err) {
            const message = err instanceof Error ? err.message : "Ошибка удаления";
            toast.error("Ошибка", { description: message });
        } finally {
            setDeleteCandidate(null);
        }
    };

    const move = async (index: number, direction: -1 | 1) => {
        const target = index + direction;
        if (target < 0 || target >= items.length) return;
        const reordered = [...items];
        [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
        setItems(reordered);
        try {
            await adminReorderGallery(
                reordered.map((it, idx) => ({ id: it.id, order_index: idx })),
            );
        } catch (err) {
            const message = err instanceof Error ? err.message : "Не удалось изменить порядок";
            toast.error("Ошибка", { description: message });
            load();
        }
    };

    const sortedItems = useMemo(
        () => [...items].sort((a, b) => a.order_index - b.order_index),
        [items],
    );

    return (
        <Card>
            <CardHeader className="flex flex-row items-start justify-between">
                <div>
                    <CardTitle>Галерея работ</CardTitle>
                    <CardDescription>
                        Глобальная для сайта. Порядок задаёт стрелочками; пустая галерея → fallback из course-content.ts.
                    </CardDescription>
                </div>
                <Button onClick={openCreate}>
                    <Plus className="w-4 h-4 mr-2" />
                    Добавить
                </Button>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="flex items-center justify-center min-h-[120px]">
                        <Loader2 className="w-6 h-6 animate-spin text-primary" />
                    </div>
                ) : sortedItems.length === 0 ? (
                    <div className="space-y-3">
                        <p className="text-text-secondary">Пока ни одной фотографии в галерее.</p>
                        <p className="text-sm text-text-secondary">
                            На лендинге сейчас рендерится статическая подборка ({staticGalleryItems.length} фото) — её можно импортировать в БД одной кнопкой и потом редактировать как обычные элементы.
                        </p>
                        <Button variant="outline" onClick={handleImportStatic} disabled={isImporting}>
                            {isImporting ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : (
                                <Upload className="w-4 h-4 mr-2" />
                            )}
                            Импортировать статическую подборку ({staticGalleryItems.length})
                        </Button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {sortedItems.map((item, idx) => (
                            <div key={item.id} className="border border-border rounded-lg overflow-hidden bg-surface">
                                <div className="relative aspect-square bg-muted">
                                    {item.image_url && (
                                        <Image
                                            src={item.image_url}
                                            alt={item.alt ?? item.title}
                                            fill
                                            sizes="(max-width: 768px) 100vw, 33vw"
                                            className="object-cover"
                                        />
                                    )}
                                </div>
                                <div className="p-3 space-y-2">
                                    <div className="flex items-start justify-between gap-2">
                                        <div className="min-w-0">
                                            <p className="font-medium text-text-primary truncate">{item.title}</p>
                                            {item.caption && (
                                                <p className="text-xs text-text-secondary line-clamp-2">{item.caption}</p>
                                            )}
                                        </div>
                                        {!item.is_published && (
                                            <span className="text-xs px-2 py-0.5 rounded bg-muted text-text-secondary">скрыто</span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            disabled={idx === 0}
                                            onClick={() => move(idx, -1)}
                                            title="Выше"
                                        >
                                            <ArrowUp className="w-4 h-4" />
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            disabled={idx === sortedItems.length - 1}
                                            onClick={() => move(idx, 1)}
                                            title="Ниже"
                                        >
                                            <ArrowDown className="w-4 h-4" />
                                        </Button>
                                        <Button size="sm" variant="outline" onClick={() => openEdit(item)} className="ml-auto">
                                            <Pencil className="w-4 h-4" />
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => setDeleteCandidate(item)}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>

            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{editingId ? "Редактировать фото" : "Добавить фото"}</DialogTitle>
                        <DialogDescription>Заголовок и описание видны под фото на лендинге.</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-3">
                        <div>
                            <Label htmlFor="g-image">URL изображения</Label>
                            <Input
                                id="g-image"
                                value={formData.image_url}
                                onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                            />
                            <div className="flex items-center gap-2 mt-2">
                                <input
                                    type="file"
                                    accept="image/*"
                                    disabled={isUploading}
                                    onChange={(e) => {
                                        const file = e.target.files?.[0];
                                        if (file) handleUpload(file);
                                        e.target.value = "";
                                    }}
                                />
                                {isUploading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
                                {!isUploading && (
                                    <span className="text-xs text-text-secondary inline-flex items-center gap-1">
                                        <Upload className="w-3 h-3" />
                                        или загрузите файл
                                    </span>
                                )}
                            </div>
                        </div>
                        <div>
                            <Label htmlFor="g-title">Заголовок (техника)</Label>
                            <Input
                                id="g-title"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            />
                        </div>
                        <div>
                            <Label htmlFor="g-caption">Описание</Label>
                            <Textarea
                                id="g-caption"
                                rows={3}
                                value={formData.caption}
                                onChange={(e) => setFormData({ ...formData, caption: e.target.value })}
                            />
                        </div>
                        <div>
                            <Label htmlFor="g-alt">Alt-текст (для accessibility)</Label>
                            <Input
                                id="g-alt"
                                value={formData.alt}
                                onChange={(e) => setFormData({ ...formData, alt: e.target.value })}
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <Switch
                                id="g-published"
                                checked={formData.is_published}
                                onCheckedChange={(checked) => setFormData({ ...formData, is_published: checked })}
                            />
                            <Label htmlFor="g-published">Показывать на лендинге</Label>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                            Отмена
                        </Button>
                        <Button onClick={handleSave} disabled={isSaving}>
                            {isSaving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                            Сохранить
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={!!deleteCandidate} onOpenChange={(open) => !open && setDeleteCandidate(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Удалить фото?</AlertDialogTitle>
                        <AlertDialogDescription>
                            «{deleteCandidate?.title}» исчезнет из галереи на лендинге. Действие необратимо.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Отмена</AlertDialogCancel>
                        <AlertDialogAction onClick={handleDelete}>Удалить</AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Card>
    );
}
