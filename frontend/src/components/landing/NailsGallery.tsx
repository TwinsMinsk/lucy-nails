"use client";

import React, { useCallback, useEffect, useState } from "react";
import useEmblaCarousel from "embla-carousel-react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NailsGalleryProps {
    images: string[];
}

export function NailsGallery({ images }: NailsGalleryProps) {
    const [emblaRef, emblaApi] = useEmblaCarousel({
        loop: true,
        align: "center",
        skipSnaps: false,
    });

    const [selectedIndex, setSelectedIndex] = useState(0);

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
                    {images.map((src, index) => {
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
                                    transition={{
                                        type: "spring",
                                        stiffness: 300,
                                        damping: 30,
                                    }}
                                    className="relative aspect-[3/4] rounded-3xl overflow-hidden shadow-2xl bg-[#EBC8C8]"
                                >
                                    <img
                                        src={src}
                                        alt={`Nail work ${index + 1}`}
                                        className="w-full h-full object-cover select-none"
                                    />
                                    {/* Subtle overlay for inactive ones */}
                                    {!isActive && (
                                        <div className="absolute inset-0 bg-black/5 backdrop-blur-[1px]" />
                                    )}
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
                    className="pointer-events-auto rounded-full w-14 h-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -ml-4 md:-ml-7 transition-all hover:scale-110 active:scale-90"
                >
                    <ChevronLeft className="w-8 h-8" />
                </Button>
                <Button
                    onClick={scrollNext}
                    variant="outline"
                    size="icon"
                    className="pointer-events-auto rounded-full w-14 h-14 bg-white/95 backdrop-blur-sm border border-black/5 shadow-2xl hover:bg-white text-text-primary -mr-4 md:-mr-7 transition-all hover:scale-110 active:scale-90"
                >
                    <ChevronRight className="w-8 h-8" />
                </Button>
            </div>

            {/* Dots / Indicators */}
            <div className="flex justify-center gap-3 mt-12">
                {images.map((_, index) => (
                    <button
                        key={index}
                        onClick={() => emblaApi?.scrollTo(index)}
                        className={`h-2.5 transition-all duration-300 rounded-full shadow-sm ${selectedIndex === index
                            ? "w-12 bg-primary"
                            : "w-2.5 bg-primary/30 hover:bg-primary/50"
                            }`}
                        aria-label={`Go to slide ${index + 1}`}
                    />
                ))}
            </div>
        </div>
    );
}
