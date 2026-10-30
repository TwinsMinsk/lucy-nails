import { ProgramModuleCard } from "@/components/landing/ProgramModuleCard";
import { ProgramModulesExpander } from "@/components/landing/ProgramModulesExpander";
import type { ModuleResponse } from "@/lib/api";
import {
  programModules as staticProgramModules,
  type ProgramModuleContent,
} from "@/lib/landing/course-content";
import { worksPhotos } from "@/lib/landing/works-photos";

// Kept in this server module: a constant imported from a "use client" file
// arrives here as a client reference, not as a number.
const VISIBLE_ON_MOBILE = 3;

export interface ProgramSectionProps {
  /** Lesson-level overrides (description/duration) coming from /api/courses/:id/modules */
  apiModules: ModuleResponse[] | null;
  /** Pre-merged copy for each module (DB landing-fields applied on top of static fallback) */
  modules?: ProgramModuleContent[];
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return "";
  const m = Math.round(seconds / 60);
  if (m <= 0) return "~1 мин";
  return `${m} мин`;
}

export function ProgramSection({ apiModules, modules }: ProgramSectionProps) {
  const programModules = modules ?? staticProgramModules;
  const apiByTitle = new Map((apiModules ?? []).map((m) => [m.title, m] as const));

  return (
    <ProgramModulesExpander total={programModules.length} visibleOnMobile={VISIBLE_ON_MOBILE}>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
        {programModules.map((copy, idx) => {
          const apiMod = apiByTitle.get(copy.title);
          const apiLesson = apiMod?.lessons?.[0];

          const description =
            copy.description ||
            apiLesson?.promo_description?.trim() ||
            apiMod?.description ||
            "";
          const bullets =
            copy.bullets?.length
              ? copy.bullets
              : apiLesson?.promo_bullets?.length
                ? apiLesson.promo_bullets
                : copy.bullets;
          const durationLabel =
            copy.duration ||
            (apiLesson?.duration_seconds ? formatDuration(apiLesson.duration_seconds) : "");

          return (
            <ProgramModuleCard
              key={apiMod?.id || copy.slug}
              orderIndex={idx + 1}
              title={copy.title}
              description={description}
              outcome={copy.outcome}
              bullets={bullets}
              mistakes={copy.mistakes}
              photos={worksPhotos[copy.slug] ?? []}
              reverseMarquee={idx % 2 === 1}
              durationLabel={durationLabel}
              className={idx >= VISIBLE_ON_MOBILE ? "max-md:group-data-[collapsed=true]/program:hidden" : undefined}
            />
          );
        })}
      </div>
    </ProgramModulesExpander>
  );
}
