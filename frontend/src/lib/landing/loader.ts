import {
    galleryItems as staticGalleryItems,
    landingCourse,
    programModules as staticProgramModules,
    type GalleryItem,
    type ProgramModuleContent,
} from "@/lib/landing/course-content";
import { getLandingPayload, type GalleryItem as ApiGalleryItem, type LandingCourseSnapshot } from "@/lib/api";

import { formatCourseDuration } from "@/lib/format";

type LandingCourse = typeof landingCourse;

export type ResolvedHero = LandingCourse & {
    instructorImageUrl: string | null;
};

export interface ResolvedLandingContent {
    /**
     * false when the landing API could not be reached and the static marketing copy is shown.
     * Then `course: null` means "unknown", not "no published course".
     */
    available: boolean;
    course: LandingCourseSnapshot | null;
    hero: ResolvedHero;
    modules: ProgramModuleContent[];
    gallery: GalleryItem[];
}

const STATIC_HERO: ResolvedHero = {
    ...landingCourse,
    instructorImageUrl: null,
};

const STATIC_FALLBACK: ResolvedLandingContent = {
    available: false,
    course: null,
    hero: STATIC_HERO,
    modules: staticProgramModules,
    gallery: staticGalleryItems,
};

function mapGallery(item: ApiGalleryItem): GalleryItem {
    return {
        src: item.image_url,
        alt: item.alt ?? item.title,
        technique: item.title,
        caption: item.caption ?? "",
    };
}

export class LandingUnavailableError extends Error {
    constructor() {
        super("Landing course is unknown: the landing API is unavailable");
        this.name = "LandingUnavailableError";
    }
}

// The landing course id the API last confirmed in this server process. undefined: never loaded.
let lastKnownLandingCourseId: string | null | undefined;

/**
 * Id of the course the landing page sells (null: nothing is published).
 * While the landing API is down, answers with the last confirmed id; with none yet, throws
 * LandingUnavailableError so callers never treat an outage as "no published course".
 */
export async function getLandingCourseId(): Promise<string | null> {
    const landing = await getLandingContent();
    if (landing.available) return landing.course?.id ?? null;
    if (lastKnownLandingCourseId !== undefined) return lastKnownLandingCourseId;
    throw new LandingUnavailableError();
}

export async function getLandingContent(): Promise<ResolvedLandingContent> {
    let payload;
    try {
        payload = await getLandingPayload();
    } catch {
        return STATIC_FALLBACK;
    }

    const apiHero = payload.hero;
    const course = payload.course ?? null;
    lastKnownLandingCourseId = course?.id ?? null;
    const hero: ResolvedHero = {
        ...landingCourse,
        title: apiHero.landing_title ?? course?.title ?? "Курс пока не опубликован",
        subtitle: apiHero.landing_subtitle ?? "",
        description: apiHero.landing_description ?? "",
        audience: apiHero.landing_audience ?? "",
        supportNote: apiHero.landing_support_note ?? "",
        heroStats: apiHero.landing_hero_stats ?? [],
        benefits: apiHero.landing_benefits ?? [],
        instructorImageUrl: apiHero.landing_instructor_image_url ?? null,
        lessonsCount: course?.lessons_count ?? 0,
        duration: course ? formatCourseDuration(course.total_duration) ?? "" : "",
        access: course ? `${course.access_days} дней` : "",
    };
    const modules = payload.modules.map((item) => {
        const fallback = staticProgramModules.find((module) => module.title === item.title);
        return {
            slug: fallback?.slug ?? item.id,
            title: item.title,
            duration: item.landing_duration_label ?? fallback?.duration ?? "",
            description: item.landing_description ?? fallback?.description ?? "",
            outcome: item.landing_outcome ?? fallback?.outcome ?? "",
            bullets: item.landing_bullets ?? fallback?.bullets ?? [],
            mistakes: item.landing_mistakes ?? fallback?.mistakes ?? [],
        };
    });
    return { available: true, course, hero, modules, gallery: payload.gallery.map(mapGallery) };
}
