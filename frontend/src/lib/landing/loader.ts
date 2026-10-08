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

export async function getLandingContent(): Promise<ResolvedLandingContent> {
    let payload;
    try {
        payload = await getLandingPayload();
    } catch {
        return STATIC_FALLBACK;
    }

    const apiHero = payload.hero;
    const course = payload.course ?? null;
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
    const modules = payload.modules.map((item) => ({
        slug: item.id,
        title: item.title,
        duration: item.landing_duration_label ?? "",
        description: item.landing_description ?? "",
        outcome: item.landing_outcome ?? "",
        bullets: item.landing_bullets ?? [],
        mistakes: item.landing_mistakes ?? [],
    }));
    return { course, hero, modules, gallery: payload.gallery.map(mapGallery) };
}
