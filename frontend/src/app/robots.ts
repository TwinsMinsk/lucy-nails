import type { MetadataRoute } from "next";

import { getPublicSiteUrl } from "@/lib/env";

const siteUrl = getPublicSiteUrl();

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/admin", "/dashboard", "/profile", "/courses/*/lessons/*"],
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
