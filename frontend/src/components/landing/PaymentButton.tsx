"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface PaymentButtonProps {
  courseId: string;
  tariff: "self" | "support";
  children?: React.ReactNode;
}

export function PaymentButton({ courseId, tariff, children }: PaymentButtonProps) {
  const [loading, setLoading] = useState(false);

  const handlePayment = async () => {
    try {
      setLoading(true);
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/payments/link`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ course_id: courseId, tariff }),
      });
      
      const data = await res.json();
      
      if (data.url) {
        window.location.href = data.url;
      } else {
        alert("Ошибка при генерации ссылки. Попробуйте позже.");
      }
    } catch (e) {
      console.error(e);
      alert("Ошибка сети. Проверьте подключение и повторите попытку.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      onClick={handlePayment}
      disabled={loading}
      className="relative overflow-hidden group w-full h-14 rounded-full text-sm uppercase tracking-[0.2em] font-bold bg-gradient-to-r from-[#db3f6e] to-[#b02a52] text-white hover:to-[#db3f6e] transition-all duration-500 shadow-[0_10px_25px_rgba(219,63,110,0.3)] hover:shadow-[0_15px_35px_rgba(219,63,110,0.45)] hover:-translate-y-1 border-none ring-1 ring-white/10"
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
  );
}
