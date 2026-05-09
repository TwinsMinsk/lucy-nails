"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { CheckCircle, Play } from "lucide-react";
import Image from "next/image";

export interface ProgramModuleCardProps {
  orderIndex: number;
  title: string;
  description: string;
  outcome?: string;
  bullets: string[];
  mistakes?: string[];
  promoVideoId: string | null;
  posterUrl: string | null;
  durationLabel?: string;
}

export function ProgramModuleCard({
  orderIndex,
  title,
  description,
  outcome,
  bullets,
  mistakes = [],
  promoVideoId,
  posterUrl,
  durationLabel,
}: ProgramModuleCardProps) {
  const hasVideo = Boolean(promoVideoId);
  const embedSrc = promoVideoId
    ? `https://kinescope.io/embed/${promoVideoId}?preload=false&autopause=1&muted=0`
    : null;

  const posterArea = hasVideo && embedSrc ? (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          className="group relative w-full aspect-video rounded-2xl overflow-hidden border-2 border-primary/20 shadow-lg text-left focus:outline-none focus:ring-2 focus:ring-[#D4AF37] focus:ring-offset-2"
        >
          {posterUrl ? (
            <Image
              src={posterUrl}
              alt={title}
              fill
              className="object-cover transition duration-500 group-hover:scale-105"
              sizes="(max-width: 768px) 100vw, 33vw"
            />
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-[#fff1f4] to-[#e8c4c4]" />
          )}
          <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/35 transition">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/90 text-primary shadow-xl group-hover:scale-110 transition">
              <Play className="h-8 w-8 fill-current" />
            </div>
          </div>
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-4xl w-[95vw] p-0 overflow-hidden bg-black border-primary/20">
        <DialogHeader className="sr-only">
          <DialogTitle>Превью: {title}</DialogTitle>
        </DialogHeader>
        <div className="relative aspect-video w-full bg-black">
          <iframe
            src={embedSrc}
            title={title}
            className="absolute inset-0 h-full w-full"
            allow="autoplay; fullscreen; picture-in-picture; encrypted-media"
            allowFullScreen
            loading="lazy"
          />
        </div>
      </DialogContent>
    </Dialog>
  ) : (
    <div className="relative w-full aspect-video rounded-2xl overflow-hidden border-2 border-dashed border-primary/25 bg-gradient-to-br from-[#fff1f4] to-[#f5e6e9] flex items-center justify-center">
      <p className="text-sm text-text-secondary/80 text-center px-4">
        Промо-ролик появится после загрузки в Kinescope
      </p>
    </div>
  );

  return (
    <article className="flex flex-col bg-[#FFF1F4] rounded-[2rem] border border-primary/20 border-b-[6px] border-b-primary/15 shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 overflow-hidden">
      <div className="p-5 pb-4">{posterArea}</div>
      <div className="px-6 pb-6 flex flex-col flex-1 gap-3">
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
