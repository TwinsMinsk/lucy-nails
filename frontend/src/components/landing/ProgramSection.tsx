import { ProgramModuleCard } from "@/components/landing/ProgramModuleCard";
import type { Module } from "@/components/course/ModuleList";
import type { ModuleResponse } from "@/lib/api";

export interface ProgramSectionProps {
  apiModules: ModuleResponse[] | null;
  /** Fallback с главной (если API недоступен или без промо) */
  staticModules: Module[];
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "";
  const m = Math.round(seconds / 60);
  if (m <= 0) return "~1 мин";
  return `${m} мин`;
}

/** Тексты запасного варианта по названию модуля (первый урок на лендинге = названию темы). */
const STATIC_COPY: Record<
  string,
  { description: string; bullets: string[] }
> = {
  Фольга: {
    description:
      "Фольга и поталь: базовые отпечатки, сложные комбинации и выразительный блеск.",
    bullets: ["Техника отпечатка", "Работа с клеем и топом", "Комбинации с декором"],
  },
  Аквариум: {
    description:
      "«Живой» дизайн: объём, глубина и аккуратная сборка аквариумной композиции.",
    bullets: ["Подготовка базы", "Работа с включениями", "Финиш без потери объёма"],
  },
  Втирка: {
    description: "Втирка: ровная передача цвета, переливы и выразительные акценты.",
    bullets: ["Выбор втирки", "Растушёвка без полос", "Топ и долговечность"],
  },
  "Слайдеры и наклейки": {
    description: "Слайдеры и наклейки: быстрая графика и аккуратная фиксация.",
    bullets: ["Подбор размера", "Перенос без складок", "Запечатывание и блик"],
  },
  Френч: {
    description: "Френч: линии, формы и современные вариации классики.",
    bullets: ["Линия улыбки", "Ровные боковые линии", "Креативные модификации"],
  },
  Пигменты: {
    description: "Пигменты: насыщение, мягкие переходы и чистый цвет без разводов.",
    bullets: ["Работа с кистью/аппликатором", "Наслоение", "Сочетание с топом"],
  },
  Стемпинг: {
    description: "Стемпинг: чёткий отпечаток, контраст и быстрые узоры.",
    bullets: ["Подбор лака и штампа", "Техника переноса", "Исправление огрехов"],
  },
  "Стразы/объемные украшения": {
    description: "Стразы и объёмный декор: посадка, баланс и устойчивое крепление.",
    bullets: ["Компоновка", "Клей и фиксация", "Финиш без цепляния"],
  },
  Текстуры: {
    description: "Текстуры: матовые и рельефные акценты для премиального вида.",
    bullets: ["Подбор материала", "Рельеф без лишней толщины", "Топ и износ"],
  },
  Градиент: {
    description: "Градиент: плавные переходы цвета без полос и «ступенек».",
    bullets: ["Блендинг", "Молочные и пастельные градиенты", "Чистый торец"],
  },
  Аэрография: {
    description: "Аэрография: мягкие контуры, воздушность и контроль распыления.",
    bullets: ["Настройка потока", "Трафареты и свободная роспись", "Фиксация слоя"],
  },
};

export function ProgramSection({ apiModules, staticModules }: ProgramSectionProps) {
  const useApi = Boolean(apiModules && apiModules.length > 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
      {useApi
        ? apiModules!.map((mod, idx) => {
            const lesson = mod.lessons?.[0];
            const promoId = lesson?.promo_kinescope_video_id ?? null;
            const poster = lesson?.promo_poster_url ?? null;
            const description =
              lesson?.promo_description?.trim() ||
              STATIC_COPY[mod.title]?.description ||
              mod.description ||
              "";
            const bullets =
              lesson?.promo_bullets?.length ? lesson.promo_bullets : STATIC_COPY[mod.title]?.bullets || [];
            const durationLabel = lesson
              ? formatDuration(lesson.duration_seconds)
              : undefined;

            return (
              <ProgramModuleCard
                key={mod.id}
                orderIndex={idx + 1}
                title={mod.title}
                description={description}
                bullets={bullets}
                promoVideoId={promoId}
                posterUrl={poster}
                durationLabel={durationLabel}
              />
            );
          })
        : staticModules.map((mod, idx) => {
            const lesson = mod.lessons[0];
            const copy = STATIC_COPY[mod.title];
            const description = copy?.description ?? "";
            const bullets = copy?.bullets ?? [];

            return (
              <ProgramModuleCard
                key={mod.id}
                orderIndex={idx + 1}
                title={mod.title}
                description={description}
                bullets={bullets}
                promoVideoId={null}
                posterUrl={null}
                durationLabel={lesson?.duration}
              />
            );
          })}
    </div>
  );
}
