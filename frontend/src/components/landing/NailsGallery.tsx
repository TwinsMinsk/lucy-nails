"use client";

import React, { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import useEmblaCarousel from "embla-carousel-react";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { GalleryItem } from "@/lib/landing/course-content";

interface NailsGalleryProps {
    items: GalleryItem[];
}

export function NailsGallery({ items }: NailsGalleryProps) {
    const [emblaRef, emblaApi] = useEmblaCarousel({
        loop: true,
        align: "center",
        skipSnaps: false,
    });

    const [selectedIndex, setSelectedIndex] = useState(0);
    const reduceMotion = useReducedMotion();

    const scrollPrev = useCallback(() => emblaApi && emblaApi.scrollPrev(), [emblaApi]);
    const scrollNext = useCallback(() => emblaApi && emblaApi.scrollNext(), [emblaApi]);

    const onSelect = useCallback(() => {
        if (!emblaApi) return;
        setSelectedIndex(emblaApi.selectedScrollSnap());
    }, [emblaApi]);

    useEffect(() => {
        if (!emblaApi) return;
        onSelect();
        emblaApi.on("select", onSelect);
        emblaApi.on("reInit", onSelect);
    }, [emblaApi, onSelect]);

    return (
        <div className="relative w-full max-w-6xl mx-auto px-4 pb-8 group">
            {/* Slides plus arrows; the dots sit below and outside this box */}
            <div className="relative">
                {/* Container for Embla */}
                <div className="overflow-hidden" ref={emblaRef}>
                    <div className="flex">
                        {items.map((item, index) => {
                            const isActive = selectedIndex === index;
                            const caption = item.caption.trim();
                            const transition = reduceMotion ? { duration: 0 } : {
                                type: "spring" as const,
                                stiffness: 300,
                                damping: 30,
                            };

                            return (
                                <div
                                    key={index}
                                    className="flex-[0_0_70%] sm:flex-[0_0_50%] md:flex-[0_0_40%] lg:flex-[0_0_33.333%] min-w-0 pl-1 pt-[10vw] sm:pt-16 pb-2"
                                >
                                    {/* Inactive slides fade; only the photo scales, the text never does */}
                                    <motion.figure
                                        initial={false}
                                        animate={{ opacity: isActive ? 1 : 0.6 }}
                                        transition={transition}
                                        className="m-0"
                                    >
                                        {/* Scales from its bottom edge, so it grows into the top padding (10vw on phones,
                                            4rem from sm: each covers 10% of the widest photo at that breakpoint) and never reaches the caption below */}
                                        <motion.div
                                            initial={false}
                                            animate={{
                                                scale: isActive ? 1.1 : 0.85,
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
                                        {/* Fixed height (tag + three lines on phones, two from md) so captions never shift the layout.
                                            As wide as the scaled active photo (-mx-[5%]) to give the text room.
                                            Only the active caption is shown: cut-off neighbour text must not compete with it */}
                                        <motion.figcaption
                                            initial={false}
                                            animate={{ opacity: isActive ? 1 : 0 }}
                                            transition={transition}
                                            className="-mx-[5%] mt-4 flex h-[5.5rem] flex-col items-center gap-1.5 px-1 text-center md:h-[4.5rem]">
                                            {item.technique && (
                                                <Badge variant="secondary" className="block max-w-full truncate bg-[#fff1f4] text-text-primary border border-primary/20">
                                                    {item.technique}
                                                </Badge>
                                            )}
                                            {caption && (
                                                <p className="line-clamp-3 text-sm leading-5 text-text-secondary md:line-clamp-2">
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

                {/* Navigation Arrows: centred on the photo row (slide top padding to the caption block,
                    bottom = pb-2 + mt-4 + caption height: 7rem on phones, 6rem from md). The active photo grows upward from its bottom edge
                    by 10%, so -5% moves the arrows to its visual centre; -inset-x-4 keeps the old horizontal position */}
                <div className="absolute top-[10vw] sm:top-16 bottom-28 md:bottom-24 -left-4 -right-4 -translate-y-[5%] gap-4 flex justify-between items-center px-4 md:px-0 pointer-events-none z-20">
                    <Button
                        onClick={scrollPrev}
                        variant="outline"
                        size="icon"
                        aria-label="Предыдущая работа"
                        className="pointer-events-auto rounded-full size-11 md:size-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -ml-4 md:-ml-7 transition-all hover:scale-110 active:scale-90"
                    >
                        <ChevronLeft className="size-6 md:size-8" />
                    </Button>
                    <Button
                        onClick={scrollNext}
                        variant="outline"
                        size="icon"
                        aria-label="Следующая работа"
                        className="pointer-events-auto rounded-full size-11 md:size-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -mr-4 md:-mr-7 transition-all hover:scale-110 active:scale-90"
                    >
                        <ChevronRight className="size-6 md:size-8" />
                    </Button>
                </div>
            </div>

            {/* Dots / Indicators */}
            {/* 24px tall hit area around a 10px dot (WCAG 2.5.8) */}
            <div className="flex justify-center gap-1 mt-6">
                {items.map((_, index) => (
                    <button
                        key={index}
                        type="button"
                        onClick={() => emblaApi?.scrollTo(index)}
                        className="group/dot flex h-6 items-center px-1"
                        aria-label={`Работа ${index + 1} из ${items.length}`}
                        aria-current={selectedIndex === index ? "true" : undefined}
                    >
                        <span
                            className={`block h-2.5 rounded-full transition-all duration-300 ${selectedIndex === index
                                ? "w-12 bg-primary"
                                : "w-2.5 bg-primary/30 group-hover/dot:bg-primary/50"
                                }`}
                        />
                    </button>
                ))}
            </div>
        </div>
    );
}
