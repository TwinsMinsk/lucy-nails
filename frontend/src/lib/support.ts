// The one place that builds links to the school's support: the bot in
// Telegram and the email shown next to it.

export const SUPPORT_BOT_FALLBACK_USERNAME = "lucynails_bot";

// The support mailbox the site shows in the footer and next to the bot link,
// so a working contact stays while the bot is being set up.
export const SUPPORT_EMAIL = "Luci4ek@gmail.com";
export const SUPPORT_EMAIL_HREF = `mailto:${SUPPORT_EMAIL}`;

// Telegram usernames: 5-32 characters of letters, digits and underscores.
const USERNAME_PATTERN = /^[A-Za-z0-9_]{5,32}$/;
// Telegram accepts at most 64 characters of A-Z a-z 0-9 _ - in ?start=.
const START_PARAM_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

export function supportBotUsername(): string {
  // Static access: Next.js inlines NEXT_PUBLIC_* only for process.env.NAME.
  const configured = (process.env.NEXT_PUBLIC_SUPPORT_BOT_USERNAME ?? "").trim().replace(/^@/, "");
  return USERNAME_PATTERN.test(configured) ? configured : SUPPORT_BOT_FALLBACK_USERNAME;
}

/** https://t.me/<bot>, with ?start=<param> when a valid parameter is given. */
export function supportBotUrl(startParam?: string | null): string {
  const url = `https://t.me/${supportBotUsername()}`;
  if (startParam && START_PARAM_PATTERN.test(startParam)) {
    return `${url}?start=${startParam}`;
  }
  return url;
}
