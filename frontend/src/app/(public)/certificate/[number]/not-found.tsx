import Link from "next/link";
import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function CertificateNotFound() {
    return (
        <div className="max-w-md mx-auto my-24 px-4 text-center space-y-4">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-error/10">
                <SearchX className="h-8 w-8 text-error" />
            </div>
            <h1 className="font-serif text-2xl text-text-primary">Сертификат не найден</h1>
            <p className="text-text-secondary">
                Проверьте номер сертификата — возможно, в ссылке опечатка. Подлинные сертификаты
                Lucy Nails Academy открываются по ссылке из QR-кода на дипломе.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                <Button
                    asChild
                    className="rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white"
                >
                    <Link href="/">На главную</Link>
                </Button>
                <Button asChild variant="outline" className="rounded-full">
                    <Link href="/#program">Смотреть курсы</Link>
                </Button>
            </div>
        </div>
    );
}
