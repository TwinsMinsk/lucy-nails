import Link from "next/link";
import type { Metadata } from "next";
import { CheckCircle, Clock, Video, Star, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ModuleList, Module } from "@/components/course/ModuleList";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

import { getPublicCourse, getPublicCourseModules, CourseResponse, ModuleResponse } from "@/lib/api";
import { notFound } from "next/navigation";
import { CoursePaymentCTA } from "@/components/course/CoursePaymentCTA";
import { landingCourse } from "@/lib/landing/course-content";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
    const { id } = await params;

    try {
        const course = await getPublicCourse(id);
        return {
            title: course.title,
            description: course.description || "Онлайн-курс Lucy Nails Academy по дизайну ногтей.",
            alternates: {
                canonical: `/courses/${id}`,
            },
            openGraph: {
                title: course.title,
                description: course.description || "Онлайн-курс Lucy Nails Academy по дизайну ногтей.",
                url: `/courses/${id}`,
                images: course.cover_image_url ? [course.cover_image_url] : undefined,
            },
        };
    } catch {
        return {
            title: "Курс не найден",
        };
    }
}

// Helper to format duration like "20 мин" or "1 час"
const formatDuration = (seconds?: number) => {
    if (!seconds) return "0 мин";
    const mins = Math.floor(seconds / 60);
    if (mins >= 60) {
        return `${Math.floor(mins / 60)} ч ${mins % 60} мин`;
    }
    return `${mins} мин`;
};

// Map API data to component props
const mapModules = (apiModules: ModuleResponse[]): Module[] => {
    return apiModules.map(m => ({
        id: m.id,
        title: m.title,
        lessons: m.lessons?.map(l => ({
            id: l.id,
            title: l.title,
            duration: formatDuration(l.duration_seconds)
        })) || []
    }));
};

