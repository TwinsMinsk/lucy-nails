import Link from "next/link";
import { CheckCircle, ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Платёж принят — Lucy Nails Academy",
  description: "Платёж принят Prodamus. Доступ откроется после подтверждения webhook.",
};

export default function PaymentSuccessPage() {
  return (
    <div className="min-h-screen bg-[#FDFBF9] flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center space-y-8">
        {/* Success Icon */}
        <div className="relative mx-auto w-24 h-24">
          <div className="absolute inset-0 bg-green-100 rounded-full animate-ping opacity-30" />
          <div className="relative w-24 h-24 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center shadow-[0_10px_30px_rgba(34,197,94,0.3)]">
            <CheckCircle className="w-12 h-12 text-white" />
          </div>
        </div>

        {/* Title */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gradient-to-r from-[#D4AF37] via-[#FFF3AD] to-[#BFA15F] border border-[#D4AF37]/30 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-[#5A4B4B]" />
            <span className="text-[#5A4B4B] text-[10px] font-bold tracking-[0.2em] uppercase">
              Успешно
            </span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl text-text-primary">
            Платёж принят!
          </h1>
          <p className="text-text-secondary text-lg leading-relaxed max-w-md mx-auto">
            Спасибо за покупку курса. Обычно доступ появляется в личном кабинете в течение пары минут после подтверждения оплаты.
          </p>
        </div>

        {/* Info Card */}
        <div className="bg-white rounded-2xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.06)] border border-gray-100 space-y-4 text-left">
          <h3 className="font-semibold text-text-primary text-sm uppercase tracking-wider">
            Что дальше?
          </h3>
          <ul className="space-y-3 text-text-secondary text-sm">
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-[#D4AF37]/10 text-[#D4AF37] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">1</span>
              <span>Если вы покупали после входа в аккаунт, просто вернитесь в личный кабинет</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-[#D4AF37]/10 text-[#D4AF37] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">2</span>
              <span>Если Prodamus создавал аккаунт по email, проверьте письмо с данными для входа</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-[#D4AF37]/10 text-[#D4AF37] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">3</span>
              <span>Если доступ не появился сразу, подождите 1-2 минуты и обновите кабинет</span>
            </li>
          </ul>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button asChild className="relative overflow-hidden group rounded-full text-sm uppercase tracking-[0.15em] font-bold px-8 py-5 h-auto bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white hover:to-[#db3f6e] transition-all duration-500 shadow-[0_10px_25px_rgba(219,63,110,0.3)] hover:shadow-[0_15px_35px_rgba(219,63,110,0.45)] hover:-translate-y-1 border-none ring-1 ring-white/10">
            <Link href="/auth/login">
              <span className="relative z-10 drop-shadow-md flex items-center gap-2">
                Войти в кабинет
                <ArrowRight className="w-4 h-4" />
              </span>
              <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/30 to-transparent z-0" />
            </Link>
          </Button>
          <Button asChild variant="outline" className="rounded-full text-sm uppercase tracking-[0.15em] font-medium px-8 py-5 h-auto border-2 border-gray-200 hover:border-[#D4AF37] transition-all duration-300">
            <Link href="/">
              На главную
            </Link>
          </Button>
        </div>

        {/* Support note */}
        <p className="text-xs text-text-secondary/60">
          Если доступ или письмо не появились, проверьте папку «Спам» или напишите нам в{" "}
          <a href="https://t.me/lucysmirnova_nails" className="text-[#db3f6e] hover:underline" target="_blank" rel="noopener">
            Telegram
          </a>
        </p>
      </div>
    </div>
  );
}
