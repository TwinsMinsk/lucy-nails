import Link from "next/link";
import type { Metadata } from "next";
import {
  Sparkles,
  Star,
  Award,
  CheckCircle,
  Play
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ModuleList, Module } from "@/components/course/ModuleList";
import Image from "next/image";
import { NailsGallery } from "@/components/landing/NailsGallery";
import { PaymentButton } from "@/components/landing/PaymentButton";
import { getPublishedCourses } from "@/lib/api";

export const metadata: Metadata = {
  title: "Онлайн-курс дизайна ногтей",
  description: "Премиальный онлайн-курс по современным техникам дизайна ногтей: фольга, градиент, френч, текстуры, стемпинг и 3D-дизайн.",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Онлайн-курс дизайна ногтей",
    description: "Премиальный онлайн-курс по современным техникам дизайна ногтей.",
    url: "/",
  },
};

// Full course data based on CONTENT.md & PRD.md
const COURSE_DATA = {
  title: "Освойте искусство маникюра: Премиальный онлайн-курс",
  subtitle: "Раскройте свой творческий потенциал и станьте профессиональным мастером маникюра. От базовых техник до сложного 3D-дизайна.",
  description:
    "Практический курс для мастеров маникюра. Освойте современные техники дизайна: от аквариума и френча до стемпинга, текстур и объемных украшений.",
  duration: "~4,5 часа",
  lessonsCount: 11,
  level: "Для начинающих и опытных",
  certificate: false,
  prices: {
    self: 5900,
    support: 11900,
  },
  modules: [
    {
      id: "1",
      title: "Фольга",
      lessons: [
        { id: "1.1", title: "Фольга", duration: "скоро" },
      ],
    },
    {
      id: "2",
      title: "Аквариум",
      lessons: [
        { id: "2.1", title: "Аквариум", duration: "30 мин" },
      ],
    },
    {
      id: "3",
      title: "Втирка",
      lessons: [
        { id: "3.1", title: "Втирка", duration: "24 мин" },
      ],
    },
    {
      id: "4",
      title: "Слайдеры и наклейки",
      lessons: [
        { id: "4.1", title: "Слайдеры и наклейки", duration: "21 мин" },
      ],
    },
    {
      id: "5",
      title: "Френч",
      lessons: [
        { id: "5.1", title: "Френч", duration: "42 мин" },
      ],
    },
    {
      id: "6",
      title: "Пигменты",
      lessons: [
        { id: "6.1", title: "Пигменты", duration: "13 мин" },
      ],
    },
    {
      id: "7",
      title: "Стемпинг",
      lessons: [
        { id: "7.1", title: "Стемпинг", duration: "18 мин" },
      ],
    },
    {
      id: "8",
      title: "Стразы/объемные украшения",
      lessons: [
        { id: "8.1", title: "Стразы/объемные украшения", duration: "47 мин" },
      ],
    },
    {
      id: "9",
      title: "Текстуры",
      lessons: [
        { id: "9.1", title: "Текстуры", duration: "25 мин" },
      ],
    },
    {
      id: "10",
      title: "Градиент",
      lessons: [
        { id: "10.1", title: "Градиент", duration: "25 мин" },
      ],
    },
    {
      id: "11",
      title: "Аэрография",
      lessons: [
        { id: "11.1", title: "Аэрография", duration: "19 мин" },
      ],
    },
  ] as Module[],
};

