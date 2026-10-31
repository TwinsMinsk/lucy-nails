"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";


export function Footer() {
    const pathname = usePathname();
    const isLessonPage = pathname.includes("/lessons/");

    if (isLessonPage) return null;

    return (
        <footer className="w-full border-t bg-background py-6">
            <div className="container flex flex-col gap-6 px-4 md:px-6">
                <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
                    <div className="flex flex-col items-center gap-4 md:flex-row md:gap-2 md:px-0">
                        <p className="text-center text-sm leading-loose text-text-secondary md:text-left">
                            © {new Date().getFullYear()} Lucy Smirnova Nails. Все права защищены.
                        </p>
                    </div>
                    <div className="flex flex-wrap justify-center gap-x-4">
                        <Link href="/privacy" className="py-2 text-sm text-text-secondary hover:text-foreground hover:underline underline-offset-4 transition-colors">
                            Политика конфиденциальности
                        </Link>
                        <Link href="/terms" className="py-2 text-sm text-text-secondary hover:text-foreground hover:underline underline-offset-4 transition-colors">
                            Публичная оферта
                        </Link>
                    </div>
                </div>

                <div className="flex flex-col items-center md:items-start gap-1 text-xs text-text-secondary border-t pt-4">
                    <p>ИП Смирнова Людмила Анатольевна</p>
                    <div className="flex flex-wrap justify-center md:justify-start gap-x-4 gap-y-1">
                        <p>ИНН: 784217026925</p>
                        <p>ОГРНИП: 326784700145379</p>
                    </div>
                    <div className="flex flex-wrap justify-center md:justify-start gap-x-4 gap-y-1">
                        <p>Email: <a href="mailto:Luci4ek@gmail.com" className="hover:text-foreground hover:underline underline-offset-4">Luci4ek@gmail.com</a></p>
                        <p>Тел.: <a href="tel:+79312122091" className="whitespace-nowrap hover:text-foreground hover:underline underline-offset-4">+7 (931) 212-20-91</a></p>
                    </div>
                </div>
            </div>
        </footer>
    );
}
