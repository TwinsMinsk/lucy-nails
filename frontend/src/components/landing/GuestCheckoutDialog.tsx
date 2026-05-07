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
import { getGuestPaymentLink } from "@/lib/api";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

interface GuestCheckoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  tariff: "self" | "support";
}

export function GuestCheckoutDialog({
  open,
  onOpenChange,
  courseId,
  tariff,
}: GuestCheckoutDialogProps) {
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const next = encodeURIComponent(`/?course=${courseId}&tariff=${tariff}#pricing`);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim().toLowerCase();
    if (!trimmed) {
      toast.error("Укажите email", { description: "На него пришлём данные для входа после оплаты." });
      return;
    }
    try {
      setSubmitting(true);
      const data = await getGuestPaymentLink({
        course_id: courseId,
        tariff,
        customer_email: trimmed,
        customer_phone: phone.trim() || undefined,
      });
      if (data.url) {
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
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Оплата без регистрации</DialogTitle>
          <DialogDescription>
            Укажите email — после успешной оплаты отправим пароль для входа в личный кабинет. Телефон
            необязателен.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="guest-checkout-email">Email</Label>
            <Input
              id="guest-checkout-email"
              type="email"
              autoComplete="email"
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
          <DialogFooter className="flex-col gap-2 sm:flex-col sm:space-x-0">
            <Button
              type="submit"
              disabled={submitting}
              className="w-full rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white"
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
