export function safeNextPath(value: string | null, fallback = "/dashboard"): string {
  if (!value) return fallback;
  let decoded = value;
  for (let depth = 0; depth < 5; depth++) {
    if (!decoded.startsWith("/") || decoded.startsWith("//")) return fallback;
    if (/[\\\u0000-\u0020\u007f]/.test(decoded)) return fallback;
    try {
      const url = new URL(decoded, "https://navigation.invalid");
      if (url.origin !== "https://navigation.invalid" || url.pathname.startsWith("/auth/")) return fallback;
      const next = decodeURIComponent(decoded);
      if (next === decoded) return value;
      decoded = next;
    } catch {
      return fallback;
    }
  }
  return fallback;
}
