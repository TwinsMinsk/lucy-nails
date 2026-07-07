import Link from "next/link";
import { Home, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Страница не найдена — Lucy Nails Academy",
};

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#FDFBF9] flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center space-y-8">
        <div className="relative mx-auto w-24 h-24">
          <div className="relative w-24 h-24 bg-gradient-to-br from-[#db3f6e] to-[#b02a52] rounded-full flex items-center justify-center shadow-[0_10px_30px_rgba(219,63,110,0.3)]">
            <Search className="w-12 h-12 text-white" />
          </div>
        </div>

        <div className="space-y-3">
          <p className="font-serif text-6xl text-text-primary">404</p>
          <h1 className="font-serif text-2xl md:text-3xl text-text-primary">
            Страница не найдена
          </h1>
          <p className="text-text-secondary text-lg leading-relaxed max-w-md mx-auto">
            Возможно, ссылка устарела или страница была перемещена.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button asChild className="rounded-full text-sm uppercase tracking-[0.15em] font-bold px-8 py-5 h-auto bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white hover:to-[#db3f6e] transition-all duration-500 shadow-[0_10px_25px_rgba(219,63,110,0.3)] hover:-translate-y-1 border-none">
            <Link href="/">
              <Home className="w-4 h-4" />
              На главную
            </Link>
          </Button>
          <Button asChild variant="outline" className="rounded-full text-sm uppercase tracking-[0.15em] font-medium px-8 py-5 h-auto border-2 border-gray-200 hover:border-[#D4AF37] transition-all duration-300">
            <Link href="/dashboard">В личный кабинет</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
