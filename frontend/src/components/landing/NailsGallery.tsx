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
        <div className="relative w-full max-w-6xl mx-auto px-4 py-8 group">
            {/* Container for Embla */}
            <div className="overflow-hidden" ref={emblaRef}>
                <div className="flex">
                    {items.map((item, index) => {
                        const isActive = selectedIndex === index;

                        return (
                            <div
                                key={index}
                                className="flex-[0_0_70%] sm:flex-[0_0_50%] md:flex-[0_0_40%] lg:flex-[0_0_33.333%] min-w-0 pl-1 py-10"
                            >
                                <motion.div
                                    initial={false}
                                    animate={{
                                        scale: isActive ? 1.1 : 0.85,
                                        opacity: isActive ? 1 : 0.6,
                                        zIndex: isActive ? 10 : 0,
                                    }}
                                    transition={reduceMotion ? { duration: 0 } : {
                                        type: "spring",
                                        stiffness: 300,
                                        damping: 30,
                                    }}
                                    className="relative aspect-[3/4] rounded-3xl overflow-hidden shadow-2xl bg-[#EBC8C8]"
                                >
                                    <Image
                                        src={item.src}
                                        alt={item.alt}
                                        fill
                                        sizes="(max-width: 640px) 70vw, (max-width: 1024px) 40vw, 33vw"
                                        className="object-cover select-none"
                                    />
                                    {/* Compact caption: the work itself is the point of the slide */}
                                    <div className="absolute inset-x-3 bottom-3 rounded-2xl bg-white/90 px-3 py-2.5 border border-white/70">
                                        <Badge variant="secondary" className="mb-1 bg-[#fff1f4] text-text-primary border border-primary/20">
                                            {item.technique}
                                        </Badge>
                                        <p className="text-sm leading-snug text-text-secondary">
                                            {item.caption}
                                        </p>
                                    </div>
                                </motion.div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Navigation Arrows */}
            <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 gap-4 flex justify-between items-center px-4 md:px-0 pointer-events-none z-20">
                <Button
                    onClick={scrollPrev}
                    variant="outline"
                    size="icon"
                    aria-label="Предыдущая работа"
                    className="pointer-events-auto rounded-full w-14 h-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -ml-4 md:-ml-7 transition-all hover:scale-110 active:scale-90"
                >
                    <ChevronLeft className="w-8 h-8" />
                </Button>
                <Button
                    onClick={scrollNext}
                    variant="outline"
                    size="icon"
                    aria-label="Следующая работа"
                    className="pointer-events-auto rounded-full w-14 h-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -mr-4 md:-mr-7 transition-all hover:scale-110 active:scale-90"
                >
                    <ChevronRight className="w-8 h-8" />
                </Button>
            </div>

            {/* Dots / Indicators */}
            {/* 24px tall hit area around a 10px dot (WCAG 2.5.8) */}
            <div className="flex justify-center gap-1 mt-12">
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
