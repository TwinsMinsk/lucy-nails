import { Suspense } from "react";

import { PaymentStatus } from "./payment-status";

export const metadata = {
  title: "Платёж принят",
  description: "Проверяем оплату. Доступ к курсу откроется сразу после подтверждения платежа.",
  robots: { index: false, follow: false },
};

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#FDFBF9]" />}>
      <PaymentStatus />
    </Suspense>
  );
}
