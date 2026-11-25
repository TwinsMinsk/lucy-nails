import { TelegramIcon } from "@/components/support/TelegramIcon";
import { SUPPORT_EMAIL, SUPPORT_EMAIL_HREF, supportBotUrl } from "@/lib/support";
import { cn } from "@/lib/utils";

interface PaymentSupportNoteProps {
  className?: string;
}

const linkClassName = "font-medium text-primary underline underline-offset-4 hover:no-underline";

// A quiet text line next to the pay button: visible, but never a second CTA.
// The email stays next to the bot, which answers only once the help desk is set up.
export function PaymentSupportNote({ className }: PaymentSupportNoteProps) {
  return (
    <p className={cn("text-center text-sm leading-relaxed text-text-secondary", className)}>
      <TelegramIcon className="mr-1.5 inline-block h-4 w-4 align-[-0.2em] text-[#229ED9]" />
      Вопросы по оплате?{" "}
      <a href={supportBotUrl()} target="_blank" rel="noopener noreferrer" className={linkClassName}>
        Напишите в поддержку в Telegram
      </a>{" "}
      или на почту{" "}
      <a href={SUPPORT_EMAIL_HREF} className={linkClassName}>
        {SUPPORT_EMAIL}
      </a>
    </p>
  );
}
