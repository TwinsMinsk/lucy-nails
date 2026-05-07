import Link from "next/link";
import type { Metadata } from "next";
import {
  Sparkles,
  Star,
  Award,
  CheckCircle,
  Play,
  ArrowRight,
  ShieldCheck,
  Video,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Image from "next/image";
import { NailsGallery } from "@/components/landing/NailsGallery";
import { PaymentButton } from "@/components/landing/PaymentButton";
import { ProgramSection } from "@/components/landing/ProgramSection";
import type { Module } from "@/components/course/ModuleList";
import { getPublishedCourses, getPublicCourseModules, type ModuleResponse } from "@/lib/api";
import { galleryItems, landingCourse, programModules } from "@/lib/landing/course-content";

export const metadata: Metadata = {
  title: landingCourse.title,
  description: landingCourse.description,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: landingCourse.title,
    description: landingCourse.description,
    url: "/",
    images: ["/landing/instructor-master.webp"],
  },
};

const staticModules = programModules.map((module, index) => ({
  id: String(index + 1),
  title: module.title,
  lessons: [{ id: `${index + 1}.1`, title: module.title, duration: module.duration }],
})) satisfies Module[];

const COURSE_DATA = {
  title: landingCourse.title,
  subtitle: landingCourse.subtitle,
  description: landingCourse.description,
  duration: landingCourse.duration,
  lessonsCount: landingCourse.lessonsCount,
  level: "Для практикующих мастеров",
  certificate: false,
  prices: {
    self: 5900,
    support: 11900,
  },
  modules: staticModules,
};

