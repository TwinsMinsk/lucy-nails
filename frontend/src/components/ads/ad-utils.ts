import { toast } from "sonner"

import type { AdFile, AdMaterial, AdMaterialStatus } from "@/lib/api"

export const STATUS_LABELS: Record<AdMaterialStatus, string> = {
    draft: "Черновик",
    ready: "Готов к публикации",
    published: "Опубликован",
}

export const STATUS_SHORT: Record<AdMaterialStatus, string> = {
    draft: "Черновик",
    ready: "Готов",
    published: "Опубликован",
}

export function mainFile(material: AdMaterial, role: AdFile["role"]): AdFile | undefined {
    return material.files.find((file) => file.role === role && !file.variant)
}

/** Hook variants ("b", "c") with their video and cover, in variant order. */
export function hookVariants(material: AdMaterial) {
    const variants = new Map<string, { video?: AdFile; cover?: AdFile }>()
    for (const file of material.files) {
        if (!file.variant || (file.role !== "video" && file.role !== "cover")) continue
        const entry = variants.get(file.variant) ?? {}
        entry[file.role] = file
        variants.set(file.variant, entry)
    }
    return [...variants.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([variant, files]) => ({ variant, ...files }))
}

export function teamFiles(material: AdMaterial): AdFile[] {
    return material.files.filter((file) => file.role === "voice" || file.role === "other")
}

export function formatSize(bytes: number): string {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`
    return `${(bytes / 1024 / 1024).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0).replace(".", ",")} МБ`
}

export function formatSeconds(seconds: number | null): string | null {
    if (!seconds) return null
    return seconds < 60 ? `${seconds} с` : `${Math.floor(seconds / 60)} мин ${seconds % 60} с`
}

export async function copyText(text: string, success: string) {
    try {
        await navigator.clipboard.writeText(text)
        toast.success(success)
    } catch {
        // Clipboard API is unavailable outside secure contexts and in some in-app browsers.
        const area = document.createElement("textarea")
        area.value = text
        area.setAttribute("readonly", "")
        area.style.position = "fixed"
        area.style.opacity = "0"
        document.body.appendChild(area)
        area.select()
        const copied = document.execCommand("copy")
        area.remove()
        if (copied) toast.success(success)
        else toast.error("Не получилось скопировать: выделите текст и скопируйте вручную")
    }
}

export function errorText(error: unknown): string | undefined {
    return error instanceof Error ? error.message : undefined
}
