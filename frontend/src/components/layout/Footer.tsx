"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";

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
                            © {new Date().getFullYear()} Nails Course. Все права защищены.
                        </p>
                    </div>
                    <div className="flex gap-4">
                        <Link href="/privacy" className="text-xs text-text-secondary hover:text-primary transition-colors">
                            Политика конфиденциальности
                        </Link>
                        <Dialog>
                            <DialogTrigger asChild>
                                <button className="text-xs text-text-secondary hover:text-primary transition-colors">
                                    Публичная оферта
                                </button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl h-[90vh] w-[95vw]">
                                <DialogHeader>
                                    <DialogTitle>Публичная оферта</DialogTitle>
                                </DialogHeader>
                                <iframe
                                    src="/legal/offer-example.pdf"
                                    className="w-full h-full rounded-md border"
                                    title="Публичная оферта"
                                />
                            </DialogContent>
                        </Dialog>
                    </div>
                </div>

                <div className="flex flex-col items-center md:items-start gap-1 text-[10px] text-text-secondary/60 border-t pt-4">
                    <p>Смирнова Людмила Анатольевна</p>
                    <div className="flex flex-wrap justify-center md:justify-start gap-x-4 gap-y-1">
                        <p>ИНН: 784217026925</p>
                        <p>Режим налогообложения: НПД (Самозанятый)</p>
                    </div>
                    <div className="flex flex-wrap justify-center md:justify-start gap-x-4 gap-y-1">
                        <p>Email: Luci4ek@gmail.com</p>
                        <p>Тел: +7 (931) 212-20-91</p>
                    </div>
                </div>
            </div>
        </footer>
    );
}
