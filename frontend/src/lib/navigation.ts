export function safeNextPath(value: string | null, fallback = "/dashboard"): string {
  if (!value) return fallback;
  if (!value.startsWith("/") || value.startsWith("//")) return fallback;
  if (value.startsWith("/auth/")) return fallback;
  return value;
}
