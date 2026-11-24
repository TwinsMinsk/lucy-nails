import Link from "next/link";
import type { Metadata } from "next";
import { CheckCircle, Clock, Video, Award } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ModuleList, Module } from "@/components/course/ModuleList";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

import { ApiError, getPublicCourse, getPublicCourseModules, CourseResponse, ModuleResponse } from "@/lib/api";
import { notFound } from "next/navigation";
import { CoursePaymentCTA } from "@/components/course/CoursePaymentCTA";
import { landingCourse } from "@/lib/landing/course-content";
import { getLandingCourseId } from "@/lib/landing/loader";
import { formatCourseDuration, formatDays, formatLessonDuration } from "@/lib/format";
import { baseOpenGraph } from "@/lib/seo";

// The API takes a UUID and answers 422 to anything else, so such an id cannot be a course.
const COURSE_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Only a 404 from the course request means "no such course". Any other failure is
 * temporary and must reach the error boundary as a server error, not a cached 404.
 */
async function loadCourse(id: string): Promise<CourseResponse> {
    if (!COURSE_ID_PATTERN.test(id)) notFound();
    try {
        return await getPublicCourse(id);
    } catch (error) {
        if (error instanceof ApiError && error.status === 404) notFound();
        throw error;
    }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
    const { id } = await params;

    // getLandingCourseId throws while the landing course is unknown, so an outage
    // never flips the canonical of the landing course to its own URL.
    const [course, landingCourseId] = await Promise.all([loadCourse(id), getLandingCourseId()]);
    const description = course.description || "Онлайн-курс Люси Смирновой по дизайну ногтей.";
    const isLandingCourse = landingCourseId === id;
    // The landing page sells this course with fuller content, so it is the page to index.
    const canonical = isLandingCourse ? "/" : `/courses/${id}`;
    // One offer, one link preview: the landing course shares the prepared 1200x630 image of "/".
    const images = !isLandingCourse && course.cover_image_url ? [course.cover_image_url] : baseOpenGraph.images;
    return {
        title: course.title,
        description,
        alternates: {
            canonical,
        },
        openGraph: {
            ...baseOpenGraph,
            title: course.title,
            description,
            url: canonical,
            images,
        },
        twitter: {
            card: "summary_large_image",
            title: course.title,
            description,
            images,
        },
    };
}

// Map API data to component props
const mapModules = (apiModules: ModuleResponse[]): Module[] => {
    return [...apiModules]
        .sort((a, b) => a.order_index - b.order_index)
        .map(m => ({
            id: m.id,
            title: m.title,
            lessons: [...(m.lessons ?? [])]
                .sort((a, b) => a.order_index - b.order_index)
                .map(l => ({
                    id: l.id,
                    title: l.title,
                    duration: formatLessonDuration(l.duration_seconds)
                }))
        }));
};

export default async function CoursePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;

    const [courseData, modulesData] = await Promise.all([
        loadCourse(id),
        // The programme is secondary: without it the course page still sells the course.
        getPublicCourseModules(id).catch((error: unknown): ModuleResponse[] | null => {
            console.error("Error fetching course modules:", error);
            return null;
        }),
    ]);

    // Combine API data with some UI defaults or mapped values
    const course = {
        ...courseData,
        level: "Для практикующих мастеров",
        certificate: true,
        prices: {
            self: courseData.price_self,
        },
        duration: formatCourseDuration(courseData.total_duration),
        lessonsCount: modulesData
            ? modulesData.reduce((acc, m) => acc + (m.lessons?.length || 0), 0)
            : courseData.lessons_count ?? null,
        modules: modulesData ? mapModules(modulesData) : null,
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
                                        <Award className="w-3 h-3" /> Сертификат
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
                                {course.duration && (
                                    <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full border shadow-sm">
                                        <Clock className="w-4 h-4 text-primary" />
                                        {course.duration}
                                    </div>
                                )}
                                {course.lessonsCount != null && (
                                    <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-full border shadow-sm">
                                        <Video className="w-4 h-4 text-primary" />
                                        {course.lessonsCount} уроков
                                    </div>
                                )}
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
                        {course.modules && (
                            <section>
                                <h2 className="text-2xl font-bold mb-6">Программа курса</h2>
                                <ModuleList modules={course.modules} />
                            </section>
                        )}

                        {/* Detailed Pricing / Rates */}
                        <section id="rates" className="scroll-mt-20">
                            <h2 className="text-2xl font-bold mb-6">Стоимость обучения</h2>
                            <div className="max-w-md">
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
                                                <span>Доступ ко всем урокам ({formatDays(course.access_days || 30)})</span>
                                            </li>
                                            <li className="flex gap-3 text-sm">
                                                <CheckCircle className="w-5 h-5 text-success shrink-0" />
                                                <span>Самостоятельная отработка по конспектам</span>
                                            </li>
                                        </ul>
                                    </CardContent>
                                    <CardFooter className="flex-col gap-3">
                                        <CoursePaymentCTA courseId={id} tariff="self" className="w-full h-12 rounded-lg text-sm uppercase tracking-wide font-bold bg-primary text-primary-foreground hover:bg-primary/90">
                                            Купить курс
                                        </CoursePaymentCTA>
                                        <p className="text-xs text-text-secondary text-center">
                                            Нажимая «Купить курс», вы принимаете условия{" "}
                                            <Link href="/terms" target="_blank" className="underline underline-offset-2 hover:text-text-primary">
                                                оферты
                                            </Link>
                                        </p>
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

            {/* Mobile Sticky CTA - Hidden on Desktop and while the cookie banner, which sits in the same spot, is open */}
            <div data-mobile-buy-bar className="fixed bottom-0 left-0 right-0 p-4 bg-white/90 backdrop-blur-md border-t lg:hidden z-50 [body:has([data-consent-banner])_&]:hidden">
                <div className="flex items-center justify-between gap-4 max-w-md mx-auto">
                    <div className="flex flex-col">
                        <span className="text-xs text-text-secondary">Стоимость</span>
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
