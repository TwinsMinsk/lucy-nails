"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import useEmblaCarousel from "embla-carousel-react";
import AutoScroll from "embla-carousel-auto-scroll";
import { ChevronLeft, ChevronRight } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { WorkPhoto } from "@/lib/landing/works-photos";

// If a module has few photos, repeat them so the loop always fills the viewport
const MIN_TILES = 6;

export interface WorksMarqueeProps {
  photos: WorkPhoto[];
  title: string;
  reverse?: boolean;
}

export function WorksMarquee({ photos, title, reverse = false }: WorksMarqueeProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  // Native lazy loading never fires for tiles moved by the carousel transform,
  // so load the whole strip once the marquee itself approaches the viewport.
  const [inView, setInView] = useState(false);

  const [emblaRef, emblaApi] = useEmblaCarousel(
    { loop: true, align: "start", skipSnaps: true },
    [
      AutoScroll({
        speed: 0.6,
        direction: reverse ? "backward" : "forward",
        stopOnInteraction: false,
        stopOnMouseEnter: true,
        startDelay: 1200,
        rootNode: (root) => root.parentElement,
      }),
    ]
  );

  const handleArrow = useCallback(
    (dir: 1 | -1) => {
      if (!emblaApi) return;
      if (dir > 0) emblaApi.scrollNext();
      else emblaApi.scrollPrev();
      emblaApi.plugins()?.autoScroll?.reset();
    },
    [emblaApi]
  );

  useEffect(() => {
    const el = wrapperRef.current;
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

  return (
    <>
      <div ref={wrapperRef} className="relative">
        <div
          ref={emblaRef}
          className="works-marquee-mask h-64 w-full overflow-hidden rounded-2xl [content-visibility:auto] md:h-72"
        >
          <div className="flex">
            {seq.map((photo, i) => (
              <div key={`${photo.thumb}-${i}`} className="min-w-0 flex-[0_0_auto] pl-2">
                <button
                  type="button"
                  onClick={() => setActiveIndex(i % photos.length)}
                  className="relative size-64 shrink-0 overflow-hidden rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37] md:size-72"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- pre-sized static WebP thumb, no transform needed */}
                  <img
                    src={photo.thumb}
                    alt={`${title} — пример работы ${(i % photos.length) + 1}`}
                    width={640}
                    height={640}
                    loading={inView ? "eager" : "lazy"}
                    decoding="async"
                    draggable={false}
                    className="size-full select-none object-cover"
                  />
                </button>
              </div>
            ))}
          </div>
        </div>
        <button
          type="button"
          aria-label="Предыдущие работы"
          onClick={() => handleArrow(-1)}
          className="absolute left-2 top-1/2 z-10 flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-text-primary shadow-lg transition hover:scale-110 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37]"
        >
          <ChevronLeft className="size-5" />
        </button>
        <button
          type="button"
          aria-label="Следующие работы"
          onClick={() => handleArrow(1)}
          className="absolute right-2 top-1/2 z-10 flex size-9 -translate-y-1/2 items-center justify-center rounded-full bg-white/85 text-text-primary shadow-lg transition hover:scale-110 hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF37]"
        >
          <ChevronRight className="size-5" />
        </button>
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
