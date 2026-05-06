const trimTrailingSlash = (value: string) => value.replace(/\/$/, "");

const publicEnvDefaults: Record<string, { development: string; production: string }> = {
  NEXT_PUBLIC_API_URL: {
    development: "http://localhost:8000/api",
    production: "https://api.lucysmirnova.ru/api",
  },
  NEXT_PUBLIC_SITE_URL: {
    development: "http://localhost:3000",
    production: "https://lucysmirnova.ru",
  },
};

function getPublicEnv(name: keyof typeof publicEnvDefaults): string {
  const value = process.env[name];
  if (value) return trimTrailingSlash(value);

  const fallback =
    process.env.NODE_ENV === "development"
      ? publicEnvDefaults[name].development
      : publicEnvDefaults[name].production;
  return trimTrailingSlash(fallback);
}

export function getPublicApiUrl(): string {
  const url = getPublicEnv("NEXT_PUBLIC_API_URL");
  if (!url.startsWith("http")) {
    return `https://${url}`;
  }
  return url.endsWith("/api") ? url : `${url}/api`;
}

export function getPublicSiteUrl(): string {
  const url = getPublicEnv("NEXT_PUBLIC_SITE_URL");
  if (!url.startsWith("http")) {
    return `https://${url}`;
  }
  return url;
}
