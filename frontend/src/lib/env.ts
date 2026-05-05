const trimTrailingSlash = (value: string) => value.replace(/\/$/, "");

function getRequiredPublicEnv(name: string, developmentFallback: string): string {
  const value = process.env[name];
  if (value) return trimTrailingSlash(value);

  if (process.env.NODE_ENV === "development") {
    return trimTrailingSlash(developmentFallback);
  }

  throw new Error(`${name} is required for production build/runtime`);
}

export function getPublicApiUrl(): string {
  const url = getRequiredPublicEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000/api");
  if (!url.startsWith("http")) {
    return `https://${url}`;
  }
  return url.endsWith("/api") ? url : `${url}/api`;
}

export function getPublicSiteUrl(): string {
  const url = getRequiredPublicEnv("NEXT_PUBLIC_SITE_URL", "http://localhost:3000");
  if (!url.startsWith("http")) {
    return `https://${url}`;
  }
  return url;
}
