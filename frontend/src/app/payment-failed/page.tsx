import Link from "next/link";
import { ArrowRight, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";

// Prodamus sends buyers here (cabinet "Fail URL"); payment links have no per-link fail URL.
export const metadata = {
  title: "Оплата не прошла",
  description: "Платёж не завершён, доступ к курсу не оформлен. Можно попробовать оплатить ещё раз.",
  robots: { index: false, follow: false },
};

const reasons = [
  "банк отклонил платёж или на карте не хватило средств;",
  "не пришло подтверждение из приложения банка или СБП;",
  "оплату отменили или закрыли страницу оплаты.",
];

export default function PaymentFailedPage() {
  return (
    <div className="min-h-screen bg-[#FDFBF9] flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center space-y-8">
        <div className="mx-auto w-24 h-24 rounded-full flex items-center justify-center shadow-lg bg-[#FCEFD9] text-[#8A5A12]">
          <XCircle className="w-12 h-12" aria-hidden="true" />
        </div>

        <div className="space-y-3">
          <h1 className="font-serif text-3xl md:text-4xl text-text-primary">Оплата не прошла</h1>
          <p className="text-text-secondary text-lg leading-relaxed">
            Платёж не завершён, доступ к курсу не оформлен. Попробуйте ещё раз — можно выбрать другой способ оплаты.
          </p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-left space-y-3 text-sm text-text-secondary">
          <p className="font-medium text-text-primary">Частые причины</p>
          <ul className="list-disc pl-5 space-y-1">
            {reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
          <p>
            Если деньги всё же списались, не оплачивайте повторно — напишите нам и укажите email, на который
            оформляли оплату. Проверим платёж вручную.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button asChild className="rounded-full px-8 h-12">
            <Link href="/#pricing">
              Попробовать ещё раз <ArrowRight className="ml-2 w-4 h-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" className="rounded-full px-8 h-12">
            <Link href="/">На главную</Link>
          </Button>
        </div>

        <p className="text-sm text-text-secondary">
          Вопросы по оплате? Напишите в{" "}
          <a
            href="https://t.me/lucysmirnova_nails"
            className="text-primary underline underline-offset-4 hover:no-underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Telegram
          </a>
          .
        </p>
      </div>
    </div>
  );
}
