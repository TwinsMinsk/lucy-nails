"use client";

import { useEffect, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { WorkPhoto } from "@/lib/landing/works-photos";
import { ChevronLeft, ChevronRight } from "lucide-react";

const SECONDS_PER_PHOTO = 4.5;
// If a module has few photos, repeat them so one strip copy always fills the viewport
const MIN_TILES = 6;

export interface WorksMarqueeProps {
  photos: WorkPhoto[];
  title: string;
  reverse?: boolean;
}

export function WorksMarquee({ photos, title, reverse = false }: WorksMarqueeProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const viewportRef = useRef<HTMLDivElement>(null);
  // Native lazy loading never fires for tiles moved by the CSS transform animation,
  // so load the whole strip once the marquee itself approaches the viewport.
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: "300px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Preload lightbox neighbours so arrow navigation feels instant
  useEffect(() => {
    if (activeIndex === null || photos.length < 2) return;
    [1, -1].forEach((dir) => {
      const img = new Image();
      img.src = photos[(activeIndex + dir + photos.length) % photos.length].full;
    });
  }, [activeIndex, photos]);

  const active = activeIndex !== null ? photos[activeIndex] : null;

  const show = (dir: 1 | -1) =>
    setActiveIndex((prev) =>
      prev === null ? null : (prev + dir + photos.length) % photos.length
    );

  const seq =
    photos.length >= MIN_TILES
      ? photos
      : Array.from({ length: Math.ceil(MIN_TILES / photos.length) }, () => photos).flat();

  const strip = (hidden: boolean) => (
    <div className="flex shrink-0 gap-2 pr-2" aria-hidden={hidden || undefined}>
      {seq.map((photo, i) => (
        <button
          key={`${photo.thumb}-${i}`}
          type="button"
          tabIndex={hidden ? -1 : 0}
          onClick={() => setActiveIndex(i % photos.length)}
          className="relative size-36 shrink-0 overflow-hidden rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37] md:size-40"
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- pre-sized static WebP thumb, no transform needed */}
          <img
            src={photo.thumb}
            alt={hidden ? "" : `${title} — пример работы ${i + 1}`}
            width={320}
            height={320}
            loading={inView ? "eager" : "lazy"}
            decoding="async"
            draggable={false}
            className="size-full select-none object-cover"
          />
        </button>
      ))}
    </div>
  );

  return (
    <>
      <div
        ref={viewportRef}
        className="works-marquee-mask h-36 w-full overflow-hidden rounded-2xl [content-visibility:auto] md:h-40"
      >
        <div
          className="flex w-max animate-[works-marquee_var(--works-duration)_linear_infinite] hover:paused focus-within:paused motion-reduce:paused"
          style={
            {
              "--works-duration": `${seq.length * SECONDS_PER_PHOTO}s`,
              animationDirection: reverse ? "reverse" : undefined,
            } as React.CSSProperties
          }
        >
          {strip(false)}
          {strip(true)}
        </div>
      </div>
      <Dialog
        open={activeIndex !== null}
        onOpenChange={(open) => { if (!open) setActiveIndex(null); }}
      >
        <DialogContent
          aria-describedby={undefined}
          className="max-w-none border-none bg-transparent p-0 text-white shadow-none sm:max-w-none"
          style={{ width: "min(92vw, 80svh, 40rem)" }}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight") { e.preventDefault(); show(1); }
            if (e.key === "ArrowLeft") { e.preventDefault(); show(-1); }
          }}
        >
          <DialogHeader className="sr-only">
            <DialogTitle>{title} — пример работы</DialogTitle>
          </DialogHeader>
          {active !== null && activeIndex !== null ? (
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element -- exact-size static WebP for the lightbox */}
              <img
                key={activeIndex}
                src={active.full}
                alt={`${title} — пример работы ${activeIndex + 1}`}
                width={1024}
                height={1024}
                className="aspect-square w-full rounded-3xl object-cover shadow-2xl animate-in fade-in duration-200"
              />
              {photos.length > 1 ? (
                <>
                  <button
                    type="button"
                    aria-label="Предыдущее фото"
                    onClick={() => show(-1)}
                    className="absolute left-3 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-text-primary shadow-lg transition hover:scale-110 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37] md:size-11"
                  >
                    <ChevronLeft className="size-6" />
                  </button>
                  <button
                    type="button"
                    aria-label="Следующее фото"
                    onClick={() => show(1)}
                    className="absolute right-3 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-text-primary shadow-lg transition hover:scale-110 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37] md:size-11"
                  >
                    <ChevronRight className="size-6" />
                  </button>
                  <span className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-3 py-1 text-xs font-medium text-white">
                    {activeIndex + 1} / {photos.length}
                  </span>
                </>
              ) : null}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
