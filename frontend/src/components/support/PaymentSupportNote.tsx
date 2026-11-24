import { TelegramIcon } from "@/components/support/TelegramIcon";
import { supportBotUrl } from "@/lib/support";
import { cn } from "@/lib/utils";

interface PaymentSupportNoteProps {
  className?: string;
}

// A quiet text line next to the pay button: visible, but never a second CTA.
export function PaymentSupportNote({ className }: PaymentSupportNoteProps) {
  return (
    <p className={cn("flex items-center justify-center gap-2 text-sm text-text-secondary", className)}>
      <TelegramIcon className="h-4 w-4 shrink-0 text-[#229ED9]" />
      <span>
        Вопросы по оплате?{" "}
        <a
          href={supportBotUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-primary underline underline-offset-4 hover:no-underline"
        >
          Напишите в поддержку в Telegram
        </a>
      </span>
    </p>
  );
}
