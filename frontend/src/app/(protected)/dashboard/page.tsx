"use client"

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookOpen, CalendarClock, Loader2, MessageCircle, PlayCircle } from "lucide-react";
import Image from "next/image";

import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { getMyCourses, getMe, isAuthError, MyCourseResponse, UserResponse } from "@/lib/api";
import { toast } from "sonner";

export default function DashboardPage() {
    const router = useRouter();
    const [user, setUser] = useState<UserResponse | null>(null);
    const [courses, setCourses] = useState<MyCourseResponse[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Получаем данные пользователя и его курсы
                const [userData, coursesData] = await Promise.all([
                    getMe(),
                    getMyCourses(),
                ]);

                setUser(userData);
                setCourses(coursesData);
            } catch (error) {
                if (isAuthError(error)) {
                    router.push("/auth/login");
                    return;
                }
                const errorMessage = error instanceof Error ? error.message : "Ошибка загрузки данных";
                toast.error("Ошибка", {
                    description: errorMessage,
                });
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [router]);

    if (isLoading) {
        return (
            <div className="container px-4 py-8 md:py-12 flex items-center justify-center min-h-[400px]">
                <div className="text-center space-y-4">
                    <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto" />
                    <p className="text-text-secondary">Загрузка данных...</p>
                </div>
            </div>
        );
    }

    const userName = user?.email?.split("@")[0] || "Пользователь";

    const formatAccessLeft = (expiresAt?: string | null) => {
        if (!expiresAt) return null;
        const diff = new Date(expiresAt).getTime() - Date.now();
        const days = Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
        if (days === 0) return "доступ заканчивается сегодня";
        if (days === 1) return "остался 1 день";
        if (days < 5) return `осталось ${days} дня`;
        return `осталось ${days} дней`;
    };

    return (
        <div className="container px-4 py-8 md:py-12 space-y-8">
            {/* Header Section */}
            <div className="rounded-[2rem] bg-[#fff1f4] border border-primary/20 p-6 md:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-2">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-text-secondary">
                        Личный кабинет
                    </p>
                    <h1 className="font-serif text-3xl md:text-4xl text-text-primary">
                        Добро пожаловать, {userName}!
                    </h1>
                    <p className="text-text-secondary text-lg max-w-2xl">
                        Здесь собраны ваши уроки, прогресс и быстрый переход к следующей отработке.
                    </p>
                </div>
                <Button asChild className="rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white">
                    <Link href="/">Посмотреть программу</Link>
                </Button>
            </div>

            {/* Courses Grid */}
            <section>
                <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
                    <BookOpen className="w-6 h-6 text-primary" />
                    Мои курсы
                </h2>

                {courses.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {courses.map((course) => {
                            const accessLeft = formatAccessLeft(course.expires_at);
                            const continueLabel = course.progress > 0 ? "Продолжить обучение" : "Начать с первого урока";

                            return (
                                <Card key={course.id} className="flex flex-col hover:shadow-lg transition-shadow border-primary/10">
                                    {/* Banner Image */}
                                    <div className="aspect-video w-full bg-primary/5 relative overflow-hidden rounded-t-xl group">
                                        {course.cover_image_url ? (
                                            <Image
                                                src={course.cover_image_url}
                                                alt={course.title}
                                                fill
                                                className="object-cover transition-transform duration-500 group-hover:scale-110"
                                            />
                                        ) : (
                                            <div className="absolute inset-0 flex items-center justify-center text-primary/20 group-hover:text-primary/40 transition-colors">
                                                <BookOpen className="w-12 h-12" />
                                            </div>
                                        )}
                                    </div>

                                    <CardHeader className="pb-3">
                                        <CardTitle className="text-xl line-clamp-3 leading-tight min-h-[1.5em]" title={course.title}>
                                            {course.title}
                                        </CardTitle>
                                        <CardDescription className="line-clamp-2">
                                            {course.description}
                                        </CardDescription>
                                    </CardHeader>

                                    <CardContent className="flex-1 space-y-4">
                                        {course.expires_at && (
                                            <div className="flex items-center gap-2 rounded-xl bg-[#fff1f4] px-3 py-2 text-xs text-text-secondary">
                                                <CalendarClock className="w-4 h-4 text-[#D4AF37]" />
                                                <span>
                                                    Доступ до{" "}
                                                    <span className="font-medium text-text-primary">
                                                        {new Date(course.expires_at).toLocaleDateString("ru-RU")}
                                                    </span>
                                                    {accessLeft ? `, ${accessLeft}` : ""}
                                                </span>
                                            </div>
                                        )}
                                        {course.tariff && (
                                            <p className="text-xs text-text-secondary">
                                                Тариф:{" "}
                                                <span className="font-medium text-text-primary">
                                                    {course.tariff === "support" ? "С поддержкой" : "Самостоятельный"}
                                                </span>
                                            </p>
                                        )}
                                        {course.support_chat_url && (
                                            <a
                                                href={course.support_chat_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center justify-center w-full rounded-lg border border-primary/30 bg-primary/5 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10 transition-colors"
                                            >
                                                <MessageCircle className="w-4 h-4 mr-2" />
                                                Чат с куратором в Telegram
                                            </a>
                                        )}
                                        <div className="space-y-2">
                                            <div className="flex justify-between text-sm">
                                                <span className="font-medium text-text-primary">
                                                    {course.progress}% завершено
                                                </span>
                                                <span className="text-text-secondary">
                                                    {course.completed_lessons}/{course.total_lessons} уроков
                                                </span>
                                            </div>
                                            <Progress value={course.progress} className="h-2" />
                                        </div>

                                        {course.last_lesson_title && (
                                            <div className="p-3 bg-secondary/50 rounded-lg text-sm text-text-secondary border border-border/50">
                                                <span className="font-medium block text-text-primary mb-1 text-xs uppercase tracking-wider opacity-70">
                                                    Сейчас проходите:
                                                </span>
                                                {course.last_lesson_title}
                                            </div>
                                        )}

                                        {!course.last_lesson_title && course.total_lessons > 0 && (
                                            <div className="p-3 bg-secondary/50 rounded-lg text-sm text-text-secondary border border-border/50">
                                                <span className="font-medium block text-text-primary mb-1 text-xs uppercase tracking-wider opacity-70">
                                                    Рекомендуемый старт:
                                                </span>
                                                Начните с первого урока и отмечайте прогресс после отработки.
                                            </div>
                                        )}
                                    </CardContent>

                                    <CardFooter className="pt-2">
                                        <Button className="w-full gap-2 group" asChild>
                                            <Link href={course.last_lesson_id ? `/courses/${course.id}/lessons/${course.last_lesson_id}` : `/courses/${course.id}`}>
                                                <PlayCircle className="w-4 h-4 transition-all duration-300" />
                                                {continueLabel}
                                            </Link>
                                        </Button>
                                    </CardFooter>
                                </Card>
                            );
                        })}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-16 text-center bg-surface border rounded-[2rem] border-dashed px-6">
                        <div className="bg-primary/10 p-4 rounded-full mb-4">
                            <BookOpen className="w-8 h-8 text-primary" />
                        </div>
                        <h3 className="font-serif text-2xl text-text-primary mb-2">У вас пока нет открытого курса</h3>
                        <p className="text-text-secondary max-w-sm mb-6">
                            Вы можете оплатить курс на главной странице без регистрации. После оплаты данные для входа придут на email.
                        </p>
                        <Button asChild className="rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white">
                            <Link href="/">Перейти в каталог</Link>
                        </Button>
                    </div>
                )}
            </section>
        </div>
    );
}
