"use client"

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BookOpen, Loader2 } from "lucide-react";
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

    return (
        <div className="container px-4 py-8 md:py-12 space-y-8">
            {/* Header Section */}
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl md:text-4xl font-bold text-text-primary">
                    Добро пожаловать, {userName}!
                </h1>
                <p className="text-text-secondary text-lg">
                    Готовы продолжить обучение?
                </p>
            </div>

            {/* Courses Grid */}
            <section>
                <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
                    <BookOpen className="w-6 h-6 text-primary" />
                    Мои курсы
                </h2>

                {courses.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {courses.map((course) => (
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
                                        <p className="text-xs text-text-secondary">
                                            Доступ до{" "}
                                            <span className="font-medium text-text-primary">
                                                {new Date(course.expires_at).toLocaleDateString("ru-RU")}
                                            </span>
                                        </p>
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
                                </CardContent>

                                <CardFooter className="pt-2">
                                    <Button className="w-full gap-2 group" asChild>
                                        <Link href={course.last_lesson_id ? `/courses/${course.id}/lessons/${course.last_lesson_id}` : `/courses/${course.id}`}>
                                            <svg
                                                className="w-4 h-4 transition-all duration-300"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="currentColor"
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                            >
                                                <circle cx="12" cy="12" r="10" className="group-hover:fill-current" />
                                                <polygon points="10 8 16 12 10 16 10 8" className="group-hover:fill-white group-hover:stroke-white" />
                                            </svg>
                                            Продолжить обучение
                                        </Link>
                                    </Button>
                                </CardFooter>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center py-16 text-center bg-surface border rounded-xl border-dashed">
                        <div className="bg-primary/10 p-4 rounded-full mb-4">
                            <BookOpen className="w-8 h-8 text-primary" />
                        </div>
                        <h3 className="text-xl font-medium mb-2">У вас пока нет курсов</h3>
                        <p className="text-text-secondary max-w-sm mb-6">
                            Начните свое обучение прямо сейчас, выбрав подходящий курс в каталоге.
                        </p>
                        <Button asChild>
                            <Link href="/">Перейти в каталог</Link>
                        </Button>
                    </div>
                )}
            </section>
        </div>
    );
}
