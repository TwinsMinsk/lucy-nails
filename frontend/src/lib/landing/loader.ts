import {
    galleryItems as staticGalleryItems,
    landingCourse,
    programModules as staticProgramModules,
    type GalleryItem,
    type ProgramModuleContent,
} from "@/lib/landing/course-content";
import { getLandingPayload, type GalleryItem as ApiGalleryItem } from "@/lib/api";

type LandingCourse = typeof landingCourse;

export type ResolvedHero = LandingCourse & {
    instructorImageUrl: string | null;
};

export interface ResolvedLandingContent {
    hero: ResolvedHero;
    modules: ProgramModuleContent[];
    gallery: GalleryItem[];
}

const STATIC_HERO: ResolvedHero = {
    ...landingCourse,
    instructorImageUrl: null,
};

const STATIC_FALLBACK: ResolvedLandingContent = {
    hero: STATIC_HERO,
    modules: staticProgramModules,
    gallery: staticGalleryItems,
};

function nonEmptyArray<T>(value: T[] | null | undefined): T[] | null {
    return value && value.length > 0 ? value : null;
}

function nonEmptyString(value: string | null | undefined): string | null {
    if (!value) return null;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
}

function mapGallery(item: ApiGalleryItem): GalleryItem {
    return {
        src: item.image_url,
        alt: item.alt ?? item.title,
        technique: item.title,
        caption: item.caption ?? "",
    };
}

/**
 * Server-side loader that fetches the landing payload from the backend and
 * merges it field-by-field with the static `course-content.ts` fallback.
 * Any individual API value that is empty/null falls back to static.
 */
export async function getLandingContent(): Promise<ResolvedLandingContent> {
    let payload;
    try {
        payload = await getLandingPayload();
    } catch {
        return STATIC_FALLBACK;
    }

    const apiHero = payload.hero;
    const heroStats =
        nonEmptyArray(apiHero.landing_hero_stats) ?? landingCourse.heroStats;
    const benefits = nonEmptyArray(apiHero.landing_benefits) ?? landingCourse.benefits;

    const hero: ResolvedHero = {
        ...landingCourse,
        title: nonEmptyString(apiHero.landing_title) ?? landingCourse.title,
        subtitle: nonEmptyString(apiHero.landing_subtitle) ?? landingCourse.subtitle,
        description: nonEmptyString(apiHero.landing_description) ?? landingCourse.description,
        audience: nonEmptyString(apiHero.landing_audience) ?? landingCourse.audience,
        supportNote: nonEmptyString(apiHero.landing_support_note) ?? landingCourse.supportNote,
        heroStats,
        benefits,
        instructorImageUrl: nonEmptyString(apiHero.landing_instructor_image_url),
    };

    const apiByTitle = new Map(payload.modules.map((m) => [m.title, m] as const));
    const modules: ProgramModuleContent[] = staticProgramModules.map((copy) => {
        const apiMod = apiByTitle.get(copy.title);
        if (!apiMod) return copy;
        return {
            ...copy,
            description: nonEmptyString(apiMod.landing_description) ?? copy.description,
            outcome: nonEmptyString(apiMod.landing_outcome) ?? copy.outcome,
            bullets: nonEmptyArray(apiMod.landing_bullets) ?? copy.bullets,
            mistakes: nonEmptyArray(apiMod.landing_mistakes) ?? copy.mistakes,
            duration: nonEmptyString(apiMod.landing_duration_label) ?? copy.duration,
        };
    });

    const apiGallery = payload.gallery.length > 0 ? payload.gallery.map(mapGallery) : null;
    const gallery = apiGallery ?? staticGalleryItems;

    return { hero, modules, gallery };
}
