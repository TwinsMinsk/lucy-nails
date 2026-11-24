"use client";

import React, { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import useEmblaCarousel from "embla-carousel-react";
import type { EmblaCarouselType } from "embla-carousel";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { GalleryItem } from "@/lib/landing/course-content";

interface NailsGalleryProps {
    items: GalleryItem[];
}

interface CarouselState {
    /** Slide shown as the current work (scaled up, caption visible). */
    activeSlide: number;
    /** Slides fully inside the viewport. */
    inView: number[];
    /** Every slide is fully in view: nothing to scroll, all works are shown equally. */
    fits: boolean;
    /** Scroll snap that brings each slide into place (a snap is not a slide index). */
    snapOfSlide: number[];
}

function readCarouselState(api: EmblaCarouselType): CarouselState {
    const slideCount = api.slideNodes().length;
    // Snap index -> slide indexes. When Embla cannot loop it merges the edge snaps (trimSnaps),
    // so one snap may hold several slides.
    const registry = api.internalEngine().slideRegistry;
    const snap = api.selectedScrollSnap();
    const group = registry[snap] ?? [snap];
    // In a merged start group the slide nearest the centre is the last one; in the end group, the first.
    let activeSlide = group[0];
    if (registry.length > 1 && snap === 0) activeSlide = group[group.length - 1];
    const inView = api.slidesInView();
    const snapOfSlide = Array.from({ length: slideCount }, (_, slide) =>
        Math.max(0, registry.findIndex((slides) => slides.includes(slide))),
    );
    return { activeSlide, inView, fits: slideCount > 0 && inView.length === slideCount, snapOfSlide };
}

export function NailsGallery({ items }: NailsGalleryProps) {
    const [emblaRef, emblaApi] = useEmblaCarousel({
        loop: true,
        align: "center",
        skipSnaps: false,
        // A slide counts as in view only when it is (almost) entirely visible, not when it peeks in.
        inViewThreshold: 0.99,
    });

    const [carousel, setCarousel] = useState<CarouselState>({
        activeSlide: 0,
        inView: [],
        fits: false,
        snapOfSlide: items.map((_, index) => index),
    });
    const reduceMotion = useReducedMotion();

    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);

    const sync = useCallback(() => {
        if (!emblaApi) return;
        setCarousel(readCarouselState(emblaApi));
    }, [emblaApi]);

    useEffect(() => {
        if (!emblaApi) return;
        sync();
        emblaApi.on("select", sync).on("reInit", sync).on("slidesInView", sync);
        return () => {
            emblaApi.off("select", sync).off("reInit", sync).off("slidesInView", sync);
        };
    }, [emblaApi, sync]);

    const { activeSlide, inView, fits, snapOfSlide } = carousel;
    const showNavigation = !fits && items.length > 1;
    const transition = reduceMotion ? { duration: 0 } : {
        type: "spring" as const,
        stiffness: 300,
        damping: 30,
    };

    return (
        <div className="relative w-full max-w-6xl mx-auto px-4 pb-8 group">
            {/* Slides plus arrows; the dots sit below and outside this box */}
            <div className="relative">
                {/* Container for Embla. Slides stretch to the tallest one, so the row keeps its height while sliding */}
                <div className="overflow-hidden" ref={emblaRef}>
                    <div className="flex">
                        {items.map((item, index) => {
                            const isActive = !fits && activeSlide === index;
                            const isShown = fits || isActive;
                            // When every work fits, each visible slide shows its caption; otherwise only the current one,
                            // so cut-off neighbour text never competes with it.
                            const captionVisible = fits ? inView.includes(index) : isActive;
                            const caption = item.caption.trim();

                            return (
                                <div
                                    key={index}
                                    className="flex flex-[0_0_70%] flex-col sm:flex-[0_0_50%] md:flex-[0_0_40%] lg:flex-[0_0_33.333%] min-w-0 pl-1 pt-[10vw] sm:pt-16 pb-2"
                                >
                                    {/* Inactive slides fade; only the photo scales, the text never does */}
                                    <motion.figure
                                        initial={false}
                                        animate={{ opacity: isShown ? 1 : 0.6 }}
                                        transition={transition}
                                        className="m-0 flex flex-1 flex-col"
                                    >
                                        {/* Scales from its bottom edge, so it grows into the top padding (10vw on phones,
                                            4rem from sm: each covers 10% of the widest photo at that breakpoint) and never reaches the caption below */}
                                        <motion.div
                                            initial={false}
                                            animate={{
                                                scale: fits ? 1 : isActive ? 1.1 : 0.85,
                                                zIndex: isActive ? 10 : 0,
                                            }}
                                            transition={transition}
                                            style={{ transformOrigin: "50% 100%" }}
                                            className="relative aspect-[3/4] rounded-3xl overflow-hidden shadow-2xl bg-[#EBC8C8]"
                                        >
                                            <Image
                                                src={item.src}
                                                alt={item.alt}
                                                fill
                                                sizes="(max-width: 639px) 78vw, (max-width: 767px) 55vw, (max-width: 1023px) 44vw, 420px"
                                                className="object-cover select-none"
                                            />
                                        </motion.div>
                                        {/* As wide as the scaled active photo (-mx-[5%]); the text wraps in full, and flex-1
                                            makes every caption area as tall as the longest one in the row */}
                                        <motion.figcaption
                                            initial={false}
                                            animate={{ opacity: captionVisible ? 1 : 0 }}
                                            transition={transition}
                                            className="-mx-[5%] mt-4 flex flex-1 flex-col items-center gap-1.5 px-1 text-center"
                                        >
                                            {item.technique && (
                                                <Badge variant="secondary" className="block max-w-full whitespace-normal break-words bg-[#fff1f4] text-text-primary border border-primary/20">
                                                    {item.technique}
                                                </Badge>
                                            )}
                                            {caption && (
                                                <p className="w-full break-words text-sm leading-5 text-text-secondary">
                                                    {caption}
                                                </p>
                                            )}
                                        </motion.figcaption>
                                    </motion.figure>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {showNavigation && (
                    /* Navigation Arrows, positioned against the photo box rather than the caption: the wrapper starts
                       at the slide's top padding and its padding-top (a % of the gallery width) equals the photo height
                       (slide width minus pl-1, times 4/3). The active photo grows upward from its bottom edge by 10%,
                       so -5% moves the arrows to its visual centre */
                    <div className="pointer-events-none absolute inset-x-0 top-[10vw] sm:top-16 z-20">
                        <div className="relative pt-[calc((70%_-_4px)*4/3)] sm:pt-[calc((50%_-_4px)*4/3)] md:pt-[calc((40%_-_4px)*4/3)] lg:pt-[calc((33.333%_-_4px)*4/3)]">
                            <div className="absolute inset-0 -translate-y-[5%] flex items-center justify-between gap-4">
                                <Button
                                    onClick={scrollPrev}
                                    variant="outline"
                                    size="icon"
                                    aria-label="Предыдущая работа"
                                    className="pointer-events-auto rounded-full size-11 md:size-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -ml-4 md:-ml-11 transition-all hover:scale-110 active:scale-90"
                                >
                                    <ChevronLeft className="size-6 md:size-8" />
                                </Button>
                                <Button
                                    onClick={scrollNext}
                                    variant="outline"
                                    size="icon"
                                    aria-label="Следующая работа"
                                    className="pointer-events-auto rounded-full size-11 md:size-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -mr-4 md:-mr-11 transition-all hover:scale-110 active:scale-90"
                                >
                                    <ChevronRight className="size-6 md:size-8" />
                                </Button>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Dots / Indicators */}
            {/* 24px tall hit area around a 10px dot (WCAG 2.5.8) */}
            {showNavigation && (
                <div className="flex justify-center gap-1 mt-6">
                    {items.map((_, index) => (
                        <button
                            key={index}
                            type="button"
                            onClick={() => emblaApi?.scrollTo(snapOfSlide[index] ?? index)}
                            className="group/dot flex h-6 items-center px-1"
                            aria-label={`Работа ${index + 1} из ${items.length}`}
                            aria-current={activeSlide === index ? "true" : undefined}
                        >
                            <span
                                className={`block h-2.5 rounded-full transition-all duration-300 ${activeSlide === index
                                    ? "w-12 bg-primary"
                                    : "w-2.5 bg-primary/30 group-hover/dot:bg-primary/50"
                                    }`}
                            />
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
