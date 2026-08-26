"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertCircle, ArrowRight, CheckCircle, Clock3, Loader2, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getPublicApiUrl } from "@/lib/env";

type PaymentState = "checking" | "pending" | "paid" | "help";

const stateCopy: Record<PaymentState, { title: string; description: string }> = {
  checking: {
    title: "Проверяем оплату",
    description: "Получаем подтверждение от платёжной системы.",
  },
  pending: {
    title: "Ожидаем подтверждение",
    description: "Платёжная система ещё не прислала подтверждение. Обычно это занимает меньше минуты.",
  },
  paid: {
    title: "Оплата подтверждена",
    description: "Доступ к курсу открыт. Если это ваша первая покупка, ссылка установки пароля придёт на email.",
  },
  help: {
    title: "Нужна проверка оплаты",
    description: "Мы не смогли автоматически подтвердить статус. Не оплачивайте повторно — напишите в поддержку.",
  },
};

export function PaymentStatus() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");
  const token = searchParams.get("token");
  const [state, setState] = useState<PaymentState>("checking");

  useEffect(() => {
    if (!orderId || !token) {
      setState("help");
      return;
    }

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;

    const poll = async () => {
      attempts += 1;
      try {
        const endpoint = `${getPublicApiUrl()}/payments/orders/${encodeURIComponent(orderId)}/status?token=${encodeURIComponent(token)}`;
        const response = await fetch(endpoint, { signal: controller.signal, cache: "no-store" });
        if (!response.ok) {
          setState("help");
          return;
        }
        const result = (await response.json()) as { status: string };
        if (result.status === "paid") {
          setState("paid");
          window.history.replaceState({}, "", "/payment-success");
          return;
        }
        setState("pending");
      } catch (error) {
        if ((error as Error).name === "AbortError") return;
        setState("pending");
      }

      if (attempts >= 20) {
        setState("help");
        return;
      }
      timer = setTimeout(poll, 3000);
    };

    void poll();
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [orderId, token]);

  const copy = stateCopy[state];
  const Icon = state === "paid" ? CheckCircle : state === "help" ? AlertCircle : Clock3;

  return (
    <div className="min-h-screen bg-[#FDFBF9] flex items-center justify-center px-4">
      <div className="max-w-lg w-full text-center space-y-8">
        <div className="relative mx-auto w-24 h-24">
          <div className="absolute inset-0 bg-[#D4AF37]/20 rounded-full animate-ping opacity-30" />
          <div className="relative w-24 h-24 bg-gradient-to-br from-[#db3f6e] to-[#b02a52] rounded-full flex items-center justify-center shadow-lg">
            {state === "checking" ? (
              <Loader2 className="w-12 h-12 text-white animate-spin" />
            ) : (
              <Icon className="w-12 h-12 text-white" />
            )}
          </div>
        </div>

        <div className="space-y-3" aria-live="polite">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#D4AF37]/15 border border-[#D4AF37]/30">
            <Sparkles className="w-3.5 h-3.5 text-[#5A4B4B]" />
            <span className="text-[#5A4B4B] text-[10px] font-bold tracking-[0.2em] uppercase">
              Статус заказа
            </span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl text-text-primary">{copy.title}</h1>
          <p className="text-text-secondary text-lg leading-relaxed">{copy.description}</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-left">
          <p className="text-sm text-text-secondary">
            {state === "paid"
              ? "Можно переходить в личный кабинет. Письмо отправляется отдельно и может прийти чуть позже."
              : "Страница обновляет статус автоматически. Не закрывайте её и не создавайте повторный платёж."}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {state === "paid" && (
            <Button asChild className="rounded-full px-8 h-12 bg-gradient-to-r from-[#db3f6e] to-[#b02a52]">
              <Link href="/auth/login">
                Войти в кабинет <ArrowRight className="ml-2 w-4 h-4" />
              </Link>
            </Button>
          )}
          <Button asChild variant="outline" className="rounded-full px-8 h-12">
            <Link href="/">На главную</Link>
          </Button>
        </div>

        <p className="text-xs text-text-secondary/70">
          Проблема с доступом? Напишите в{" "}
          <a href="https://t.me/lucysmirnova_nails" className="text-[#db3f6e] hover:underline" target="_blank" rel="noopener noreferrer">
            Telegram
          </a>
          .
        </p>
      </div>
    </div>
  );
}