export default async function Home() {
  let primaryCourseId: string | null = null;
  let prices = { self: COURSE_DATA.prices.self, support: COURSE_DATA.prices.support };

  try {
    const catalog = await getPublishedCourses();
    if (catalog.total > 0 && catalog.courses[0]) {
      const c = catalog.courses[0];
      primaryCourseId = c.id;
      prices = { self: c.price_self, support: c.price_support };
    }
  } catch {
    // Оставляем цены из статического COURSE_DATA; кнопки оплаты будут заблокированы без курса из API.
  }

  let programModules: ModuleResponse[] | null = null;
  if (primaryCourseId) {
    try {
      programModules = await getPublicCourseModules(primaryCourseId);
    } catch {
      programModules = null;
    }
  }

  const course = { ...COURSE_DATA, prices };

  return (
    <div className="flex flex-col min-h-screen bg-[#FDFBF9]">
      {/* Hero Section */}
      <section id="about" className="relative overflow-hidden min-h-[calc(100vh-70px)] flex items-center py-8 lg:py-0 bg-[#fff1f4]">

        <div className="container px-4 md:px-6 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-stretch">

            {/* Left Content */}
            <div className="p-6 md:p-10 lg:p-0 relative w-full lg:col-span-7 h-full flex flex-col justify-center">
              <div className="space-y-6 relative">
                <div className="inline-flex items-center gap-2.5 px-5 py-2 rounded-full bg-gradient-to-r from-[#D4AF37] via-[#FFF3AD] to-[#BFA15F] border border-[#D4AF37]/30 shadow-[0_4px_15px_rgba(191,161,95,0.3)] mb-4 group/badge transition-transform hover:scale-105 duration-300">
                  <Sparkles className="w-4 h-4 text-[#5A4B4B] animate-pulse" />
                  <span className="text-[#5A4B4B] text-[11px] font-bold tracking-[0.2em] uppercase">
                    Онлайн-курс для мастеров
                  </span>
                </div>
                <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[1.05] text-text-primary tracking-tight">
                  {course.title}
                </h1>
                <p className="text-lg md:text-xl text-text-secondary leading-relaxed">
                  {course.subtitle}
                </p>
                <p className="text-base text-text-secondary/90 leading-relaxed max-w-2xl">
                  {course.description}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl">
                  {landingCourse.heroStats.map((stat) => (
                    <div key={stat.label} className="rounded-2xl bg-white/70 border border-white px-4 py-3 shadow-sm">
                      <div className="font-serif text-2xl text-text-primary">{stat.value}</div>
                      <div className="text-[10px] uppercase tracking-[0.18em] text-text-secondary">{stat.label}</div>
                    </div>
                  ))}
                </div>

                <div className="flex flex-col sm:flex-row gap-3 mt-8">
                  <Button asChild className="relative overflow-hidden group rounded-full text-sm uppercase tracking-[0.2em] font-bold px-10 py-6 h-auto bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white hover:to-[#db3f6e] transition-all duration-500 shadow-[0_10px_25px_rgba(219,63,110,0.35)] hover:shadow-[0_20px_40px_rgba(219,63,110,0.5)] hover:-translate-y-1 border-none ring-1 ring-white/20">
                    <Link href="#pricing">
                      <span className="relative z-10 drop-shadow-md flex items-center gap-2">
                        Выбрать тариф
                        <ArrowRight className="w-4 h-4" />
                      </span>
                      <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/30 to-transparent z-0" />
                    </Link>
                  </Button>
                  <Button asChild variant="outline" className="rounded-full text-sm uppercase tracking-[0.16em] font-bold px-8 py-6 h-auto border-2 border-[#D4AF37]/40 bg-white/70 hover:bg-white">
                    <Link href="#program">
                      Смотреть программу
                    </Link>
                  </Button>
                </div>

                <div className="flex flex-col gap-2 pt-2">
                  {landingCourse.benefits.map((benefit) => (
                    <div key={benefit} className="flex items-start gap-3 text-sm text-text-secondary">
                      <CheckCircle className="w-4 h-4 text-[#D4AF37] shrink-0 mt-0.5 fill-[#D4AF37]/10" />
                      <span>{benefit}</span>
                    </div>
                  ))}
                </div>
                <p className="text-sm text-text-secondary">
                  {landingCourse.audience}
                </p>
              </div>
            </div>

            {/* Right Image & Stats */}
            <div className="relative lg:col-span-5 group/image flex flex-col justify-center">
              <div className="relative aspect-[4/5] md:aspect-square lg:aspect-[4/5] w-full max-w-md mx-auto lg:ml-auto rounded-[2.5rem] overflow-hidden shadow-[0_0_40px_rgba(0,0,0,0.25),0_30px_60px_rgba(0,0,0,0.6)] border-b-[12px] border-black/10 transition-transform duration-500 hover:-translate-y-3 hover:shadow-[0_0_50px_rgba(0,0,0,0.3),0_40px_80px_rgba(0,0,0,0.7)]">
                <div className="w-full h-full bg-[#EBC8C8] relative">
                  <Image
                    src="/landing/instructor-master.webp"
                    alt="Мастер маникюра в студии Lucy Nails Academy"
                    fill
                    className="object-cover"
                    priority
                  />
                </div>
              </div>

              {/* Floating Cards */}
              <div className="absolute bottom-8 left-4 right-4 flex justify-center gap-4 flex-wrap md:flex-nowrap">
                {/* Card 1 */}
                <div className="flex flex-col items-center justify-center bg-white/80 backdrop-blur-md p-4 rounded-2xl shadow-lg w-28 h-28 text-center border border-white/50">
                  <Star className="w-6 h-6 text-text-primary mb-2 stroke-1" />
                  <span className="font-serif text-lg font-bold">{course.modules.length}</span>
                  <span className="text-[10px] uppercase tracking-wider text-text-secondary">Модулей</span>
                </div>
                {/* Card 2 */}
                <div className="flex flex-col items-center justify-center bg-white/80 backdrop-blur-md p-4 rounded-2xl shadow-lg w-28 h-28 text-center border border-white/50">
                  <Play className="w-6 h-6 text-text-primary mb-2 stroke-1 fill-current" />
                  <span className="font-serif text-lg font-bold">{course.lessonsCount}</span>
                  <span className="text-[10px] uppercase tracking-wider text-text-secondary">Уроков</span>
                </div>
                {/* Card 3 */}
                <div className="flex flex-col items-center justify-center bg-white/80 backdrop-blur-md p-4 rounded-2xl shadow-lg w-28 h-28 text-center border border-white/50">
                  <Award className="w-6 h-6 text-text-primary mb-2 stroke-1" />
                  <span className="text-[10px] uppercase tracking-wider text-text-secondary mt-1">30 дней</span>
                  <span className="text-[8px] text-text-secondary/70">доступа</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>


      {/* Program Section */}
      <section id="program" className="py-24 bg-white">
        <div className="container px-4 md:px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 rounded-full bg-[#fff1f4] px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-text-secondary mb-4">
              <Video className="w-4 h-4 text-[#D4AF37]" />
              11 уроков из реальной практики мастера
            </div>
            <h2 className="font-serif text-4xl md:text-5xl text-text-primary mb-4">
              Программа курса
            </h2>
            <p className="text-text-secondary max-w-3xl mx-auto leading-relaxed">
              Каждый модуль построен вокруг конкретной техники: что взять из материалов,
              как подготовить поверхность, где чаще всего ошибаются мастера и как закрепить дизайн,
              чтобы он красиво носился.
            </p>
            <div className="w-16 h-1 bg-primary mx-auto rounded-full opacity-50" />
          </div>

          <div className="max-w-6xl mx-auto">
            <ProgramSection apiModules={programModules} staticModules={course.modules} />
          </div>
        </div>
      </section>

      {/* Gallery Section */}
      <section id="gallery" className="py-24 bg-[#fff1f4] overflow-hidden">
        <div className="container px-4 md:px-6 mb-12">
          <div className="text-center text-xs font-bold uppercase tracking-[0.18em] text-text-secondary mb-3">
            Вдохновение для портфолио
          </div>
          <h2 className="font-serif text-4xl md:text-5xl text-text-primary text-center">
            Галерея работ
          </h2>
          <p className="text-center text-text-secondary mt-4 max-w-2xl mx-auto">
            Добавляйте сюда реальные фотографии из портфолио: подпись покажет технику,
            а будущий ученик сразу увидит, какие работы сможет предлагать клиентам.
          </p>
        </div>

        <NailsGallery items={galleryItems} />
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 bg-white">
        <div className="container px-4 md:px-6">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 rounded-full bg-[#fff1f4] px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-text-secondary mb-4">
              <ShieldCheck className="w-4 h-4 text-[#D4AF37]" />
              Тестовая оплата уже подключена
            </div>
            <h2 className="font-serif text-4xl md:text-5xl text-text-primary mb-4">
              Тарифы
            </h2>
            <p className="text-text-secondary max-w-2xl mx-auto leading-relaxed">
              Выберите формат обучения. Если покупаете без входа в аккаунт, укажите email:
              после подтверждения оплаты туда придут данные для доступа в кабинет.
            </p>
            {!primaryCourseId && (
              <p className="text-sm text-text-secondary mt-3">
                Каталог курсов с сервера не подгрузился, но оплата доступна: будет использован основной
                опубликованный курс. Если сумма не та — обновите страницу.
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto items-start">

            {/* Tariff: Self */}
            <Card className="border-2 border-[#D4AF37] shadow-[0_30px_90px_rgba(212,175,55,0.18)] hover:shadow-[0_40px_110px_rgba(212,175,55,0.28)] hover:-translate-y-2 transition-all duration-500 rounded-[2.5rem] p-4 bg-white">
              <CardHeader className="text-center pt-8 pb-4">
                <CardTitle className="font-serif text-2xl text-text-primary">{landingCourse.tariffs.self.title}</CardTitle>
                <div className="flex items-baseline justify-center gap-1 font-serif text-5xl text-text-primary mt-4">
                  {course.prices.self.toLocaleString()} ₽
                </div>
                <p className="text-sm text-text-secondary mt-2">Доступ на 30 дней</p>
                <p className="text-sm text-text-secondary leading-relaxed mt-4">
                  {landingCourse.tariffs.self.description}
                </p>
              </CardHeader>
              <CardContent className="space-y-6 px-8 pb-8">
                <div className="w-full h-px bg-border/50" />
                <ul className="space-y-4 text-text-secondary">
                  {landingCourse.tariffs.self.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-[#D4AF37] shrink-0 fill-[#D4AF37]/10" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter className="pb-8 px-8">
                <PaymentButton courseId={primaryCourseId} tariff="self">
                  Начать обучение
                </PaymentButton>
              </CardFooter>
            </Card>

            {/* Tariff: Support */}
            <div className="relative">
              {/* Popular Badge */}
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10 bg-[#D4AF37] text-white text-xs font-bold px-4 py-1.5 rounded-full uppercase tracking-widest shadow-lg">
                Популярный
              </div>

              <Card className="border-2 border-[#D4AF37] shadow-[0_35px_100px_rgba(212,175,55,0.22)] hover:shadow-[0_45px_120px_rgba(212,175,55,0.32)] hover:-translate-y-2 transition-all duration-500 rounded-[2.5rem] p-4 bg-[#FFF1F4] relative z-0 scale-105">
                <CardHeader className="text-center pt-10 pb-4">
                  <CardTitle className="font-serif text-2xl text-text-primary">{landingCourse.tariffs.support.title}</CardTitle>
                  <div className="flex items-baseline justify-center gap-1 font-serif text-5xl text-text-primary mt-4">
                    {course.prices.support.toLocaleString()} ₽
                  </div>
                  <p className="text-sm text-text-secondary mt-2">Доступ на 30 дней</p>
                  <p className="text-sm text-text-secondary leading-relaxed mt-4">
                    {landingCourse.tariffs.support.description}
                  </p>
                </CardHeader>
                <CardContent className="space-y-6 px-8 pb-8">
                  <div className="w-full h-px bg-border/50" />
                  <ul className="space-y-4 text-text-secondary">
                    {landingCourse.tariffs.support.features.map((feature) => (
                      <li key={feature} className="flex items-center gap-3">
                        <CheckCircle className="w-5 h-5 text-[#D4AF37] shrink-0 fill-[#D4AF37]/10" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
                <CardFooter className="pb-8 px-8">
                  <PaymentButton courseId={primaryCourseId} tariff="support">
                    Начать обучение
                  </PaymentButton>
                </CardFooter>
              </Card>
            </div>

          </div>
        </div>
      </section>

      {/* Footer is handled by layout */}
    </div>
  );
}
