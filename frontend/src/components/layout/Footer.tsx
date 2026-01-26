"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Footer() {
    const pathname = usePathname();
    const isLessonPage = pathname.includes("/lessons/");

    if (isLessonPage) return null;

    return (
        <footer className="w-full border-t bg-background py-6 md:py-0">
            <div className="container flex flex-col items-center justify-between gap-4 md:h-16 md:flex-row px-4 md:px-6">
                <div className="flex flex-col items-center gap-4 md:flex-row md:gap-2 md:px-0">
                    <p className="text-center text-sm leading-loose text-text-secondary md:text-left">
                        © {new Date().getFullYear()} Nails Course. Все права защищены.
                    </p>
                </div>
                <div className="flex gap-4">
                    {/* Placeholder for future footer links like Privacy Policy */}
                    <Link href="/privacy" className="text-xs text-text-secondary hover:text-primary transition-colors">
                        Политика конфиденциальности
                    </Link>
                    <Link href="/terms" className="text-xs text-text-secondary hover:text-primary transition-colors">
                        Публичная оферта
                    </Link>
                </div>
            </div>
        </footer>
    );
}
