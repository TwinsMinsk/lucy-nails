"use client";

import { PaymentButton } from "@/components/landing/PaymentButton";

// Only the self-paced tariff is sold.
type Tariff = "self";

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
