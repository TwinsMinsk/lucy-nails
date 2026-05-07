"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { getMe, getPaymentLink, isAuthError } from "@/lib/api";
import { toast } from "sonner";
import { GuestCheckoutDialog } from "@/components/landing/GuestCheckoutDialog";

interface PaymentButtonProps {
  /** UUID курса с API или `"default"` — первый опубликованный курс на бэкенде */
  courseId: string | null;
  tariff: "self" | "support";
  children?: React.ReactNode;
  className?: string;
}

function resolveCourseIdForCheckout(raw: string | null): string {
  const s = raw?.trim();
  if (!s) return "default";
  return s;
}

export function PaymentButton({ courseId, tariff, children, className }: PaymentButtonProps) {
  const [loading, setLoading] = useState(false);
  const [guestOpen, setGuestOpen] = useState(false);
  const effectiveCourseId = resolveCourseIdForCheckout(courseId);

  const handlePayment = async () => {
    const hasSession = typeof document !== "undefined" && document.cookie.includes("auth_session=1");

    if (!hasSession) {
      toast.info("Можно оплатить без регистрации", {
        description: "Укажите email, и после оплаты мы отправим данные для входа.",
      });
      setGuestOpen(true);
      return;
    }

    try {
      setLoading(true);

      const user = await getMe();
      const data = await getPaymentLink({
        course_id: effectiveCourseId,
        tariff,
        customer_email: user.email,
      });

      if (data.url) {
        window.location.href = data.url;
      } else {
        toast.error("Ошибка при генерации ссылки", {
          description: "Попробуйте позже или напишите нам.",
        });
      }
    } catch (e) {
      console.error("Payment link error:", e);
      if (isAuthError(e)) {
        toast.info("Можно оплатить без регистрации", {
          description: "Укажите email, и после оплаты мы отправим данные для входа.",
        });
        setGuestOpen(true);
        return;
      }
      toast.error("Ошибка при переходе к оплате", {
        description: e instanceof Error ? e.message : "Попробуйте позже.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <GuestCheckoutDialog
        open={guestOpen}
        onOpenChange={setGuestOpen}
        courseId={effectiveCourseId}
        tariff={tariff}
      />
      <Button
        onClick={handlePayment}
        disabled={loading}
        className={
          className ??
          "relative overflow-hidden group w-full h-14 rounded-full text-sm uppercase tracking-[0.2em] font-bold bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white hover:to-[#db3f6e] transition-all duration-500 shadow-[0_10px_25px_rgba(219,63,110,0.3)] hover:shadow-[0_15px_35px_rgba(219,63,110,0.45)] hover:-translate-y-1 border-none ring-1 ring-white/10"
        }
      >
        {loading ? (
          <span className="flex items-center gap-2 relative z-10 drop-shadow-md">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Переход к оплате...</span>
          </span>
        ) : (
          <>
            <span className="relative z-10 drop-shadow-md">{children || "Начать обучение"}</span>
            <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-white/30 to-transparent z-0" />
          </>
        )}
      </Button>
    </>
  );
}
