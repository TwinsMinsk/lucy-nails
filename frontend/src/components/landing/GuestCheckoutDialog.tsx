"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type ConsentState,
  focusFirstMissingConsent,
  hasFullConsent,
  NO_CONSENT,
  PersonalDataConsent,
} from "@/components/legal/PersonalDataConsent";
import { getGuestPaymentLink } from "@/lib/api";
import { CheckCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { captureCheckoutAttribution } from "@/lib/attribution";
import { sendYandexGoal } from "@/lib/analytics-client";
import { CONSENT_VERSION } from "@/lib/legal";

const CONSENT_ID = "guest-checkout-consent";

interface GuestCheckoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  tariff: "self";
}

export function GuestCheckoutDialog({
  open,
  onOpenChange,
  courseId,
  tariff,
}: GuestCheckoutDialogProps) {
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState<ConsentState>(NO_CONSENT);
  const [consentError, setConsentError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const next = encodeURIComponent(`/?course=${courseId}&tariff=${tariff}#pricing`);
  const consentGiven = hasFullConsent(consent);

  const handleConsentChange = (value: ConsentState) => {
    setConsent(value);
    if (hasFullConsent(value)) setConsentError(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consentGiven) {
      setConsentError(true);
      focusFirstMissingConsent(CONSENT_ID, consent);
      return;
    }
    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      toast.error("Укажите email", { description: "На него пришлём ссылку для входа после оплаты." });
      return;
    }
    try {
      setSubmitting(true);
      const data = await getGuestPaymentLink({
        course_id: courseId,
        tariff,
        customer_email: trimmed,
        customer_phone: phone.trim() || undefined,
        attribution: captureCheckoutAttribution(),
        offer_accepted: consent.offer,
        personal_data_consent: consent.personalData,
        consent_version: CONSENT_VERSION,
      });
      if (data.url) {
        sendYandexGoal("checkout");
        window.location.href = data.url;
      } else {
        toast.error("Не удалось получить ссылку на оплату");
      }
    } catch (err) {
      console.error("Guest payment link error:", err);
      toast.error("Ошибка при переходе к оплате", {
        description: err instanceof Error ? err.message : "Попробуйте позже.",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* Scroll inside the dialog: on small phones the form is taller than the screen */}
      <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto p-5 sm:max-w-md sm:p-6">
        <DialogHeader>
          <DialogTitle>Оплата без регистрации</DialogTitle>
          <DialogDescription>
            Укажите email — после оплаты пришлём ссылку, по которой вы создадите пароль для входа в кабинет.
            Телефон необязателен, но поможет быстрее найти платёж.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-2xl bg-[#fff1f4] border border-primary/20 p-3 sm:p-4 text-sm text-text-secondary space-y-2">
          <div className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-[#D4AF37] shrink-0 mt-0.5" />
            <span>Вы перейдёте на платёжную форму Prodamus.</span>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-[#D4AF37] shrink-0 mt-0.5" />
            <span>После подтверждения платежа доступ появится в кабинете в течение пары минут.</span>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="guest-checkout-email">Email</Label>
            <Input
              id="guest-checkout-email"
              type="email"
              autoComplete="email"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={submitting}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="guest-checkout-phone">Телефон (необязательно)</Label>
            <Input
              id="guest-checkout-phone"
              type="tel"
              autoComplete="tel"
              placeholder="+7 ..."
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={submitting}
            />
          </div>
          <PersonalDataConsent
            id={CONSENT_ID}
            value={consent}
            onChange={handleConsentChange}
            showError={consentError}
            disabled={submitting}
          />
          <DialogFooter className="flex-col gap-2 sm:flex-col sm:space-x-0">
            {/* aria-disabled (not disabled) keeps the click alive so we can explain why it is blocked */}
            <Button
              type="submit"
              disabled={submitting}
              aria-disabled={!consentGiven}
              className="w-full rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white aria-disabled:opacity-50 aria-disabled:cursor-not-allowed"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Переход к оплате…
                </span>
              ) : (
                "Перейти к оплате"
              )}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Уже есть аккаунт?{" "}
              <Link href={`/auth/login?next=${next}`} className="font-medium text-[#db3f6e] hover:underline">
                Войти
              </Link>
            </p>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
