"use client"

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Loader2, BookOpen, Plus, Pencil, Trash2, Eye, EyeOff, ChevronRight, Upload } from "lucide-react";
import {
    adminGetCourses,
    adminCreateCourse,
    adminUpdateCourse,
    adminDeleteCourse,
    adminUploadFile,
    AdminCourseFullResponse,
    CourseCreateRequest,
} from "@/lib/api";
import { toast } from "sonner";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
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

export default function AdminCoursesPage() {
    const [courses, setCourses] = useState<AdminCourseFullResponse[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingCourse, setEditingCourse] = useState<AdminCourseFullResponse | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    // Form state
    const [formData, setFormData] = useState<CourseCreateRequest>({
        title: "",
        description: "",
        cover_image_url: "",
        price_self: 5000,
        price_support: 20000,
        is_published: false,
    });

    const fetchCourses = async () => {
        try {
            const data = await adminGetCourses();
            setCourses(data);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка загрузки";
            toast.error("Ошибка", { description: errorMessage });
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchCourses();
    }, []);

    const resetForm = () => {
        setFormData({
            title: "",
            description: "",
            cover_image_url: "",
            price_self: 5000,
            price_support: 20000,
            is_published: false,
        });
        setEditingCourse(null);
    };

    const openCreateDialog = () => {
        resetForm();
        setIsDialogOpen(true);
    };

    const openEditDialog = (course: AdminCourseFullResponse) => {
        setEditingCourse(course);
        setFormData({
            title: course.title,
            description: course.description,
            cover_image_url: course.cover_image_url || "",
            price_self: course.price_self,
            price_support: course.price_support,
            is_published: course.is_published,
        });
        setIsDialogOpen(true);
    };

    const handleSave = async () => {
        if (!formData.title.trim()) {
            toast.error("Ошибка", { description: "Название курса обязательно" });
            return;
        }

        setIsSaving(true);
        try {
            if (editingCourse) {
                await adminUpdateCourse(editingCourse.id, formData);
                toast.success("Курс обновлён");
            } else {
                await adminCreateCourse(formData);
                toast.success("Курс создан");
            }
            setIsDialogOpen(false);
            resetForm();
            fetchCourses();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка сохранения";
            toast.error("Ошибка", { description: errorMessage });
        } finally {
            setIsSaving(false);
        }
    };

    const handleDelete = async (courseId: string) => {
        try {
            await adminDeleteCourse(courseId);
            toast.success("Курс удалён");
            fetchCourses();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка удаления";
            toast.error("Ошибка", { description: errorMessage });
        }
    };

    const togglePublish = async (course: AdminCourseFullResponse) => {
        try {
            await adminUpdateCourse(course.id, { is_published: !course.is_published });
            toast.success(course.is_published ? "Курс скрыт" : "Курс опубликован");
            fetchCourses();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Ошибка";
            toast.error("Ошибка", { description: errorMessage });
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    return (
        <div className="container px-6 py-8 max-w-7xl">
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
                            <BookOpen className="w-8 h-8 text-primary" />
                            Управление курсами
                        </h1>
                        <p className="text-text-secondary mt-2">
                            Создание и редактирование курсов, модулей и уроков
                        </p>
                    </div>
                    <Dialog open={isDialogOpen} onOpenChange={(open) => {
                        setIsDialogOpen(open);
                        if (!open) resetForm();
                    }}>
                        <DialogTrigger asChild>
                            <Button onClick={openCreateDialog} className="gap-2">
                                <Plus className="w-4 h-4" />
                                Добавить курс
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-lg">
                            <DialogHeader>
                                <DialogTitle>
                                    {editingCourse ? "Редактировать курс" : "Создать курс"}
                                </DialogTitle>
                                <DialogDescription>
                                    Заполните информацию о курсе
                                </DialogDescription>
                            </DialogHeader>

                            <div className="space-y-4 py-4">
                                <div className="space-y-2">
                                    <Label htmlFor="title">Название курса *</Label>
                                    <Input
                                        id="title"
                                        value={formData.title}
                                        onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                                        placeholder="Дизайн ногтей: От А до Я"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="description">Описание</Label>
                                    <Textarea
                                        id="description"
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        placeholder="Подробное описание курса..."
                                        rows={3}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="cover_image_url">Баннер (обложка)</Label>
                                    <div className="space-y-3">
                                        {/* URL Input */}
                                        <Input
                                            id="cover_image_url"
                                            value={formData.cover_image_url}
                                            onChange={(e) => setFormData({ ...formData, cover_image_url: e.target.value })}
                                            placeholder="https://example.com/image.jpg или загрузите файл ниже"
                                        />

                                        {/* File Upload */}
                                        <div className="flex items-center gap-2">
                                            <Input
                                                type="file"
                                                accept="image/*"
                                                onChange={async (e) => {
                                                    const file = e.target.files?.[0];
                                                    if (!file) return;

                                                    setIsUploading(true);
                                                    try {
                                                        const result = await adminUploadFile(file);
                                                        setFormData({ ...formData, cover_image_url: result.url });
                                                        toast.success("Файл загружен");
                                                    } catch (error) {
                                                        const errorMessage = error instanceof Error ? error.message : "Ошибка загрузки";
                                                        toast.error("Ошибка", { description: errorMessage });
                                                    } finally {
                                                        setIsUploading(false);
                                                    }
                                                }}
                                                disabled={isUploading}
                                                className="flex-1"
                                            />
                                            {isUploading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
                                        </div>

                                        {/* Preview */}
                                        {formData.cover_image_url && (
                                            <div className="relative w-full h-32 bg-slate-100 rounded-lg overflow-hidden border">
                                                <Image
                                                    src={formData.cover_image_url}
                                                    alt="Preview"
                                                    fill
                                                    className="object-cover"
                                                />
                                            </div>
                                        )}
                                    </div>
                                    <p className="text-xs text-text-secondary">Введите URL или загрузите изображение</p>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="price_self">Цена "Самостоятельный" (₽)</Label>
                                        <Input
                                            id="price_self"
                                            type="number"
                                            value={formData.price_self}
                                            onChange={(e) => setFormData({ ...formData, price_self: parseInt(e.target.value) || 0 })}
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="price_support">Цена "С поддержкой" (₽)</Label>
                                        <Input
                                            id="price_support"
                                            type="number"
                                            value={formData.price_support}
                                            onChange={(e) => setFormData({ ...formData, price_support: parseInt(e.target.value) || 0 })}
                                        />
                                    </div>
                                </div>

                                <div className="flex items-center justify-between p-3 bg-primary/5 rounded-lg">
                                    <div className="space-y-0.5">
                                        <Label>Опубликован</Label>
                                        <p className="text-xs text-text-secondary">
                                            Курс будет виден пользователям
                                        </p>
                                    </div>
                                    <Switch
                                        checked={formData.is_published}
                                        onCheckedChange={(checked) => setFormData({ ...formData, is_published: checked })}
                                    />
                                </div>
                            </div>

                            <DialogFooter>
                                <Button variant="outline" onClick={() => setIsDialogOpen(false)} disabled={isSaving}>
                                    Отмена
                                </Button>
                                <Button onClick={handleSave} disabled={isSaving}>
                                    {isSaving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                                    {editingCourse ? "Сохранить" : "Создать"}
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>

                {/* Content */}
                <Card>
                    <CardHeader>
                        <CardTitle>Все курсы</CardTitle>
                        <CardDescription>
                            Всего курсов: {courses.length}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="text-center space-y-3">
                                    <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" />
                                    <p className="text-text-secondary text-sm">Загрузка курсов...</p>
                                </div>
                            </div>
                        ) : courses.length > 0 ? (
                            <div className="rounded-md border">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>Название</TableHead>
                                            <TableHead className="w-[100px]">Модули</TableHead>
                                            <TableHead className="w-[100px]">Уроки</TableHead>
                                            <TableHead className="w-[120px]">Цена</TableHead>
                                            <TableHead className="w-[100px]">Статус</TableHead>
                                            <TableHead className="w-[120px]">Дата</TableHead>
                                            <TableHead className="w-[180px] text-right">Действия</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {courses.map((course) => (
                                            <TableRow key={course.id}>
                                                <TableCell>
                                                    <div className="font-medium">{course.title}</div>
                                                    {course.description && (
                                                        <div className="text-sm text-text-secondary line-clamp-1">
                                                            {course.description}
                                                        </div>
                                                    )}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {course.modules_count}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {course.lessons_count}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="text-sm">
                                                        <div>{course.price_self.toLocaleString('ru-RU')} ₽</div>
                                                        <div className="text-text-secondary">{course.price_support.toLocaleString('ru-RU')} ₽</div>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant={course.is_published ? "default" : "secondary"}>
                                                        {course.is_published ? "Опубликован" : "Черновик"}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-text-secondary text-sm">
                                                    {formatDate(course.created_at)}
                                                </TableCell>
                                                <TableCell className="text-right">
                                                    <div className="flex items-center justify-end gap-1">
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            onClick={() => togglePublish(course)}
                                                            title={course.is_published ? "Скрыть" : "Опубликовать"}
                                                        >
                                                            {course.is_published ? (
                                                                <EyeOff className="w-4 h-4" />
                                                            ) : (
                                                                <Eye className="w-4 h-4" />
                                                            )}
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            onClick={() => openEditDialog(course)}
                                                            title="Редактировать"
                                                        >
                                                            <Pencil className="w-4 h-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="icon"
                                                            asChild
                                                            title="Модули"
                                                        >
                                                            <Link href={`/admin/courses/${course.id}`}>
                                                                <ChevronRight className="w-4 h-4" />
                                                            </Link>
                                                        </Button>
                                                        <AlertDialog>
                                                            <AlertDialogTrigger asChild>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="icon"
                                                                    className="text-destructive hover:text-destructive"
                                                                    title="Удалить"
                                                                >
                                                                    <Trash2 className="w-4 h-4" />
                                                                </Button>
                                                            </AlertDialogTrigger>
                                                            <AlertDialogContent>
                                                                <AlertDialogHeader>
                                                                    <AlertDialogTitle>Удалить курс?</AlertDialogTitle>
                                                                    <AlertDialogDescription>
                                                                        Это действие нельзя отменить. Курс "{course.title}" и все его модули и уроки будут удалены.
                                                                    </AlertDialogDescription>
                                                                </AlertDialogHeader>
                                                                <AlertDialogFooter>
                                                                    <AlertDialogCancel>Отмена</AlertDialogCancel>
                                                                    <AlertDialogAction
                                                                        onClick={() => handleDelete(course.id)}
                                                                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                                                    >
                                                                        Удалить
                                                                    </AlertDialogAction>
                                                                </AlertDialogFooter>
                                                            </AlertDialogContent>
                                                        </AlertDialog>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        ) : (
                            <div className="text-center py-12 text-text-secondary">
                                <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-20" />
                                <p>Курсы не найдены</p>
                                <Button onClick={openCreateDialog} variant="link" className="mt-2">
                                    Создать первый курс
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
