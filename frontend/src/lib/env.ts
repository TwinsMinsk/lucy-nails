const trimTrailingSlash = (value: string) => value.replace(/\/$/, "");

export function getPublicApiUrl(): string {
  // Next.js replaces NEXT_PUBLIC_* values in browser bundles only for static
  // property access. Dynamic process.env[name] silently ignores staging URLs.
  const url = trimTrailingSlash(
    process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === "development"
        ? "http://localhost:8000/api"
        : "https://api.lucysmirnova.ru/api"),
  );
  if (!url.startsWith("http")) {
    return `https://${url}`;
  }
  return url.endsWith("/api") ? url : `${url}/api`;
}

export function getPublicSiteUrl(): string {
  const url = trimTrailingSlash(
    process.env.NEXT_PUBLIC_SITE_URL ||
      (process.env.NODE_ENV === "development"
        ? "http://localhost:3000"
        : "https://lucysmirnova.ru"),
  );
  if (!url.startsWith("http")) {
    return `https://${url}`;
  }
  return url;
}
