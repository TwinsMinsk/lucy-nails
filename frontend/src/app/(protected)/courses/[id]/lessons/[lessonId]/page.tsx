"use client";

import { use } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, CheckCircle, Loader2, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { getLesson, LessonResponse, getPublicCourseModules, ModuleResponse, getCourseProgress, updateLessonProgress } from "@/lib/api";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { VideoPlayer } from "@/components/course/VideoPlayer";

export default function LessonPage({ params }: { params: Promise<{ id: string, lessonId: string }> }) {
    const { id, lessonId } = use(params);

    const [lesson, setLesson] = useState<LessonResponse | null>(null);
    const [modules, setModules] = useState<ModuleResponse[]>([]);
    const [completedLessonIds, setCompletedLessonIds] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [prevLessonId, setPrevLessonId] = useState<string | null>(null);
    const [nextLessonId, setNextLessonId] = useState<string | null>(null);
    const [progressPercent, setProgressPercent] = useState(0);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                // Fetch current lesson, course structure, and progress in parallel
                const [lessonData, modulesData, progressData] = await Promise.all([
                    getLesson(lessonId),
                    getPublicCourseModules(id),
                    getCourseProgress(id)
                ]);

                setLesson(lessonData);
                setModules(modulesData);
                setCompletedLessonIds(progressData.completed_lesson_ids);
                setProgressPercent(progressData.progress_percent);

                // Calculate navigation
                const allLessons: { id: string, module_id: string }[] = [];
                // Sort modules just in case
                const sortedModules = [...modulesData].sort((a, b) => a.order_index - b.order_index);

                sortedModules.forEach(m => {
                    const sortedLessons = [...(m.lessons || [])].sort((a, b) => a.order_index - b.order_index);
                    sortedLessons.forEach(l => {
                        allLessons.push({ id: l.id, module_id: m.id });
                    });
                });

                const currentIndex = allLessons.findIndex(l => l.id === lessonId);
                if (currentIndex !== -1) {
                    setPrevLessonId(currentIndex > 0 ? allLessons[currentIndex - 1].id : null);
                    setNextLessonId(currentIndex < allLessons.length - 1 ? allLessons[currentIndex + 1].id : null);
                }

            } catch (error) {
                console.error(error);
                toast.error("Ошибка загрузки данных урока");
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [id, lessonId]);

    const handleToggleComplete = async () => {
        if (!lesson) return;

        const isCompleted = completedLessonIds.includes(lesson.id);
        const newStatus = !isCompleted;

        try {
            // Optimistic update
            if (newStatus) {
                setCompletedLessonIds(prev => [...prev, lesson.id]);
                toast.success("Урок отмечен как просмотренный");
            } else {
                setCompletedLessonIds(prev => prev.filter(id => id !== lesson.id));
                toast.success("Отметка просмотра снята");
            }

            await updateLessonProgress(lesson.id, { is_completed: newStatus });

            // Refresh progress stats in background
            const progressData = await getCourseProgress(id);
            setProgressPercent(progressData.progress_percent);

        } catch (error) {
            console.error(error);
            toast.error("Ошибка сохранения прогресса");
            // Revert optimistic update
            if (newStatus) {
                setCompletedLessonIds(prev => prev.filter(id => id !== lesson!.id));
            } else {
                setCompletedLessonIds(prev => [...prev, lesson!.id]);
            }
        }
    };

    // Format duration helper
    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        return `${mins} мин`;
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-[calc(100vh-64px)]">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
        );
    }

    if (!lesson) {
        return (
            <div className="flex flex-col items-center justify-center h-[calc(100vh-64px)] gap-4">
                <p className="text-text-secondary">Урок не найден</p>
                <Button asChild variant="outline">
                    <Link href="/dashboard">Вернуться в кабинет</Link>
                </Button>
            </div>
        );
    }

    const isLessonCompleted = completedLessonIds.includes(lesson.id);

    return (
        <div className="flex flex-col lg:flex-row h-[calc(100vh-64px)] overflow-hidden">
            {/* Main Content (Video Player) */}
            <div className="flex-1 flex flex-col overflow-y-auto bg-background">

                {/* Breadcrumb / Back Link */}
                <div className="container px-4 md:px-6 py-2 flex items-center justify-between">
                    <Link href="/dashboard" className="text-sm text-text-secondary hover:text-primary flex items-center gap-1">
                        <ChevronLeft className="w-4 h-4" /> Назад в кабинет
                    </Link>
                </div>

                {/* Video Player Section */}
                <div className="container px-4 md:px-6 py-2">
                    <div className="max-w-4xl mx-auto overflow-hidden rounded-2xl shadow-2xl border bg-black aspect-video">
                        <VideoPlayer
                            lessonId={lessonId}
                            title={lesson.title}
                        />
                    </div>
                </div>

                {/* Lesson Info & Navigation */}
                <div className="container px-4 md:px-6 py-6 space-y-6 pb-20">
                    <div className="max-w-4xl mx-auto">
                        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
                            <div className="space-y-2">
                                <h1 className="text-2xl md:text-3xl font-serif font-bold text-text-primary">
                                    {modules.find(m => m.id === lesson.module_id)?.order_index}.{lesson.order_index}. {lesson.title}
                                </h1>
                                <p className="text-text-secondary text-base leading-relaxed max-w-2xl">
                                    {lesson.description}
                                </p>
                            </div>

                            <div />
                        </div>

                        {lesson.content && (
                            <div className="mt-10 p-6 md:p-10 bg-white rounded-3xl border shadow-sm">
                                <h2 className="text-xl font-bold mb-6 text-text-primary">Конспект урока</h2>
                                <div
                                    className="prose prose-pink max-w-none 
                                    prose-headings:font-serif prose-headings:text-text-primary
                                    prose-p:text-text-secondary prose-p:leading-relaxed
                                    prose-li:text-text-secondary"
                                    dangerouslySetInnerHTML={{ __html: lesson.content }}
                                />
                            </div>
                        )}

                        <Separator className="my-8" />

                        {/* Lesson Navigation */}
                        <div className="flex justify-between items-center pt-4">
                            {prevLessonId ? (
                                <Button variant="ghost" asChild className="gap-2 text-muted-foreground hover:text-primary pl-0">
                                    <Link href={`/courses/${id}/lessons/${prevLessonId}`}>
                                        <ChevronLeft className="w-4 h-4" /> Предыдущий урок
                                    </Link>
                                </Button>
                            ) : (
                                <div /> // spacer
                            )}

                            <div className="flex items-center gap-4">
                                {!isLessonCompleted ? (
                                    <Button
                                        size="lg"
                                        onClick={handleToggleComplete}
                                        className="rounded-full px-8 bg-green-600 hover:bg-green-700 text-white shadow-md transition-all hover:scale-105"
                                    >
                                        <CheckCircle className="w-5 h-5 mr-2" />
                                        Отметить просмотренным
                                    </Button>
                                ) : (
                                    <>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleToggleComplete}
                                            className="text-xs text-muted-foreground hover:text-destructive hidden sm:flex"
                                            title="Снять отметку"
                                        >
                                            <Check className="w-3 h-3 mr-1" /> Отменить
                                        </Button>

                                        {nextLessonId ? (
                                            <Button asChild size="lg" className="rounded-full px-8 gap-2 bg-primary hover:bg-primary/90 shadow-md animate-in fade-in zoom-in duration-300">
                                                <Link href={`/courses/${id}/lessons/${nextLessonId}`}>
                                                    Следующий урок <ChevronRight className="w-4 h-4" />
                                                </Link>
                                            </Button>
                                        ) : (
                                            <Button asChild size="lg" className="rounded-full px-8 gap-2 bg-primary hover:bg-primary/90 shadow-md animate-in fade-in zoom-in duration-300">
                                                <Link href="/dashboard">
                                                    Завершить курс <CheckCircle className="w-4 h-4" />
                                                </Link>
                                            </Button>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Sidebar (Lesson List) */}
            <div className="w-full lg:w-80 border-l bg-surface hidden lg:flex flex-col h-full overflow-hidden">
                <div className="p-4 border-b font-semibold text-lg flex items-center justify-between">
                    <span>Содержание курса</span>
                    <Badge variant="outline" className="text-xs font-normal">
                        {progressPercent}%
                    </Badge>
                </div>
                <ScrollArea className="flex-1 min-h-0">
                    <div className="p-4 space-y-6">
                        {modules.map((module) => (
                            <div key={module.id} className="space-y-2">
                                <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider pl-2">
                                    Модуль {module.order_index}: {module.title}
                                </h3>
                                <div className="space-y-1">
                                    {module.lessons?.sort((a, b) => a.order_index - b.order_index).map((l) => {
                                        const isCurrent = l.id === lessonId;
                                        const isCompleted = completedLessonIds.includes(l.id);

                                        return (
                                            <Link
                                                key={l.id}
                                                href={`/courses/${id}/lessons/${l.id}`}
                                                className={cn(
                                                    "flex items-center gap-3 p-3 rounded-lg text-sm transition-colors",
                                                    isCurrent
                                                        ? "bg-primary/10 text-primary font-medium"
                                                        : "hover:bg-slate-50 text-text-primary",
                                                    !isCurrent && !isCompleted && "opacity-60 hover:opacity-100" // Dim unchecked lessons
                                                )}
                                            >
                                                <div className="shrink-0 pt-0.5">
                                                    {isCurrent ? (
                                                        <div className="w-4 h-4 rounded-full border-2 border-primary flex items-center justify-center">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                                                        </div>
                                                    ) : isCompleted ? (
                                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                                    ) : (
                                                        <div className="w-4 h-4 rounded-full border-2 border-text-secondary/30" />
                                                    )}
                                                </div>
                                                <span className="line-clamp-2">{l.order_index}. {l.title}</span>
                                                <span className="ml-auto text-xs text-text-secondary shrink-0">
                                                    {formatDuration(l.duration_seconds)}
                                                </span>
                                            </Link>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </div>
        </div>
    );
}
