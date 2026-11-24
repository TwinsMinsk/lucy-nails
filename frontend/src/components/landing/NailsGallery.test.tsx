import { act, cleanup, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { GalleryItem } from "@/lib/landing/course-content"
import { NailsGallery } from "./NailsGallery"

// Embla needs layout and IntersectionObserver, which jsdom does not have: a fake API stands in for it.
const embla = vi.hoisted(() => {
    type Handler = () => void
    const state = {
        slideCount: 0,
        registry: [] as number[][],
        selected: 0,
        inView: [] as number[],
        handlers: new Map<string, Set<Handler>>(),
    }
    const api = {
        slideNodes: () => Array.from({ length: state.slideCount }),
        internalEngine: () => ({ slideRegistry: state.registry }),
        selectedScrollSnap: () => state.selected,
        slidesInView: () => state.inView,
        scrollPrev: vi.fn(),
        scrollNext: vi.fn(),
        scrollTo: vi.fn(),
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

function setup(items: GalleryItem[], carousel: { registry: number[][]; selected?: number; inView: number[] }) {
    embla.state.slideCount = items.length
    embla.state.registry = carousel.registry
    embla.state.selected = carousel.selected ?? 0
    embla.state.inView = carousel.inView
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

const captions = () => [...document.querySelectorAll("figcaption")] as HTMLElement[]
const expectOpacities = (expected: string[]) =>
    waitFor(() => expect(captions().map((c) => c.style.opacity)).toEqual(expected))

afterEach(() => cleanup())

describe("NailsGallery captions", () => {
    it("shows every caption when all works fit without scrolling", async () => {
        // Two works at 1024px: both in view, Embla turns loop off and exposes one snap.
        setup([item(1), item(2)], { registry: [[0, 1]], inView: [0, 1] })

        await expectOpacities(["1", "1"])
        expect(screen.queryByRole("button", { name: "Следующая работа" })).not.toBeInTheDocument()
        expect(screen.queryByRole("button", { name: /^Работа 1 из/ })).not.toBeInTheDocument()
    })

    it("shows only the current work's caption in a scrolling carousel and follows the selection", async () => {
        setup([item(1), item(2)], { registry: [[0], [1]], inView: [0] })
        await expectOpacities(["1", "0"])

        act(() => {
            embla.state.selected = 1
            embla.state.inView = [1]
            embla.api.emit("select")
        })

        await expectOpacities(["0", "1"])
        expect(screen.getByRole("button", { name: "Работа 2 из 2" })).toHaveAttribute("aria-current", "true")
    })

    it("treats the centred slide of a merged edge snap as the current work", async () => {
        // Four works at 1440px: Embla cannot loop and merges the edge snaps into [[0, 1], [2, 3]].
        setup([item(1), item(2), item(3), item(4)], { registry: [[0, 1], [2, 3]], inView: [0, 1, 2] })

        await expectOpacities(["0", "1", "0", "0"])
        act(() => { screen.getByRole("button", { name: "Работа 4 из 4" }).click() })
        expect(embla.api.scrollTo).toHaveBeenCalledWith(1)
    })

    it("renders only the tag for an empty caption", () => {
        setup([item(1, { caption: "   " })], { registry: [[0]], inView: [0] })

        const [caption] = captions()
        expect(caption).toHaveTextContent("Техника 1")
        expect(caption.querySelector("p")).toBeNull()
    })

    it("renders no badge for an empty technique", () => {
        setup([item(1, { technique: "" })], { registry: [[0]], inView: [0] })

        const [caption] = captions()
        expect(caption.querySelector('[data-slot="badge"]')).toBeNull()
        expect(caption).toHaveTextContent("Подпись 1")
    })

    it("does not clamp a long caption", () => {
        const long = "Длинная подпись из CMS. ".repeat(12).trim()
        setup([item(1, { caption: long })], { registry: [[0]], inView: [0] })

        const text = captions()[0].querySelector("p")!
        expect(text).toHaveTextContent(long)
        expect(text.className).not.toMatch(/line-clamp|truncate/)
        expect(text).toHaveClass("break-words")
    })
})
