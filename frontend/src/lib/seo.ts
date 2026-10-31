import type { LandingCourseSnapshot } from "@/lib/api";

export const SITE_NAME = "Lucy Smirnova";
// The school as an organisation: certificates, copyright and the Organization in JSON-LD,
// so search engines do not merge it with the author (Person "Люся Смирнова").
export const ORGANIZATION_NAME = "Lucy Smirnova Nails";
export const AUTHOR_NAME = "Люся Смирнова";

// Search snippet for the landing page. The CMS hero title stays in the H1 and social cards.
export const HOME_TITLE = "Онлайн-курс дизайна ногтей для мастеров — Люся Смирнова";
export const HOME_DESCRIPTION =
    "Авторский онлайн-курс Люси Смирновой: 11 техник nail art — фольга, втирка, стемпинг, слайдеры, аэрография. Видеоуроки для практикующих мастеров маникюра.";

// 1200x630 link preview under 300 KB. The CMS portrait is a 1.6 MB PNG in the wrong aspect ratio.
export const SOCIAL_IMAGE = {
    url: "/og/nail-design-pro.jpg",
    width: 1200,
    height: 630,
    alt: "Nail Design PRO — онлайн-курс дизайна ногтей Люси Смирновой",
};

// Next.js replaces a parent's openGraph object instead of merging it, so every page that sets
// openGraph has to spread these fields to keep og:type, og:locale, og:site_name and og:image.
export const baseOpenGraph = {
    type: "website" as const,
    locale: "ru_RU",
    siteName: SITE_NAME,
    images: [SOCIAL_IMAGE],
};

// Last change of each legal text, used as its sitemap lastmod. Update together with the page text.
export const LEGAL_UPDATED_AT = {
    privacy: "2026-10-30",
    terms: "2026-10-08",
};

type HomeJsonLdInput = {
    siteUrl: string;
    course: LandingCourseSnapshot | null;
    title: string;
    description: string;
    imageUrl: string;
};

export function buildHomeJsonLd({ siteUrl, course, title, description, imageUrl }: HomeJsonLdInput) {
    const organizationId = `${siteUrl}/#organization`;
    const authorId = `${siteUrl}/#author`;
    const graph: Record<string, unknown>[] = [
        {
            "@type": "Organization",
            "@id": organizationId,
            name: ORGANIZATION_NAME,
            url: siteUrl,
            // Google reads an Organization with a phone as a local business and asks for an image.
            image: new URL(SOCIAL_IMAGE.url, siteUrl).toString(),
            email: "Luci4ek@gmail.com",
            telephone: "+7 931 212-20-91",
            founder: { "@id": authorId },
        },
        {
            "@type": "Person",
            "@id": authorId,
            name: AUTHOR_NAME,
            worksFor: { "@id": organizationId },
        },
        {
            // Site name in search results: Google takes it from WebSite on the home page.
            "@type": "WebSite",
            "@id": `${siteUrl}/#website`,
            name: SITE_NAME,
            alternateName: ORGANIZATION_NAME,
            url: siteUrl,
            inLanguage: "ru",
            publisher: { "@id": organizationId },
        },
    ];

    if (course) {
        graph.push({
            "@type": "Course",
            name: title,
            description,
            url: siteUrl,
            image: new URL(imageUrl, siteUrl).toString(),
            inLanguage: "ru",
            isAccessibleForFree: false,
            provider: { "@id": organizationId },
            author: { "@id": authorId },
            offers: {
                "@type": "Offer",
                category: "Paid",
                price: course.price_self,
                priceCurrency: "RUB",
                url: `${siteUrl}/#pricing`,
            },
            hasCourseInstance: {
                "@type": "CourseInstance",
                courseMode: "Online",
                ...(course.total_duration > 0 && {
                    courseWorkload: `PT${Math.max(1, Math.round(course.total_duration / 60))}M`,
                }),
            },
        });
    }

    return { "@context": "https://schema.org", "@graph": graph };
}
