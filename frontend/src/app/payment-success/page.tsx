import { Suspense } from "react";

import { PaymentStatus } from "./payment-status";

export const metadata = {
  title: "Платёж принят — Lucy Nails Academy",
  description: "Проверяем оплату. Доступ к курсу откроется сразу после подтверждения платежа.",
};

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#FDFBF9]" />}>
      <PaymentStatus />
    </Suspense>
  );
}
