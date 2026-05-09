import { ProgramModuleCard } from "@/components/landing/ProgramModuleCard";
import type { Module } from "@/components/course/ModuleList";
import type { ModuleResponse } from "@/lib/api";
import { programModules } from "@/lib/landing/course-content";

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

export function ProgramSection({ apiModules }: ProgramSectionProps) {
  const apiByTitle = new Map((apiModules ?? []).map((m) => [m.title, m] as const));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
      {programModules.map((copy, idx) => {
        const apiMod = apiByTitle.get(copy.title);
        const apiLesson = apiMod?.lessons?.[0];

        const promoId = apiLesson?.promo_kinescope_video_id || copy.promoVideoId || null;
        const poster = apiLesson?.promo_poster_url || copy.promoPosterUrl || null;
        const description =
          apiLesson?.promo_description?.trim() ||
          copy.description ||
          apiMod?.description ||
          "";
        const bullets =
          apiLesson?.promo_bullets?.length ? apiLesson.promo_bullets : copy.bullets;
        const durationLabel = apiLesson?.duration_seconds
          ? formatDuration(apiLesson.duration_seconds)
          : copy.duration;

        return (
          <ProgramModuleCard
            key={apiMod?.id || copy.slug}
            orderIndex={idx + 1}
            title={copy.title}
            description={description}
            outcome={copy.outcome}
            bullets={bullets}
            mistakes={copy.mistakes}
            promoVideoId={promoId}
            posterUrl={poster}
            durationLabel={durationLabel}
          />
        );
      })}
    </div>
  );
}