const galleryImages = [
  "/nails-gallery/design-1.svg",
  "/nails-gallery/design-2.svg",
  "/nails-gallery/design-3.svg",
  "/nails-gallery/design-4.svg",
];

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

  const course = { ...COURSE_DATA, prices };

  return (
    <div className="flex flex-col min-h-screen bg-[#FDFBF9]">
      {/* Hero Section */}
      <section id="about" className="relative overflow-hidden min-h-[calc(100vh-70px)] flex items-center py-8 lg:py-0 bg-[#fff1f4]">

        <div className="container px-4 md:px-6 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-stretch">

            {/* Left Content */}
            <div className="p-6 md:p-10 lg:p-0 relative w-full lg:col-span-7 lg:ml-0 mx-auto h-full flex flex-col justify-center">


              <div className="space-y-6 relative">
                <div className="inline-flex items-center gap-2.5 px-5 py-2 rounded-full bg-gradient-to-r from-[#D4AF37] via-[#FFF3AD] to-[#BFA15F] border border-[#D4AF37]/30 shadow-[0_4px_15px_rgba(191,161,95,0.3)] mb-4 group/badge transition-transform hover:scale-105 duration-300">
                  <Sparkles className="w-4 h-4 text-[#5A4B4B] animate-pulse" />
                  <span className="text-[#5A4B4B] text-[11px] font-bold tracking-[0.2em] uppercase">
                    Онлайн-курс
                  </span>
                </div>
                <h1 className="font-serif text-4xl md:text-5xl lg:text-6xl leading-[1.05] text-text-primary tracking-tight">
                  {course.title}
                </h1>
                <p className="text-lg md:text-xl text-text-secondary leading-relaxed">
                  {course.subtitle}
                </p>
                <Button asChild className="relative overflow-hidden group rounded-full text-sm uppercase tracking-[0.2em] font-bold px-16 py-6 h-auto bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white hover:to-[#db3f6e] transition-all duration-500 shadow-[0_10px_25px_rgba(219,63,110,0.35)] hover:shadow-[0_20px_40px_rgba(219,63,110,0.5)] hover:-translate-y-1 mt-8 border-none ring-1 ring-white/20">
                  <Link href="#pricing">
                    <span className="relative z-10 drop-shadow-md">Начать обучение</span>
                    <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/30 to-transparent z-0" />
                  </Link>
                </Button>
              </div>
            </div>

            {/* Right Image & Stats */}
            <div className="relative lg:col-span-5 group/image flex flex-col justify-center">
              <div className="relative aspect-[4/5] md:aspect-square lg:aspect-[4/5] w-full max-w-md mx-auto lg:ml-auto rounded-[2.5rem] overflow-hidden shadow-[0_0_40px_rgba(0,0,0,0.25),0_30px_60px_rgba(0,0,0,0.6)] border-b-[12px] border-black/10 transition-transform duration-500 hover:-translate-y-3 hover:shadow-[0_0_50px_rgba(0,0,0,0.3),0_40px_80px_rgba(0,0,0,0.7)]">
                <div className="w-full h-full bg-[#EBC8C8] relative">
                  <Image
                    src="/instructor-placeholder.svg"
                    alt="Instructor"
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
            <h2 className="font-serif text-4xl md:text-5xl text-text-primary mb-4">
              Программа курса
            </h2>
            <div className="w-16 h-1 bg-primary mx-auto rounded-full opacity-50" />
          </div>

          <div className="max-w-4xl mx-auto">
            {/* Using ModuleList but wrapping nicely */}
            <div className="bg-transparent space-y-4">
              <ModuleList modules={course.modules} />
            </div>
          </div>
        </div>
      </section>

      {/* Gallery Section */}
      <section id="reviews" className="py-24 bg-[#fff1f4] overflow-hidden">
        <div className="container px-4 md:px-6 mb-12">
          <h2 className="font-serif text-4xl md:text-5xl text-text-primary text-center">
            Галерея работ
          </h2>
          <p className="text-center text-text-secondary mt-4 max-w-2xl mx-auto">
            Вдохновитесь примерами работ, которые вы научитесь создавать на нашем курсе.
            От классики до самых смелых трендов.
          </p>
        </div>

        <NailsGallery images={galleryImages} />
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 bg-white">
        <div className="container px-4 md:px-6">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl md:text-5xl text-text-primary mb-4">
              Тарифы
            </h2>
            {!primaryCourseId && (
              <p className="text-sm text-text-secondary mt-3">
                Оплата временно недоступна: опубликованный курс не загрузился. Попробуйте обновить страницу.
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto items-start">

            {/* Tariff: Self */}
            {/* Tariff: Self */}
            <Card className="border-2 border-[#D4AF37] shadow-[0_30px_90px_rgba(212,175,55,0.18)] hover:shadow-[0_40px_110px_rgba(212,175,55,0.28)] hover:-translate-y-2 transition-all duration-500 rounded-[2.5rem] p-4 bg-white">
              <CardHeader className="text-center pt-8 pb-4">
                <CardTitle className="font-serif text-2xl text-text-primary">Самостоятельный</CardTitle>
                <div className="flex items-baseline justify-center gap-1 font-serif text-5xl text-text-primary mt-4">
                  {course.prices.self.toLocaleString()} ₽
                </div>
                <p className="text-sm text-text-secondary mt-2">Доступ на 30 дней</p>
              </CardHeader>
              <CardContent className="space-y-6 px-8 pb-8">
                <div className="w-full h-px bg-border/50" />
                <ul className="space-y-4 text-text-secondary">
                  <li className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-[#D4AF37] shrink-0 fill-[#D4AF37]/10" />
                    <span>Доступ ко всем видео-урокам</span>
                  </li>
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
                  <CardTitle className="font-serif text-2xl text-text-primary">С поддержкой</CardTitle>
                  <div className="flex items-baseline justify-center gap-1 font-serif text-5xl text-text-primary mt-4">
                    {course.prices.support.toLocaleString()} ₽
                  </div>
                  <p className="text-sm text-text-secondary mt-2">Доступ на 30 дней</p>
                </CardHeader>
                <CardContent className="space-y-6 px-8 pb-8">
                  <div className="w-full h-px bg-border/50" />
                  <ul className="space-y-4 text-text-secondary">
                    <li className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-[#D4AF37] shrink-0 fill-[#D4AF37]/10" />
                      <span>Доступ ко всем видео-урокам</span>
                    </li>
                    <li className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-[#D4AF37] shrink-0 fill-[#D4AF37]/10" />
                      <span>Закрытый чат с куратором</span>
                    </li>
                    <li className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-[#D4AF37] shrink-0 fill-[#D4AF37]/10" />
                      <span>Обратная связь по работам</span>
                    </li>
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
