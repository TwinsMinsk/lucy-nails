import { act, cleanup, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { GalleryItem } from "@/lib/landing/course-content"
import { NailsGallery } from "./NailsGallery"

// Embla needs layout, which jsdom does not have: a fake carousel with N scroll positions stands in for it.
const embla = vi.hoisted(() => {
    type Handler = () => void
    const state = {
        slideCount: 0,
        positions: 0,
        selected: 0,
        handlers: new Map<string, Set<Handler>>(),
    }
    const api = {
        slideNodes: () => Array.from({ length: state.slideCount }),
        scrollSnapList: () => Array.from({ length: state.positions }, (_, i) => i / Math.max(1, state.positions - 1)),
        selectedScrollSnap: () => state.selected,
        scrollTo(index: number) {
            state.selected = index
            api.emit("select")
        },
        scrollPrev: () => api.scrollTo(Math.max(0, state.selected - 1)),
        scrollNext: () => api.scrollTo(Math.min(state.positions - 1, state.selected + 1)),
        on(event: string, handler: Handler) {
            if (!state.handlers.has(event)) state.handlers.set(event, new Set())
            state.handlers.get(event)!.add(handler)
            return api
        },
        off(event: string, handler: Handler) {
            state.handlers.get(event)?.delete(handler)
            return api
        },
        emit(event: string) {
            state.handlers.get(event)?.forEach((handler) => handler())
        },
    }
    return { state, api }
})

// Reduced motion makes framer-motion apply the target styles without a spring.
vi.mock("framer-motion", async (importOriginal) => ({
    ...(await importOriginal<typeof import("framer-motion")>()),
    useReducedMotion: () => true,
}))
vi.mock("embla-carousel-react", () => ({ default: () => [() => undefined, embla.api] }))
vi.mock("next/image", () => ({
    // eslint-disable-next-line @next/next/no-img-element
    default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}))

function setup(items: GalleryItem[], positions: number) {
    embla.state.slideCount = items.length
    embla.state.positions = positions
    embla.state.selected = 0
    embla.state.handlers.clear()
    return render(<NailsGallery items={items} />)
}

const item = (n: number, overrides: Partial<GalleryItem> = {}): GalleryItem => ({
    src: `/nails-gallery/${n}.jpg`,
    alt: `Работа ${n}`,
    technique: `Техника ${n}`,
    caption: `Подпись ${n}`,
    ...overrides,
})

// What the user sees: captions at full opacity, by their text.
const visibleCaptions = () => [...document.querySelectorAll("figcaption")]
    .filter((caption) => (caption as HTMLElement).style.opacity === "1")
    .map((caption) => caption.querySelector("p")?.textContent)
const currentDot = () => screen.getAllByRole("button", { name: / из / })
    .filter((dot) => dot.getAttribute("aria-current") === "true")
    .map((dot) => dot.getAttribute("aria-label"))

afterEach(() => cleanup())

describe("NailsGallery", () => {
    it("carousel mode: each dot shows its own work's caption and marks itself current", async () => {
        // Every work has its own scroll position.
        setup([item(1), item(2), item(3)], 3)

        for (const n of [2, 3, 1]) {
            act(() => { screen.getByRole("button", { name: `Работа ${n} из 3` }).click() })
            await waitFor(() => expect(visibleCaptions()).toEqual([`Подпись ${n}`]))
            expect(currentDot()).toEqual([`Работа ${n} из 3`])
        }
    })

    it("strip mode: merged positions show every caption, dots are pages", async () => {
        // Four works at 1440px: Embla cannot loop and keeps two scroll positions.
        setup([item(1), item(2), item(3), item(4)], 2)

        expect(screen.queryByRole("button", { name: /^Работа/ })).not.toBeInTheDocument()
        for (const n of [2, 1]) {
            act(() => { screen.getByRole("button", { name: `Страница ${n} из 2` }).click() })
            await waitFor(() => expect(currentDot()).toEqual([`Страница ${n} из 2`]))
            expect(visibleCaptions()).toEqual(["Подпись 1", "Подпись 2", "Подпись 3", "Подпись 4"])
        }
    })

    it("strip mode with one position: everything fits, no arrows and no dots", async () => {
        setup([item(1), item(2), item(3)], 1)

        await waitFor(() => expect(visibleCaptions()).toEqual(["Подпись 1", "Подпись 2", "Подпись 3"]))
        expect(screen.queryByRole("button", { name: "Следующая работа" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: / из / })).not.toBeInTheDocument()
    })

    it("one work: no emphasis and no navigation", async () => {
        // One work has its own position (carousel rule), but a scaled photo would be cut by the gallery edge.
        setup([item(1)], 1)

        await waitFor(() => expect(visibleCaptions()).toEqual(["Подпись 1"]))
        const photo = document.querySelector("figure > div") as HTMLElement
        expect(photo.style.transform).not.toMatch(/scale\((?!1\))/)
        expect((document.querySelector("figure") as HTMLElement).style.opacity).toBe("1")
        expect(screen.queryByRole("button", { name: "Следующая работа" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: / из / })).not.toBeInTheDocument()
    })

    it("switches mode when Embla re-initialises with another number of positions", async () => {
        setup([item(1), item(2), item(3)], 3)
        await waitFor(() => expect(visibleCaptions()).toEqual(["Подпись 1"]))

        act(() => {
            embla.state.positions = 1
            embla.api.emit("reInit")
        })

        await waitFor(() => expect(visibleCaptions()).toEqual(["Подпись 1", "Подпись 2", "Подпись 3"]))
    })

    it("renders only the tag for an empty caption", () => {
        setup([item(1, { caption: "   " })], 1)

        const caption = document.querySelector("figcaption")!
        expect(caption).toHaveTextContent("Техника 1")
        expect(caption.querySelector("p")).toBeNull()
    })

    it("renders no badge for an empty technique", () => {
        setup([item(1, { technique: "" })], 1)

        const caption = document.querySelector("figcaption")!
        expect(caption.querySelector('[data-slot="badge"]')).toBeNull()
        expect(caption).toHaveTextContent("Подпись 1")
    })

    it("does not clamp a long caption", () => {
        const long = "Длинная подпись из CMS. ".repeat(12).trim()
        setup([item(1, { caption: long })], 1)

        const text = document.querySelector("figcaption p")!
        expect(text).toHaveTextContent(long)
        expect(text.className).not.toMatch(/line-clamp|truncate/)
        expect(text).toHaveClass("break-words")
    })
})
