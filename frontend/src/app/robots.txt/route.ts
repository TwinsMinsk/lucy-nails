import { getPublicSiteUrl } from "@/lib/env";

// A route handler instead of robots.ts: MetadataRoute.Robots cannot express Yandex's Clean-param.
// Clean-param tells Yandex that ad tracking parameters do not change the page, so links like
// /?utm_source=... are not crawled and indexed as separate URLs.
const TRACKING_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "yclid", "ysclid", "gclid", "fbclid"];

export const dynamic = "force-static";

export function GET() {
  const body = [
    "User-Agent: *",
    "Allow: /",
    "Disallow: /admin",
    "Disallow: /dashboard",
    "Disallow: /profile",
    "Disallow: /courses/*/lessons/*",
    `Clean-param: ${TRACKING_PARAMS.join("&")}`,
    "",
    `Sitemap: ${getPublicSiteUrl()}/sitemap.xml`,
    "",
  ].join("\n");
  // Same caching as the robots.ts metadata route, so crawlers never get a stale copy.
  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=0, must-revalidate" },
  });
}
