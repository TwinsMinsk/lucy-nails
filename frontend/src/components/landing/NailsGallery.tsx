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
    /**
     * "carousel": every work has its own scroll position, the selected one is emphasised.
     * "strip": Embla could not loop, merged positions or everything fits; all works are shown equally.
     */
    mode: "carousel" | "strip";
    /** Selected scroll position; in carousel mode it is also the work index. */
    selected: number;
    positions: number;
}

function readCarouselState(api: EmblaCarouselType): CarouselState {
    const positions = api.scrollSnapList().length;
    return {
        mode: positions === api.slideNodes().length ? "carousel" : "strip",
        selected: api.selectedScrollSnap(),
        positions,
    };
}

export function NailsGallery({ items }: NailsGalleryProps) {
    const [emblaRef, emblaApi] = useEmblaCarousel({
        loop: true,
        align: "center",
        skipSnaps: false,
    });

    const [carousel, setCarousel] = useState<CarouselState>({
        mode: "carousel",
        selected: 0,
        positions: items.length,
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
        emblaApi.on("select", sync).on("reInit", sync).on("resize", sync);
        return () => {
            emblaApi.off("select", sync).off("reInit", sync).off("resize", sync);
        };
    }, [emblaApi, sync]);

    const { mode, selected, positions } = carousel;
    const isCarousel = mode === "carousel";
    const showNavigation = positions > 1;
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
                            const isActive = isCarousel && selected === index;
                            // In carousel mode only the selected work is shown in full, so cut-off neighbour
                            // text never competes with it; in strip mode every work is.
                            const isShown = !isCarousel || isActive;
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
                                                scale: !isCarousel ? 1 : isActive ? 1.1 : 0.85,
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
                                        {/* Never wider than its slide; the text wraps in full, and flex-1 makes every
                                            caption area as tall as the longest one in the row */}
                                        <motion.figcaption
                                            initial={false}
                                            animate={{ opacity: isShown ? 1 : 0 }}
                                            transition={transition}
                                            className="mt-4 flex flex-1 flex-col items-center gap-1.5 px-1 text-center"
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
                       (slide width minus pl-1, times 4/3). In carousel mode the active photo grows upward from its
                       bottom edge by 10%, so -5% moves the arrows to its visual centre */
                    <div className="pointer-events-none absolute inset-x-0 top-[10vw] sm:top-16 z-20">
                        <div className="relative pt-[calc((70%_-_4px)*4/3)] sm:pt-[calc((50%_-_4px)*4/3)] md:pt-[calc((40%_-_4px)*4/3)] lg:pt-[calc((33.333%_-_4px)*4/3)]">
                            <div className={`absolute inset-0 flex items-center justify-between gap-4 ${isCarousel ? "-translate-y-[5%]" : ""}`}>
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

            {/* Dots / Indicators: one per work in carousel mode, one per scroll position in strip mode */}
            {/* 24px tall hit area around a 10px dot (WCAG 2.5.8) */}
            {showNavigation && (
                <div className="flex justify-center gap-1 mt-6">
                    {Array.from({ length: positions }, (_, index) => (
                        <button
                            key={index}
                            type="button"
                            onClick={() => emblaApi?.scrollTo(index)}
                            className="group/dot flex h-6 items-center px-1"
                            aria-label={`${isCarousel ? "Работа" : "Страница"} ${index + 1} из ${positions}`}
                            aria-current={selected === index ? "true" : undefined}
                        >
                            <span
                                className={`block h-2.5 rounded-full transition-all duration-300 ${selected === index
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
