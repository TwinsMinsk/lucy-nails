"use client";

import { useEffect, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { WorkPhoto } from "@/lib/landing/works-photos";

const SECONDS_PER_PHOTO = 4.5;
// If a module has few photos, repeat them so one strip copy always fills the viewport
const MIN_TILES = 6;

export interface WorksMarqueeProps {
  photos: WorkPhoto[];
  title: string;
  reverse?: boolean;
}

export function WorksMarquee({ photos, title, reverse = false }: WorksMarqueeProps) {
  const [active, setActive] = useState<WorkPhoto | null>(null);
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
          onClick={() => setActive(photo)}
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
      <Dialog open={active !== null} onOpenChange={(open) => { if (!open) setActive(null); }}>
        <DialogContent
          aria-describedby={undefined}
          className="max-w-none border-none bg-transparent p-0 text-white shadow-none sm:max-w-none"
          style={{ width: "min(92vw, 80svh, 40rem)" }}
        >
          <DialogHeader className="sr-only">
            <DialogTitle>{title} — пример работы</DialogTitle>
          </DialogHeader>
          {active ? (
            /* eslint-disable-next-line @next/next/no-img-element -- exact-size static WebP for the lightbox */
            <img
              src={active.full}
              alt={`${title} — пример работы`}
              width={1024}
              height={1024}
              className="aspect-square w-full rounded-3xl object-cover shadow-2xl"
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
