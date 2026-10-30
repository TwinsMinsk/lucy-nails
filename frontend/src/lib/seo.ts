import type { LandingCourseSnapshot } from "@/lib/api";

export const SITE_NAME = "Lucy Nails Academy";
export const AUTHOR_NAME = "Люся Смирнова";

// Search snippet for the landing page. The CMS hero title stays in the H1 and social cards.
export const HOME_TITLE = "Онлайн-курс дизайна ногтей для мастеров — Люся Смирнова";
export const HOME_DESCRIPTION =
    "Авторский онлайн-курс Люси Смирновой: 11 техник nail art — фольга, втирка, стемпинг, слайдеры, аэрография. Видеоуроки для практикующих мастеров маникюра.";

// Next.js replaces a parent's openGraph object instead of merging it, so every page that sets
// openGraph has to spread these fields to keep og:type, og:locale and og:site_name.
export const baseOpenGraph = {
    type: "website",
    locale: "ru_RU",
    siteName: SITE_NAME,
} as const;

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
            name: SITE_NAME,
            url: siteUrl,
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