export default async function CoursePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;

    let courseData: CourseResponse;
    let modulesData: ModuleResponse[] = [];

    try {
        [courseData, modulesData] = await Promise.all([
            getPublicCourse(id),
            getPublicCourseModules(id)
        ]);
    } catch (error) {
        // If course not found or API error
        console.error("Error fetching course data:", error);
        notFound();
    }

    // Combine API data with some UI defaults or mapped values
    const course = {
        ...courseData,
        level: "Для всех уровней", // Placeholder or add to DB
        certificate: false, // Сертификаты вынесены в post-MVP.
        prices: {
            self: courseData.price_self,
            support: courseData.price_support,
        },
        duration: `~${Math.ceil((courseData.duration_seconds || 0) / 3600)} часов`, // Estimate from metadata if available? Or just hide
        lessonsCount: modulesData.reduce((acc, m) => acc + (m.lessons?.length || 0), 0),
        modules: mapModules(modulesData),
    };

    return (
        <div className="min-h-screen bg-background pb-20">
            {/* Course Header - Full Width */}
            <div className="bg-primary/5 border-b border-primary/10">
                <div className="container px-4 py-10 md:py-16">
                    <div className="flex flex-col gap-6 md:items-start justify-between">
                        <div className="space-y-6 max-w-4xl">
                            <div className="flex flex-wrap gap-2">
                                <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
                                    {course.level}
                                </Badge>
                                {course.certificate && (
                                    <Badge variant="outline" className="border-primary/20 text-primary gap-1">
                                        <Star className="w-3 h-3" /> Сертификат
                                    </Badge>
                                )}
                            </div>

                            <h1 className="text-3xl md:text-5xl font-bold tracking-tight text-text-primary">
                                {course.title}
                            </h1>

                            <p className="text-lg text-text-secondary max-w-2xl leading-relaxed">
                                {course.description}
                            </p>

                            <div className="flex flex-wrap gap-4 text-sm font-medium text-text-secondary">
                                <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full border shadow-sm">
                                    <Clock className="w-4 h-4 text-primary" />
                                    {course.duration}
                                </div>
                                <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full border shadow-sm">
                                    <Video className="w-4 h-4 text-primary" />
                                    {course.lessonsCount} уроков
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Grid Layout */}
            <div className="container px-4 py-8 md:py-12">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 lg:gap-12 relative">

                    {/* Left Column: Modules & Detailed Rates */}
                    <div className="lg:col-span-2 space-y-12 order-2 lg:order-1">
                        {/* Program */}
                        <section>
                            <ModuleList modules={course.modules} />
                        </section>

                        {/* Detailed Pricing / Rates */}
                        <section id="rates" className="scroll-mt-20">
                            <h3 className="text-2xl font-bold mb-6">Тарифы обучения</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Rate 1 */}
                                <Card className="flex flex-col h-full border hover:border-primary/50 transition-colors">
                                    <CardHeader>
                                        <CardTitle className="text-xl">Самостоятельный</CardTitle>
                                        <div className="text-3xl font-bold text-primary py-2">
                                            {course.prices.self.toLocaleString('ru-RU')} ₽
                                        </div>
                                    </CardHeader>
                                    <CardContent className="flex-1 space-y-4">
                                        <ul className="space-y-3">
                                            <li className="flex gap-3 text-sm">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Доступ ко всем урокам (30 дней)</span>
                                            </li>
                                            <li className="flex gap-3 text-sm">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Самостоятельная отработка по конспектам</span>
                                            </li>
                                            <li className="flex gap-3 text-sm opacity-50">
                                                <ShieldCheck className="w-5 h-5 shrink-0" />
                                                <span className="line-through">Чат с куратором</span>
                                            </li>
                                        </ul>
                                    </CardContent>
                                    <CardFooter>
                                        <CoursePaymentCTA courseId={id} tariff="self" className="w-full h-12 rounded-lg text-sm uppercase tracking-wide font-bold bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white">
                                            Выбрать тариф
                                        </CoursePaymentCTA>
                                    </CardFooter>
                                </Card>

                                {/* Rate 2 */}
                                <Card className="flex flex-col h-full border-2 border-primary/20 bg-primary/5 relative overflow-hidden">
                                    <div className="absolute top-0 right-0 bg-primary text-white text-xs font-bold px-3 py-1 rounded-bl-lg">
                                        Популярный
                                    </div>
                                    <CardHeader>
                                        <CardTitle className="text-xl">С поддержкой</CardTitle>
                                        <div className="text-3xl font-bold text-primary py-2">
                                        {course.prices.support.toLocaleString('ru-RU')} ₽
                                        </div>
                                    </CardHeader>
                                    <CardContent className="flex-1 space-y-4">
                                        <ul className="space-y-3">
                                            <li className="flex gap-3 text-sm">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Доступ ко всем урокам (30 дней)</span>
                                            </li>
                                            <li className="flex gap-3 text-sm">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Проверка домашних заданий</span>
                                            </li>
                                            <li className="flex gap-3 text-sm font-medium">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Закрытый чат с куратором</span>
                                            </li>
                                            <li className="flex gap-3 text-sm">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Подсказки по материалам и ошибкам</span>
                                            </li>
                                        </ul>
                                    </CardContent>
                                    <CardFooter>
                                        <CoursePaymentCTA courseId={id} tariff="support" className="w-full h-12 rounded-lg text-sm uppercase tracking-wide font-bold bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white shadow-lg shadow-primary/20">
                                            Выбрать тариф
                                        </CoursePaymentCTA>
                                    </CardFooter>
                                </Card>
                            </div>
                        </section>
                    </div>

                    {/* Right Column: Sticky Sidebar (Desktop Only) */}
                    <aside className="hidden lg:block lg:col-span-1 relative order-1 lg:order-2">
                        <div className="sticky top-24 space-y-6">
                            <Card className="border-primary/20 shadow-lg overflow-hidden">
                                <div className="bg-primary/5 p-6 border-b border-primary/10 text-center">
                                    <p className="text-text-secondary mb-1">Стоимость обучения</p>
                                    <div className="flex items-baseline justify-center gap-2">
                                        <span className="text-3xl font-bold text-primary">
                                            {course.prices.self.toLocaleString('ru-RU')} ₽
                                        </span>
                                    </div>
                                </div>
                                <CardContent className="p-6 space-y-6">
                                    <ul className="space-y-3">
                                        <li className="flex items-start gap-3 text-sm text-text-primary">
                                            <CheckCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                                            <span>Доступ ко всем материалам курса</span>
                                        </li>
                                        <li className="flex items-start gap-3 text-sm text-text-primary">
                                            <CheckCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                                            <span>Удобная платформа обучения</span>
                                        </li>
                                        <li className="flex items-start gap-3 text-sm text-text-primary">
                                            <CheckCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                                            <span>Просмотр с любого устройства</span>
                                        </li>
                                    </ul>
                                    <Button className="w-full text-lg h-12 rounded-xl shadow-md" asChild>
                                        <Link href="#rates">Начать обучение</Link>
                                    </Button>

                                    <p className="text-xs text-center text-text-secondary">
                                        {landingCourse.supportNote}
                                    </p>
                                </CardContent>
                            </Card>
                        </div>
                    </aside>

                </div>
            </div>

            {/* Mobile Sticky CTA - Hidden on Desktop */}
            <div className="fixed bottom-0 left-0 right-0 p-4 bg-white/90 backdrop-blur-md border-t lg:hidden z-50">
                <div className="flex items-center justify-between gap-4 max-w-md mx-auto">
                    <div className="flex flex-col">
                        <span className="text-xs text-text-secondary">Стоимость от</span>
                        <span className="font-bold text-lg leading-tight">{course.prices.self.toLocaleString('ru-RU')} ₽</span>
                    </div>
                    <Button size="lg" className="rounded-full shadow-lg" asChild>
                        <Link href="#rates">
                            Купить курс
                        </Link>
                    </Button>
                </div>
            </div>
        </div>
    );
}
