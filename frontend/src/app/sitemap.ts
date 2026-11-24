import type { MetadataRoute } from "next";

import { getPublishedCourses } from "@/lib/api";
import { getPublicSiteUrl } from "@/lib/env";
import { getLandingCourseId } from "@/lib/landing/loader";
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
    // The landing course page declares "/" as canonical, so only other courses are listed.
    // getLandingCourseId throws while that course is unknown (landing API down, nothing confirmed
    // yet), so an outage never lists the landing course under its own URL.
    const [catalog, landingCourseId] = await Promise.all([getPublishedCourses(), getLandingCourseId()]);
    return [
      ...staticRoutes,
      ...catalog.courses.filter((course) => course.id !== landingCourseId).map((course) => ({
        url: `${siteUrl}/courses/${course.id}`,
        lastModified: optionalDate(course.created_at),
        changeFrequency: "weekly" as const,
        priority: 0.8,
      })),
    ];
  } catch {
    return staticRoutes;
  }
}
