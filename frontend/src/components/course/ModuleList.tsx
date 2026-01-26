import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import { PlayCircle, Lock, Layers, Palette, Sparkles, GraduationCap, Gem, Feather, Brush, Zap } from "lucide-react";

export interface Lesson {
    id: string;
    title: string;
    duration?: string;
    isLocked?: boolean;
}

export interface Module {
    id: string;
    title: string;
    lessons: Lesson[];
}

interface ModuleListProps {
    modules: Module[];
}

// Helper to map module IDs to icons (optional, for visual flair)
const getModuleIcon = (id: string) => {
    const num = parseInt(id);
    if (isNaN(num)) return <Layers className="w-5 h-5 text-primary-dark" />;

    const icons = [
        <Layers key={1} className="w-5 h-5 text-primary-dark" />,       // 1. Basics
        <Palette key={2} className="w-5 h-5 text-primary-dark" />,      // 2. Pigments
        <Brush key={3} className="w-5 h-5 text-primary-dark" />,        // 3. Gradient
        <Feather key={4} className="w-5 h-5 text-primary-dark" />,      // 4. French
        <Sparkles key={5} className="w-5 h-5 text-primary-dark" />,     // 5. Textures
        <Gem key={6} className="w-5 h-5 text-primary-dark" />,          // 6. Aquarium
        <Zap key={7} className="w-5 h-5 text-primary-dark" />,          // 7. Bonus
        <GraduationCap key={8} className="w-5 h-5 text-primary-dark" />, // 8. Stamping
        <Layers key={9} className="w-5 h-5 text-primary-dark" />,       // 9. Sliders
        <Gem key={10} className="w-5 h-5 text-primary-dark" />,         // 10. 3D
    ];
    return icons[num - 1] || <Layers className="w-5 h-5 text-primary-dark" />;
};

export function ModuleList({ modules }: ModuleListProps) {
    return (
        <div className="w-full">
            <Accordion type="single" collapsible className="w-full space-y-4">
                {modules.map((module) => (
                    <AccordionItem
                        key={module.id}
                        value={module.id}
                        className="bg-[#FFF1F4] rounded-2xl border border-primary/20 border-b-[6px] border-b-primary/20 shadow-xl hover:shadow-2xl hover:-translate-y-1 hover:border-b-primary/30 transition-all duration-300 px-4 py-1 data-[state=open]:border-primary/40 data-[state=open]:border-b-primary/30"
                    >
                        <AccordionTrigger className="hover:no-underline py-5 group">
                            <div className="flex items-center gap-4 text-left w-full">
                                {/* Icon Box */}
                                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-white/80 shadow-inner shrink-0 group-hover:bg-primary/20 transition-colors">
                                    {getModuleIcon(module.id)}
                                </div>

                                <div className="flex flex-col gap-0.5">
                                    <span className="text-2xl font-serif font-medium text-text-primary group-hover:text-primary-dark transition-colors">
                                        Модуль {module.id}: {module.title}
                                    </span>
                                </div>
                            </div>
                        </AccordionTrigger>
                        <AccordionContent>
                            <div className="pb-4 pt-1 pl-[3.5rem] pr-2 space-y-2">
                                {module.lessons.map((lesson) => (
                                    <div
                                        key={lesson.id}
                                        className="flex items-center gap-3 p-3 rounded-xl bg-white/60 hover:bg-white/90 shadow-sm transition-all"
                                    >
                                        {lesson.isLocked ? (
                                            <Lock className="h-4 w-4 text-text-secondary/40 shrink-0" />
                                        ) : (
                                            <PlayCircle className="h-4 w-4 text-primary shrink-0" />
                                        )}
                                        <span className="text-base font-medium text-text-secondary">
                                            {lesson.title}
                                        </span>
                                        {lesson.duration && (
                                            <span className="ml-auto text-xs text-text-secondary/70 bg-white px-2 py-1 rounded-full border border-gray-100">
                                                {lesson.duration}
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </AccordionContent>
                    </AccordionItem>
                ))}
            </Accordion>
        </div>
    );
}
