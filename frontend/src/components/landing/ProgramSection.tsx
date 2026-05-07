import { ProgramModuleCard } from "@/components/landing/ProgramModuleCard";
import type { Module } from "@/components/course/ModuleList";
import type { ModuleResponse } from "@/lib/api";
import { programModules, type ProgramModuleContent } from "@/lib/landing/course-content";

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

const copyByTitle = new Map(programModules.map((module) => [module.title, module]));
const copyByOrder = new Map(programModules.map((module, index) => [index + 1, module]));

function getFallbackCopy(title: string, orderIndex: number): ProgramModuleContent | undefined {
  return copyByTitle.get(title) ?? copyByOrder.get(orderIndex);
}

export function ProgramSection({ apiModules, staticModules }: ProgramSectionProps) {
  const useApi = Boolean(apiModules && apiModules.length > 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
      {useApi
        ? apiModules!.map((mod, idx) => {
            const lesson = mod.lessons?.[0];
            const promoId = lesson?.promo_kinescope_video_id ?? null;
            const poster = lesson?.promo_poster_url ?? null;
            const fallback = getFallbackCopy(mod.title, idx + 1);
            const description =
              lesson?.promo_description?.trim() ||
              fallback?.description ||
              mod.description ||
              "";
            const bullets =
              lesson?.promo_bullets?.length ? lesson.promo_bullets : fallback?.bullets || [];
            const durationLabel = lesson
              ? formatDuration(lesson.duration_seconds)
              : fallback?.duration;

            return (
              <ProgramModuleCard
                key={mod.id}
                orderIndex={idx + 1}
                title={mod.title}
                description={description}
                outcome={fallback?.outcome}
                bullets={bullets}
                mistakes={fallback?.mistakes}
                promoVideoId={promoId}
                posterUrl={poster}
                durationLabel={durationLabel}
              />
            );
          })
        : staticModules.map((mod, idx) => {
            const lesson = mod.lessons[0];
            const copy = getFallbackCopy(mod.title, idx + 1);
            const description = copy?.description ?? "";
            const bullets = copy?.bullets ?? [];

            return (
              <ProgramModuleCard
                key={mod.id}
                orderIndex={idx + 1}
                title={mod.title}
                description={description}
                outcome={copy?.outcome}
                bullets={bullets}
                mistakes={copy?.mistakes}
                promoVideoId={null}
                posterUrl={null}
                durationLabel={copy?.duration ?? lesson?.duration}
              />
            );
          })}
    </div>
  );
}
