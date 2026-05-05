import type { MetadataRoute } from "next";

import { getPublishedCourses } from "@/lib/api";
import { getPublicSiteUrl } from "@/lib/env";

const siteUrl = getPublicSiteUrl();

function optionalDate(value?: string): Date | undefined {
  if (!value) return undefined;

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: siteUrl,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${siteUrl}/privacy`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${siteUrl}/terms`,
      lastModified: new Date(),
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];

  try {
    const catalog = await getPublishedCourses();
    return [
      ...staticRoutes,
      ...catalog.courses.map((course) => ({
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
