import { Suspense } from "react"
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import Dashboard from "@/app/(protected)/dashboard/page"
import Lesson from "@/app/(protected)/courses/[id]/lessons/[lessonId]/page"
import * as api from "@/lib/api"

const router = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock("next/navigation", () => ({ useRouter: () => router }))
vi.mock("@/components/course/VideoPlayer", () => ({ VideoPlayer: () => <div>Preview player</div> }))
vi.mock("@/components/certificate/CertificateClaimDialog", () => ({ CertificateClaimDialog: () => null }))
vi.mock("@/lib/api", async (original) => ({ ...await original<typeof api>(), getMe: vi.fn(), getMyCourses: vi.fn(), getMyExpiredCourses: vi.fn(), getLesson: vi.fn(), getPublicCourseModules: vi.fn(), getCourseProgress: vi.fn(), updateLessonProgress: vi.fn(), getCertificateStatus: vi.fn(), getPublicCourse: vi.fn() }))
beforeEach(() => {
    vi.mocked(api.getMe).mockResolvedValue({ id: "student", email: "student@example.test", role: "student", email_verified_at: "2026-10-07T00:00:00", created_at: "2026-10-07T00:00:00" })
    vi.mocked(api.getMyExpiredCourses).mockResolvedValue([])
    vi.mocked(api.getMyCourses).mockResolvedValue([])
    vi.mocked(api.getPublicCourseModules).mockResolvedValue([{ id: "module", course_id: "course", title: "Module", order_index: 1, is_published: true, lessons: [{ id: "preview", title: "Preview", order_index: 1, is_preview: true }] }] as unknown as api.ModuleResponse[])
    vi.mocked(api.getLesson).mockResolvedValue({ id: "preview", module_id: "module", title: "Preview", is_preview: true, duration_seconds: 60, order_index: 1 })
    vi.mocked(api.getCourseProgress).mockRejectedValue(new api.ApiError(403, "Course access required", "Forbidden"))
    vi.spyOn(console, "error").mockImplementation(() => undefined)
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

it("shows a retryable dashboard API error instead of an empty course account", async () => {
    vi.mocked(api.getMyCourses).mockRejectedValueOnce(new Error("Service unavailable")).mockResolvedValueOnce([])
    render(<Dashboard />)
    expect(await screen.findByText("Не удалось загрузить ваши курсы")).toBeVisible()
    expect(screen.queryByText("У вас пока нет курсов")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }))
    expect(await screen.findByRole("heading", { name: /Добро пожаловать/ })).toBeVisible()
})

it("renders an allowed preview when course progress is forbidden and hides paid progress controls", async () => {
    const params = Promise.resolve({ id: "course", lessonId: "preview" })
    await act(async () => { render(<Suspense fallback="Loading"><Lesson params={params} /></Suspense>) })
    expect(await screen.findByText("Preview player")).toBeVisible()
    expect(screen.queryByRole("button", { name: "Отметить просмотренным" })).not.toBeInTheDocument()
    expect(screen.getByText("Предпросмотр: прогресс курса недоступен без доступа")).toBeVisible()
})

it("does not hide a required lesson denial behind preview progress fallback", async () => {
    vi.mocked(api.getLesson).mockRejectedValueOnce(new api.ApiError(403, "Course access required", "Forbidden"))
    const params = Promise.resolve({ id: "course", lessonId: "locked" })
    await act(async () => { render(<Suspense fallback="Loading"><Lesson params={params} /></Suspense>) })
    expect(await screen.findByText("Доступ к курсу закончился или ещё не открыт")).toBeVisible()
    expect(screen.queryByText("Preview player")).not.toBeInTheDocument()
})

it("shows a revoked dashboard certificate without a claim or active certificate link", async () => {
    vi.mocked(api.getMyCourses).mockResolvedValue([{ id: "course", title: "Course", progress: 100, total_lessons: 1, completed_lessons: 1, certificate_number: "OLD", certificate_status: "revoked" }] as api.MyCourseResponse[])
    render(<Dashboard />)
    expect(await screen.findByText("Сертификат отозван")).toBeVisible()
    expect(screen.queryByText("Получить сертификат")).not.toBeInTheDocument()
    expect(screen.queryByText("Мой сертификат")).not.toBeInTheDocument()
})

it("shows a revoked lesson certificate without an active certificate link", async () => {
    vi.mocked(api.getCourseProgress).mockResolvedValue({ completed_lesson_ids: ["preview"], progress_percent: 100 })
    vi.mocked(api.getCertificateStatus).mockResolvedValue({ status: "revoked", eligible: false, progress_percent: 100, completed_lessons: 1, total_lessons: 1, certificate: { certificate_number: "OLD", status: "revoked", revoke_reason: "Refund" } } as unknown as api.CertificateStatusResponse)
    vi.mocked(api.getPublicCourse).mockResolvedValue({ title: "Course" } as api.CourseResponse)
    const params = Promise.resolve({ id: "course", lessonId: "preview" })
    await act(async () => { render(<Suspense fallback="Loading"><Lesson params={params} /></Suspense>) })
    expect(await screen.findByText("Сертификат отозван")).toBeVisible()
    expect(screen.queryByText("Мой сертификат")).not.toBeInTheDocument()
    expect(screen.queryByText("Получить сертификат")).not.toBeInTheDocument()
})
