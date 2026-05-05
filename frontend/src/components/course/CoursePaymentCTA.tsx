"use client";

import { PaymentButton } from "@/components/landing/PaymentButton";

type Tariff = "self" | "support";

export function CoursePaymentCTA({
  courseId,
  tariff,
  children,
  className,
}: {
  courseId: string;
  tariff: Tariff;
  children: React.ReactNode;
  /** Дополнительные классы для обёртки Button (передаются во внутренний Button) */
  className?: string;
}) {
  return (
    <PaymentButton courseId={courseId} tariff={tariff} className={className}>
      {children}
    </PaymentButton>
  );
}
