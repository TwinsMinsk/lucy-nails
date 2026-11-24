// The one place that builds links to the school's support bot in Telegram.

export const SUPPORT_BOT_FALLBACK_USERNAME = "lucynails_bot";

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
