"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import useEmblaCarousel from "embla-carousel-react";
import AutoScroll from "embla-carousel-auto-scroll";
import { useReducedMotion } from "framer-motion";
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
// Tiles loaded on each side of the visible ones, so the next tile is ready before
// the auto-scroll or an arrow brings it in (one tile passes in about seven seconds).
const PRELOAD_NEIGHBOURS = 2;
// Share of the strip that must be on screen before it auto-scrolls (about 13 px of a 256 px strip).
const PLAYBACK_VISIBLE_RATIO = 0.05;

export interface WorksMarqueeProps {
  photos: WorkPhoto[];
  title: string;
  reverse?: boolean;
}

export function WorksMarquee({ photos, title, reverse = false }: WorksMarqueeProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  // True while the strip is on screen or within 300 px of it: tiles load only then,
  // so strips further down the page cost no requests.
  const [nearViewport, setNearViewport] = useState(false);
  // True while some of the strip is actually on screen: it auto-scrolls only then.
  const [onScreen, setOnScreen] = useState(false);
  const onScreenRef = useRef(false);
  // Native lazy loading never fires for tiles moved by the carousel transform, so the tiles
  // in view and their neighbours are switched to eager loading as the carousel moves.
  const [loadedTiles, setLoadedTiles] = useState<ReadonlySet<number>>(() => new Set());
  // Endless auto-scroll is motion the visitor did not start: off when the OS asks for less motion.
  const reduceMotion = useReducedMotion();

  const [emblaRef, emblaApi] = useEmblaCarousel(
    { loop: true, align: "start", skipSnaps: true },
    reduceMotion
      ? []
      : [
          AutoScroll({
            speed: 0.6,
            direction: reverse ? "backward" : "forward",
            stopOnInteraction: false,
            stopOnMouseEnter: true,
            startDelay: 1200,
            // Started by the visibility observer below, not on mount.
            playOnInit: false,
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
    const preload = new IntersectionObserver(
      (entries) => {
        const entry = entries[entries.length - 1];
        if (entry) setNearViewport(entry.isIntersecting);
      },
      { rootMargin: "300px" }
    );
    // isIntersecting is also true for a strip that only touches the viewport edge with
    // zero visible area, so playback needs part of the strip to be actually visible.
    const playback = new IntersectionObserver(
      (entries) => {
        const entry = entries[entries.length - 1];
        if (entry) setOnScreen(entry.intersectionRatio >= PLAYBACK_VISIBLE_RATIO);
      },
      { threshold: PLAYBACK_VISIBLE_RATIO }
    );
    preload.observe(el);
    playback.observe(el);
    return () => {
      preload.disconnect();
      playback.disconnect();
    };
  }, []);

  // Auto-scroll only while the strip is on screen. Embla re-creates its plugins after
  // a resize, and playOnInit is off, so playback is restored on reInit as well.
  useEffect(() => {
    onScreenRef.current = onScreen;
    if (!emblaApi) return;
    const sync = () => {
      const autoScroll = emblaApi.plugins()?.autoScroll;
      if (!autoScroll) return;
      if (onScreenRef.current) autoScroll.play();
      else autoScroll.stop();
    };
    // The plugin also resumes by itself on mouseleave, focusout and after a drag settles.
    // Off screen that start is cancelled; the plugin marks itself playing only after
    // emitting the event, hence the microtask.
    const keepStillOffScreen = () => {
      if (!onScreenRef.current) queueMicrotask(() => emblaApi.plugins()?.autoScroll?.stop());
    };
    sync();
    emblaApi.on("reInit", sync).on("autoScroll:play", keepStillOffScreen);
    return () => {
      emblaApi.off("reInit", sync).off("autoScroll:play", keepStillOffScreen);
    };
  }, [emblaApi, onScreen]);

  // Load the tiles in view plus PRELOAD_NEIGHBOURS on each side (both directions: strips
  // scroll either way and the arrows go back too). Loaded tiles stay loaded.
  useEffect(() => {
    if (!emblaApi || !nearViewport) return;
    const markNearbyTiles = () => {
      const count = emblaApi.slideNodes().length;
      if (count === 0) return;
      const inView = emblaApi.slidesInView();
      const anchors = inView.length > 0 ? inView : [emblaApi.selectedScrollSnap()];
      setLoadedTiles((prev) => {
        let next: Set<number> | null = null;
        for (const index of anchors) {
          for (let offset = -PRELOAD_NEIGHBOURS; offset <= PRELOAD_NEIGHBOURS; offset++) {
            const tile = (((index + offset) % count) + count) % count;
            if (!prev.has(tile)) {
              next ??= new Set(prev);
              next.add(tile);
            }
          }
        }
        return next ?? prev;
      });
    };
    markNearbyTiles();
    emblaApi.on("slidesInView", markNearbyTiles).on("reInit", markNearbyTiles);
    return () => {
      emblaApi.off("slidesInView", markNearbyTiles).off("reInit", markNearbyTiles);
    };
  }, [emblaApi, nearViewport]);

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
                    loading={loadedTiles.has(i) ? "eager" : "lazy"}
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
