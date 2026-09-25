import { CheckCircle } from "lucide-react";

import { WorksMarquee } from "@/components/landing/WorksMarquee";
import type { WorkPhoto } from "@/lib/landing/works-photos";

export interface ProgramModuleCardProps {
  orderIndex: number;
  title: string;
  description: string;
  outcome?: string;
  bullets: string[];
  mistakes?: string[];
  photos: WorkPhoto[];
  reverseMarquee?: boolean;
  durationLabel?: string;
}

export function ProgramModuleCard({
  orderIndex,
  title,
  description,
  outcome,
  bullets,
  mistakes = [],
  photos,
  reverseMarquee = false,
  durationLabel,
}: ProgramModuleCardProps) {
  // Modules without photos render text only instead of a placeholder for buyers.
  const hasPhotos = photos.length > 0;

  return (
    <article className="flex flex-col bg-[#FFF1F4] rounded-[2rem] border border-primary/20 border-b-[6px] border-b-primary/15 shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 overflow-hidden">
      {hasPhotos ? (
        <div className="p-5 pb-4">
          <WorksMarquee photos={photos} title={title} reverse={reverseMarquee} />
        </div>
      ) : null}
      <div className={`px-6 pb-6 flex flex-col flex-1 gap-3${hasPhotos ? "" : " pt-6"}`}>
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-serif text-2xl text-text-primary leading-snug">
            Модуль {orderIndex}: {title}
          </h3>
          {durationLabel ? (
            <span className="shrink-0 text-xs font-medium text-text-secondary bg-white/80 px-3 py-1 rounded-full border border-gray-100">
              {durationLabel}
            </span>
          ) : null}
        </div>
        <p className="text-text-secondary leading-relaxed text-sm md:text-base">{description}</p>
        {outcome ? (
          <div className="rounded-2xl bg-white/70 border border-white px-4 py-3 text-sm text-text-primary">
            <span className="block text-[10px] uppercase tracking-[0.18em] text-text-secondary mb-1">
              Что заберёте в работу
            </span>
            {outcome}
          </div>
        ) : null}
        <ul className="space-y-2 mt-1">
          {bullets.map((b, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
              <CheckCircle className="h-4 w-4 text-[#D4AF37] shrink-0 mt-0.5 fill-[#D4AF37]/10" />
              <span>{b}</span>
            </li>
          ))}
        </ul>
        {mistakes.length > 0 ? (
          <div className="mt-auto rounded-2xl border border-primary/15 bg-white/45 px-4 py-3">
            <span className="block text-[10px] uppercase tracking-[0.18em] text-text-secondary mb-2">
              Разберём ошибки
            </span>
            <div className="flex flex-wrap gap-2">
              {mistakes.slice(0, 3).map((mistake) => (
                <span
                  key={mistake}
                  className="rounded-full bg-white/80 px-3 py-1 text-xs text-text-secondary border border-white"
                >
                  {mistake}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </article>
  );
}
