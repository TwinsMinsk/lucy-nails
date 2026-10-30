"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { getMe, getPaymentLink, isAuthError } from "@/lib/api";
import { toast } from "sonner";
import { GuestCheckoutDialog } from "@/components/landing/GuestCheckoutDialog";
import { captureCheckoutAttribution } from "@/lib/attribution";
import { sendYandexGoal, trackPublicEvent } from "@/lib/analytics-client";

interface PaymentButtonProps {
  /** Canonical published course ID; null disables checkout. */
  courseId: string | null;
  tariff: "self";
  children?: React.ReactNode;
  className?: string;
  /** Where the CTA sits, for the cta_click analytics event */
  location?: "pricing" | "dashboard_renewal";
}

export function PaymentButton({ courseId, tariff, children, className, location = "pricing" }: PaymentButtonProps) {
  const [loading, setLoading] = useState(false);
  const [guestOpen, setGuestOpen] = useState(false);
  const effectiveCourseId = courseId?.trim() || null;

  const handlePayment = async () => {
    if (!effectiveCourseId) return;
    void trackPublicEvent("cta_click", { tariff, location }, effectiveCourseId);
    sendYandexGoal("checkout_open");
    const hasSession = typeof document !== "undefined" && document.cookie.includes("auth_session=1");

    // The guest dialog explains itself; a toast here repeated its title and
    // covered the dialog's submit button on phones.
    if (!hasSession) {
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
        attribution: captureCheckoutAttribution(),
      });

      if (data.url) {
        sendYandexGoal("checkout");
        window.location.href = data.url;
      } else {
        toast.error("Ошибка при генерации ссылки", {
          description: "Попробуйте позже или напишите нам.",
        });
      }
    } catch (e) {
      console.error("Payment link error:", e);
      if (isAuthError(e)) {
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
      {effectiveCourseId && <GuestCheckoutDialog
        open={guestOpen}
        onOpenChange={setGuestOpen}
        courseId={effectiveCourseId}
        tariff={tariff}
      />}
      <Button
        onClick={handlePayment}
        disabled={loading || !effectiveCourseId}
        className={
          className ??
          "w-full h-14 rounded-full text-base font-semibold shadow-[0_10px_25px_rgba(189,48,97,0.3)] hover:shadow-[0_14px_32px_rgba(189,48,97,0.4)]"
        }
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
            <span>Переход к оплате…</span>
          </span>
        ) : (
          children || "Начать обучение"
        )}
      </Button>
    </>
  );
}
