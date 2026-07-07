"use client";

import { FileDown, ImageDown, Share2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { certificateFileUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

interface CertificateActionsProps {
  certificateNumber: string;
  className?: string;
}

export function CertificateActions({ certificateNumber, className }: CertificateActionsProps) {
  const handleShare = async () => {
    const url = `${window.location.origin}/certificate/${certificateNumber}`;

    if (navigator.share) {
      try {
        await navigator.share({ title: "Мой сертификат Lucy Nails Academy", url });
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
      }
      return;
    }

    await navigator.clipboard.writeText(url);
    toast.success("Ссылка скопирована");
  };

  return (
    <div className={cn("flex flex-wrap gap-2 justify-center", className)}>
      <Button
        asChild
        className="bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white rounded-full"
      >
        <a href={certificateFileUrl(certificateNumber, "pdf")}>
          <FileDown />
          Скачать PDF
        </a>
      </Button>
      <Button
        asChild
        variant="outline"
        className="border border-[#D4AF37]/50 text-[#8a6d1f] hover:bg-[#D4AF37]/10 rounded-full"
      >
        <a href={certificateFileUrl(certificateNumber, "png")}>
          <ImageDown />
          Скачать картинку
        </a>
      </Button>
      <Button
        variant="outline"
        className="rounded-full"
        onClick={handleShare}
      >
        <Share2 />
        Ссылка для проверки
      </Button>
    </div>
  );
}
