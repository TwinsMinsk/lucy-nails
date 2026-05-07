"use client"

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Loader2, BookOpen, Plus, Pencil, Trash2, ArrowLeft, GripVertical, Video, Clock } from "lucide-react";
import {
    adminGetCourse,
    adminGetCourseModules,
    adminCreateModule,
    adminUpdateModule,
    adminDeleteModule,
    adminCreateLesson,
    adminUpdateLesson,
    adminDeleteLesson,
    adminGetLesson,
    AdminCourseFullResponse,
    ModuleResponse,
    ModuleCreateRequest,
    LessonCreateRequest,
    LessonBriefResponse,
} from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Editor } from "@/components/ui/editor";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";

export default function AdminCourseDetailPage() {
    const params = useParams();
    const courseId = params.id as string;

    const [course, setCourse] = useState<AdminCourseFullResponse | null>(null);
    const [modules, setModules] = useState<ModuleResponse[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

    // Module dialog
    const [moduleDialogOpen, setModuleDialogOpen] = useState(false);
    const [editingModule, setEditingModule] = useState<ModuleResponse | null>(null);
    const [moduleForm, setModuleForm] = useState({ title: "", description: "", order_index: 0, is_published: false });

    // Lesson dialog
    const [lessonDialogOpen, setLessonDialogOpen] = useState(false);
    const [editingLesson, setEditingLesson] = useState<LessonBriefResponse | null>(null);
    const [lessonModuleId, setLessonModuleId] = useState<string | null>(null);
    const [lessonForm, setLessonForm] = useState({
        title: "",
        description: "",
        content: "",
        kinescope_video_id: "",
        duration_seconds: 0,
        order_index: 0,
        is_preview: false,
        promo_kinescope_video_id: "",
        promo_poster_url: "",
        promo_description: "",
        promo_bullets_text: "",
    });

    const fetchData = useCallback(async () => {
        try {
            const [courseData, modulesData] = await Promise.all([
                adminGetCourse(courseId),
                adminGetCourseModules(courseId),
            ]);
            setCourse(courseData);
            setModules(modulesData);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка загрузки";
            toast.error("Ошибка", { description: errorMessage });
        } finally {
            setIsLoading(false);
        }
    }, [courseId]);

    useEffect(() => {
        if (courseId) fetchData();
    }, [courseId, fetchData]);

    // === Module handlers ===
    const openModuleDialog = (module?: ModuleResponse) => {
        if (module) {
            setEditingModule(module);
            setModuleForm({
                title: module.title,
                description: module.description || "",
                order_index: module.order_index,
                is_published: module.is_published,
            });
        } else {
            setEditingModule(null);
            setModuleForm({ title: "", description: "", order_index: modules.length, is_published: false });
        }
        setModuleDialogOpen(true);
    };

    const saveModule = async () => {
        if (!moduleForm.title.trim()) {
            toast.error("Введите название модуля");
            return;
        }
        setIsSaving(true);
        try {
            if (editingModule) {
                await adminUpdateModule(editingModule.id, moduleForm);
                toast.success("Модуль обновлён");
            } else {
                await adminCreateModule({ ...moduleForm, course_id: courseId } as ModuleCreateRequest);
                toast.success("Модуль создан");
            }
            setModuleDialogOpen(false);
            fetchData();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка сохранения";
            toast.error("Ошибка", { description: errorMessage });
        } finally {
            setIsSaving(false);
        }
    };

    const deleteModule = async (moduleId: string) => {
        try {
            await adminDeleteModule(moduleId);
            toast.success("Модуль удалён");
            fetchData();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка удаления";
            toast.error("Ошибка", { description: errorMessage });
        }
    };

    // === Lesson handlers ===
    const openLessonDialog = async (moduleId: string, lesson?: LessonBriefResponse) => {
        setLessonModuleId(moduleId);
        if (lesson) {
            // Edit Mode
            try {
                // Show loading toast or minimal UI blocking if needed
                // For now just fetch
                const fullLesson = await adminGetLesson(lesson.id);
                setEditingLesson(lesson);
                setLessonForm({
                    title: fullLesson.title,
                    description: fullLesson.description || "",
                    content: fullLesson.content || "",
                    kinescope_video_id: fullLesson.kinescope_video_id || "",
                    duration_seconds: fullLesson.duration_seconds,
                    order_index: fullLesson.order_index,
                    is_preview: fullLesson.is_preview,
                    promo_kinescope_video_id: fullLesson.promo_kinescope_video_id || "",
                    promo_poster_url: fullLesson.promo_poster_url || "",
                    promo_description: fullLesson.promo_description || "",
                    promo_bullets_text: (fullLesson.promo_highlights?.bullets || []).join("\n"),
                });
                setLessonDialogOpen(true);
            } catch (error) {
                console.error("Failed to load lesson:", error);
                toast.error("Ошибка загрузки деталей урока");
            }
        } else {
            // Create Mode
            setEditingLesson(null);
            const courseModule = modules.find(m => m.id === moduleId);
            setLessonForm({
                title: "",
                description: "",
                content: "",
                kinescope_video_id: "",
                duration_seconds: 0,
                order_index: courseModule?.lessons?.length || 0,
                is_preview: false,
                promo_kinescope_video_id: "",
                promo_poster_url: "",
                promo_description: "",
                promo_bullets_text: "",
            });
            setLessonDialogOpen(true);
        }
    };

    const saveLesson = async () => {
        if (!lessonForm.title.trim() || !lessonModuleId) {
            toast.error("Введите название урока");
            return;
        }
        setIsSaving(true);

        try {
            const promoBullets = lessonForm.promo_bullets_text
                .split("\n")
                .map((item) => item.trim())
                .filter(Boolean);
            const lessonPayload = {
                title: lessonForm.title,
                description: lessonForm.description,
                content: lessonForm.content,
                kinescope_video_id: lessonForm.kinescope_video_id,
                duration_seconds: lessonForm.duration_seconds,
                order_index: lessonForm.order_index,
                is_preview: lessonForm.is_preview,
                promo_kinescope_video_id: lessonForm.promo_kinescope_video_id,
                promo_poster_url: lessonForm.promo_poster_url,
                promo_description: lessonForm.promo_description,
                promo_highlights: { bullets: promoBullets },
            };

            // Проверка режима: Редактирование или Создание
            if (editingLesson && editingLesson.id) {
                // Edit Mode (PUT)
                await adminUpdateLesson(editingLesson.id, lessonPayload);
                toast.success("Урок успешно обновлён");
            } else {
                // Create Mode (POST)
                await adminCreateLesson({
                    ...lessonPayload,
                    module_id: lessonModuleId
                } as LessonCreateRequest);
                toast.success("Урок успешно создан");
            }

            setLessonDialogOpen(false);
            setEditingLesson(null); // Сбрасываем после сохранения
            fetchData();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка сохранения";
            toast.error("Ошибка", { description: errorMessage });
        } finally {
            setIsSaving(false);
        }
    };

    const deleteLesson = async (lessonId: string) => {
        try {
            await adminDeleteLesson(lessonId);
            toast.success("Урок удалён");
            fetchData();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка удаления";
            toast.error("Ошибка", { description: errorMessage });
        }
    };

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        return mins > 0 ? `${mins} мин` : "—";
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    if (!course) {
        return (
            <div className="container px-6 py-8 text-center">
                <p className="text-text-secondary">Курс не найден</p>
            </div>
        );
    }

    return (
        <div className="container px-6 py-8 max-w-5xl">
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div className="space-y-1">
                        <Link href="/admin/courses" className="text-sm text-text-secondary hover:text-primary flex items-center gap-1 mb-2">
                            <ArrowLeft className="w-4 h-4" />
                            Назад к курсам
                        </Link>
                        <h1 className="text-2xl font-bold text-text-primary">{course.title}</h1>
                        <p className="text-text-secondary">
                            {course.modules_count} модулей • {course.lessons_count} уроков
                        </p>
                    </div>
                    <Button onClick={() => openModuleDialog()} className="gap-2">
                        <Plus className="w-4 h-4" />
                        Добавить модуль
                    </Button>
                </div>

                {/* Modules List */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-primary" />
                            Модули и уроки
                        </CardTitle>
                        <CardDescription>
                            Управляйте структурой курса
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {modules.length > 0 ? (
                            <Accordion type="multiple" className="space-y-2">
                                {modules.map((module) => (
                                    <AccordionItem key={module.id} value={module.id} className="border rounded-lg px-4">
                                        <div className="flex items-center w-full">
                                            <AccordionTrigger className="hover:no-underline py-4 flex-1">
                                                <div className="flex items-center gap-3 w-full">
                                                    <GripVertical className="w-4 h-4 text-text-secondary shrink-0" />
                                                    <div className="flex-1 text-left">
                                                        <div className="font-medium flex items-center gap-2">
                                                            <span className="text-primary text-sm">#{module.order_index + 1}</span>
                                                            {module.title}
                                                            {!module.is_published && (
                                                                <Badge variant="outline" className="text-xs">Черновик</Badge>
                                                            )}
                                                        </div>
                                                        <div className="text-sm text-text-secondary">
                                                            {module.lessons_count} уроков
                                                        </div>
                                                    </div>
                                                </div>
                                            </AccordionTrigger>
                                            <div className="flex items-center gap-1 ml-2">
                                                <Button variant="ghost" size="icon" onClick={() => openModuleDialog(module)}>
                                                    <Pencil className="w-4 h-4" />
                                                </Button>
                                                <AlertDialog>
                                                    <AlertDialogTrigger asChild>
                                                        <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive">
                                                            <Trash2 className="w-4 h-4" />
                                                        </Button>
                                                    </AlertDialogTrigger>
                                                    <AlertDialogContent>
                                                        <AlertDialogHeader>
                                                            <AlertDialogTitle>Удалить модуль?</AlertDialogTitle>
                                                            <AlertDialogDescription>
                                                                Модуль "{module.title}" и все его уроки будут удалены.
                                                            </AlertDialogDescription>
                                                        </AlertDialogHeader>
                                                        <AlertDialogFooter>
                                                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                                                            <AlertDialogAction onClick={() => deleteModule(module.id)} className="bg-destructive text-destructive-foreground">
                                                                Удалить
                                                            </AlertDialogAction>
                                                        </AlertDialogFooter>
                                                    </AlertDialogContent>
                                                </AlertDialog>
                                            </div>
                                        </div>
                                        <AccordionContent className="pb-4">
                                            <div className="space-y-2 ml-7">
                                                {module.lessons && module.lessons.length > 0 ? (
                                                    module.lessons.map((lesson) => (
                                                        <div key={lesson.id} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 hover:bg-slate-100 transition-colors">
                                                            <div className="flex items-center gap-3">
                                                                <Video className="w-4 h-4 text-primary" />
                                                                <div>
                                                                    <div className="font-medium text-sm flex items-center gap-2">
                                                                        {lesson.title}
                                                                        {lesson.is_preview && <Badge variant="secondary" className="text-xs">Превью</Badge>}
                                                                        {(lesson.promo_kinescope_video_id || lesson.promo_description) && (
                                                                            <Badge variant="outline" className="text-xs border-[#D4AF37]/40 text-text-secondary">
                                                                                Промо заполнено
                                                                            </Badge>
                                                                        )}
                                                                    </div>
                                                                    <div className="text-xs text-text-secondary flex items-center gap-2">
                                                                        <Clock className="w-3 h-3" />
                                                                        {formatDuration(lesson.duration_seconds)}
                                                                        {lesson.kinescope_video_id && (
                                                                            <span className="text-green-600">• Видео загружено</span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-1">
                                                                <Button variant="ghost" size="icon" onClick={() => openLessonDialog(module.id, lesson)}>
                                                                    <Pencil className="w-3 h-3" />
                                                                </Button>
                                                                <AlertDialog>
                                                                    <AlertDialogTrigger asChild>
                                                                        <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive">
                                                                            <Trash2 className="w-3 h-3" />
                                                                        </Button>
                                                                    </AlertDialogTrigger>
                                                                    <AlertDialogContent>
                                                                        <AlertDialogHeader>
                                                                            <AlertDialogTitle>Удалить урок?</AlertDialogTitle>
                                                                            <AlertDialogDescription>
                                                                                Урок "{lesson.title}" будет удалён.
                                                                            </AlertDialogDescription>
                                                                        </AlertDialogHeader>
                                                                        <AlertDialogFooter>
                                                                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                                                                            <AlertDialogAction onClick={() => deleteLesson(lesson.id)} className="bg-destructive text-destructive-foreground">
                                                                                Удалить
                                                                            </AlertDialogAction>
                                                                        </AlertDialogFooter>
                                                                    </AlertDialogContent>
                                                                </AlertDialog>
                                                            </div>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p className="text-sm text-text-secondary py-2">Уроков пока нет</p>
                                                )}
                                                <Button variant="outline" size="sm" className="mt-2 gap-1" onClick={() => openLessonDialog(module.id)}>
                                                    <Plus className="w-3 h-3" />
                                                    Добавить урок
                                                </Button>
                                            </div>
                                        </AccordionContent>
                                    </AccordionItem>
                                ))}
                            </Accordion>
                        ) : (
                            <div className="text-center py-8 text-text-secondary">
                                <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-20" />
                                <p>Модулей пока нет</p>
                                <Button onClick={() => openModuleDialog()} variant="link" className="mt-1">
                                    Создать первый модуль
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Module Dialog */}
            <Dialog open={moduleDialogOpen} onOpenChange={setModuleDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{editingModule ? "Редактировать модуль" : "Создать модуль"}</DialogTitle>
                        <DialogDescription>Заполните информацию о модуле</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Название *</Label>
                            <Input value={moduleForm.title} onChange={(e) => setModuleForm({ ...moduleForm, title: e.target.value })} placeholder="Название модуля" />
                        </div>
                        <div className="space-y-2">
                            <Label>Описание</Label>
                            <Textarea value={moduleForm.description} onChange={(e) => setModuleForm({ ...moduleForm, description: e.target.value })} rows={2} />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Порядок</Label>
                                <Input type="number" value={moduleForm.order_index} onChange={(e) => setModuleForm({ ...moduleForm, order_index: parseInt(e.target.value) || 0 })} />
                            </div>
                            <div className="flex items-center justify-between p-3 bg-primary/5 rounded-lg">
                                <Label>Опубликован</Label>
                                <Switch checked={moduleForm.is_published} onCheckedChange={(checked) => setModuleForm({ ...moduleForm, is_published: checked })} />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setModuleDialogOpen(false)} disabled={isSaving}>Отмена</Button>
                        <Button onClick={saveModule} disabled={isSaving}>
                            {isSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                            {editingModule ? "Сохранить" : "Создать"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Lesson Dialog */}
            <Dialog open={lessonDialogOpen} onOpenChange={setLessonDialogOpen}>
                <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>{editingLesson ? "Редактировать урок" : "Создать урок"}</DialogTitle>
                        <DialogDescription>Заполните информацию об уроке</DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label>Название *</Label>
                            <Input value={lessonForm.title} onChange={(e) => setLessonForm({ ...lessonForm, title: e.target.value })} placeholder="Название урока" />
                        </div>
                        <div className="space-y-2">
                            <Label>Kinescope Video ID</Label>
                            <Input value={lessonForm.kinescope_video_id} onChange={(e) => setLessonForm({ ...lessonForm, kinescope_video_id: e.target.value })} placeholder="abc123xyz" />
                            <p className="text-xs text-text-secondary">ID видео из Kinescope</p>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Длительность (сек)</Label>
                                <Input type="number" value={lessonForm.duration_seconds} onChange={(e) => setLessonForm({ ...lessonForm, duration_seconds: parseInt(e.target.value) || 0 })} />
                            </div>
                            <div className="space-y-2">
                                <Label>Порядок</Label>
                                <Input type="number" value={lessonForm.order_index} onChange={(e) => setLessonForm({ ...lessonForm, order_index: parseInt(e.target.value) || 0 })} />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Конспект (Текстовое описание)</Label>
                            <Editor
                                value={lessonForm.content}
                                onChange={(value) => setLessonForm({ ...lessonForm, content: value })}
                                placeholder="Введите текст конспекта..."
                            />
                        </div>
                        <div className="flex items-center justify-between p-3 bg-primary/5 rounded-lg">
                            <div>
                                <Label>Бесплатный превью</Label>
                                <p className="text-xs text-text-secondary">Урок будет доступен без покупки</p>
                            </div>
                            <Switch checked={lessonForm.is_preview} onCheckedChange={(checked) => setLessonForm({ ...lessonForm, is_preview: checked })} />
                        </div>
                        <div className="rounded-2xl border border-primary/20 bg-[#fff1f4]/60 p-4 space-y-4">
                            <div>
                                <h3 className="font-semibold text-text-primary">Промо для лендинга</h3>
                                <p className="text-xs text-text-secondary">
                                    Эти поля показываются в блоке «Программа курса» на главной странице.
                                </p>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>Kinescope ID промо</Label>
                                    <Input
                                        value={lessonForm.promo_kinescope_video_id}
                                        onChange={(e) => setLessonForm({ ...lessonForm, promo_kinescope_video_id: e.target.value })}
                                        placeholder="id короткого промо"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>URL постера промо</Label>
                                    <Input
                                        value={lessonForm.promo_poster_url}
                                        onChange={(e) => setLessonForm({ ...lessonForm, promo_poster_url: e.target.value })}
                                        placeholder="https://.../poster.jpg"
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label>Краткое описание для карточки</Label>
                                <Textarea
                                    value={lessonForm.promo_description}
                                    onChange={(e) => setLessonForm({ ...lessonForm, promo_description: e.target.value })}
                                    rows={3}
                                    placeholder="Что мастер освоит в этом уроке и почему это полезно клиентам"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Буллеты «что узнаете»</Label>
                                <Textarea
                                    value={lessonForm.promo_bullets_text}
                                    onChange={(e) => setLessonForm({ ...lessonForm, promo_bullets_text: e.target.value })}
                                    rows={4}
                                    placeholder={"Один тезис на строку\nНапример: Подбор материалов\nЗакрепление без сколов"}
                                />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setLessonDialogOpen(false)} disabled={isSaving}>Отмена</Button>
                        <Button onClick={saveLesson} disabled={isSaving}>
                            {isSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                            {editingLesson ? "Сохранить" : "Создать"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
