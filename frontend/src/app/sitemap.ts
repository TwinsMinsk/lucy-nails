import type { MetadataRoute } from "next";
import { PHASE_PRODUCTION_BUILD } from "next/constants";

import { getPublishedCourses } from "@/lib/api";
import { getPublicSiteUrl } from "@/lib/env";
import { resolvePrimaryCourseId } from "@/lib/landing/loader";
import { LEGAL_UPDATED_AT } from "@/lib/seo";

const siteUrl = getPublicSiteUrl();

function optionalDate(value?: string): Date | undefined {
  if (!value) return undefined;

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      // No lastmod: the landing is assembled from CMS records that carry no modification time.
      url: siteUrl,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${siteUrl}/privacy`,
      lastModified: LEGAL_UPDATED_AT.privacy,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${siteUrl}/terms`,
      lastModified: LEGAL_UPDATED_AT.terms,
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];

  try {
    // The primary course page declares "/" as canonical, so only other courses are listed.
    // resolvePrimaryCourseId throws when the primary course cannot be established, so an
    // outage never lists it under its own URL.
    const [catalog, primaryCourseId] = await Promise.all([getPublishedCourses(), resolvePrimaryCourseId()]);
    return [
      ...staticRoutes,
      ...catalog.courses.filter((course) => course.id !== primaryCourseId).map((course) => ({
        url: `${siteUrl}/courses/${course.id}`,
        lastModified: optionalDate(course.created_at),
        changeFrequency: "weekly" as const,
        priority: 0.8,
      })),
    ];
  } catch (error) {
    // The production build has no API: publish the static routes so the build succeeds.
    if (process.env.NEXT_PHASE === PHASE_PRODUCTION_BUILD) return staticRoutes;
    // At request time (ISR revalidation) a shortened map must not replace a complete one:
    // throwing keeps Next.js serving the last successfully generated sitemap.
    throw error;
  }
}
