import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { VideoPlayer } from "@/components/course/VideoPlayer"
import { ApiError, getLessonPlayUrl } from "@/lib/api"

vi.mock("@/lib/api", async (original) => ({ ...await original<typeof import("@/lib/api")>(), getLessonPlayUrl: vi.fn() }))
beforeEach(() => { vi.mocked(getLessonPlayUrl).mockReset(); vi.useFakeTimers(); vi.setSystemTime(new Date("2026-10-08T00:00:00Z")) })
afterEach(() => { cleanup(); vi.useRealTimers() })
const response = (token: string) => ({ video_url: `https://kinescope.io/embed/test?drmauthtoken=${token}`, title: "Lesson", provider: "kinescope", expires_in_seconds: 300 })

it("renews the signed URL after five minutes idle before resume", async () => {
    vi.mocked(getLessonPlayUrl).mockResolvedValueOnce(response("first")).mockResolvedValueOnce(response("renewed"))
    render(<VideoPlayer lessonId="lesson-1" title="Lesson" />)
    await act(async () => {})
    expect(screen.getByTitle("Lesson")).toHaveAttribute("src", response("first").video_url)
    await act(async () => { vi.advanceTimersByTime(301000); window.dispatchEvent(new Event("focus")) })
    expect(getLessonPlayUrl).toHaveBeenCalledTimes(2)
    expect(screen.getByTitle("Lesson")).toHaveAttribute("src", response("renewed").video_url)
})

it("removes stale playback on revoked access and does not retry on every focus", async () => {
    vi.mocked(getLessonPlayUrl).mockResolvedValueOnce(response("first")).mockRejectedValueOnce(new ApiError(403, "Access revoked", "Forbidden"))
    render(<VideoPlayer lessonId="lesson-1" title="Lesson" />)
    await act(async () => {})
    await act(async () => { vi.advanceTimersByTime(301000); window.dispatchEvent(new Event("focus")) })
    expect(screen.queryByTitle("Lesson")).not.toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Доступ ограничен" })).toBeVisible()
    await act(async () => { window.dispatchEvent(new Event("focus")) })
    expect(getLessonPlayUrl).toHaveBeenCalledTimes(2)
})

it("offers a user retry after transient playback failure", async () => {
    vi.mocked(getLessonPlayUrl).mockRejectedValueOnce(new Error("Temporary outage")).mockResolvedValueOnce(response("retry"))
    render(<VideoPlayer lessonId="lesson-1" title="Lesson" />)
    await act(async () => {})
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }))
    await act(async () => {})
    expect(screen.getByTitle("Lesson")).toBeVisible()
})
