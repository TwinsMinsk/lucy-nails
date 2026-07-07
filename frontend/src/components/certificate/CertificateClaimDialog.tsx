"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Award, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CertificateActions } from "@/components/certificate/CertificateActions";
import { fireConfetti } from "@/components/certificate/confetti";
import { claimCertificate, isAuthError, CertificateResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CertificateClaimDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  courseId: string;
  courseTitle: string;
  /** Non-null → dialog renders straight to the success view */
  certificate: CertificateResponse | null;
  onClaimed: (cert: CertificateResponse) => void;
  /** Prefill (e.g. from user profile later) */
  defaultName?: string;
}

// Mirrors backend `_FULL_NAME_PATTERN` (backend/app/schemas/certificate.py): first
// character must be a letter (Latin or Cyrillic); the rest may also contain
// apostrophes (straight or curly, for smart-quote names like «Д’Арк»), spaces,
// dots and hyphens.
const NAME_ALLOWED_CHARS_RE = /^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'’ .\-]*$/;

function validateFullName(raw: string): { value: string; error: string | null } {
  const value = raw.replace(/\s+/g, " ").trim();

  if (value.length < 2 || value.length > 120) {
    return { value, error: "Имя должно быть от 2 до 120 символов" };
  }
  if (!NAME_ALLOWED_CHARS_RE.test(value)) {
    return { value, error: "Имя должно начинаться с буквы. Допустимы буквы, пробел, дефис, апостроф и точка" };
  }

  const words = value.split(" ").filter(Boolean);
  const fullWords = words.filter((word) => (word.match(/[A-Za-zА-Яа-яЁё]/g)?.length ?? 0) >= 2);
  if (fullWords.length < 2) {
    return { value, error: "Укажите фамилию и имя полностью" };
  }

  return { value, error: null };
}

export function CertificateClaimDialog({
  open,
  onOpenChange,
  courseId,
  courseTitle,
  certificate,
  onClaimed,
  defaultName,
}: CertificateClaimDialogProps) {
  const router = useRouter();
  const [name, setName] = useState(defaultName ?? "");
  const [phase, setPhase] = useState<"form" | "loading">("form");
  const [error, setError] = useState<string | null>(null);

  const isSuccess = certificate !== null;

  const handleOpenChange = (next: boolean) => {
    if (phase === "loading" && !next) return;
    onOpenChange(next);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const { value, error: validationError } = validateFullName(name);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setPhase("loading");
    try {
      const cert = await claimCertificate(courseId, value);
      onClaimed(cert);
      void fireConfetti();
      toast.success("Сертификат готов!");
    } catch (err) {
      if (isAuthError(err)) {
        router.push("/auth/login");
        return;
      }
      setError(err instanceof Error ? err.message : "Не удалось получить сертификат");
    } finally {
      setPhase("form");
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className="sm:max-w-md"
        onInteractOutside={(e) => {
          if (phase === "loading") e.preventDefault();
        }}
        onEscapeKeyDown={(e) => {
          if (phase === "loading") e.preventDefault();
        }}
      >
        {isSuccess ? (
          <>
            <DialogHeader>
              <DialogTitle className="font-serif">Ваш сертификат готов! 🎉</DialogTitle>
            </DialogHeader>
            {certificate.png_url && (
              // eslint-disable-next-line @next/next/no-img-element -- remote certificate storage URL, no next/image remote pattern configured
              <img
                src={certificate.png_url}
                alt="Сертификат"
                className="rounded-xl border-4 border-[#D4AF37]/30 shadow-2xl"
              />
            )}
            <CertificateActions certificateNumber={certificate.certificate_number} />
            <p className="text-center text-sm text-muted-foreground">
              Поделитесь достижением в Instagram или Telegram — картинка уже готова для сторис.
            </p>
            <p className="text-center text-xs text-muted-foreground">
              № {certificate.certificate_number} · выдан{" "}
              {new Date(certificate.issued_at).toLocaleDateString("ru-RU")}
            </p>
            <Link
              href={`/certificate/${certificate.certificate_number}`}
              className="text-center text-sm font-medium text-[#db3f6e] hover:underline"
            >
              Открыть страницу сертификата →
            </Link>
          </>
        ) : (
          <>
            <DialogHeader>
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#D4AF37]/10">
                <Award className="h-6 w-6 text-[#D4AF37]" />
              </div>
              <DialogTitle className="text-center font-serif">Поздравляем, курс пройден!</DialogTitle>
              <DialogDescription className="text-center">
                Вы прошли все уроки курса «{courseTitle}». Получите именной сертификат Lucy Nails Academy.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="certificate-full-name">
                  Фамилия и имя — как напечатать на дипломе
                </Label>
                <Input
                  id="certificate-full-name"
                  autoFocus
                  placeholder="Анна Иванова"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={phase === "loading"}
                />
              </div>
              <div className="rounded-xl bg-[#fff1f4] border border-[#D4AF37]/40 p-4 text-center">
                <p className="text-[10px] tracking-[0.25em] text-[#b02a52]">LUCY NAILS ACADEMY</p>
                <p
                  className={cn(
                    "mt-2 font-serif italic text-2xl",
                    name.trim() ? "text-[#b02a52]" : "text-muted-foreground"
                  )}
                >
                  {name.trim() || "Ваше имя"}
                </p>
              </div>
              <p className="text-xs text-muted-foreground">
                Проверьте написание — именно так имя будет напечатано на сертификате.
              </p>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button
                type="submit"
                disabled={phase === "loading"}
                className="w-full rounded-full bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white"
              >
                {phase === "loading" ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Готовим ваш диплом…
                  </span>
                ) : (
                  "Получить сертификат"
                )}
              </Button>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
