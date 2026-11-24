import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import AdminAnalyticsPage from "./page"

const mocks = vi.hoisted(() => ({
    sources: vi.fn(),
    overview: vi.fn(),
    delivery: vi.fn(),
    csv: vi.fn(),
}))
vi.mock("@/lib/api", () => ({
    adminGetReportOverview: mocks.overview,
    adminGetReportTimeseries: vi.fn().mockResolvedValue([]),
    adminGetReportFunnel: vi.fn().mockResolvedValue({ stages: [] }),
    adminGetReportSources: mocks.sources,
    adminGetReportTariffs: vi.fn().mockResolvedValue([]),
    adminGetReportCohorts: vi.fn().mockResolvedValue([]),
    adminGetReportProgress: vi.fn().mockResolvedValue({ active_students: 0, completed_lessons: 0, certificates_issued: 0 }),
    adminGetReportRefunds: vi.fn().mockResolvedValue([]),
    adminGetReportDelivery: mocks.delivery,
    adminDownloadReportSourcesCsv: mocks.csv,
}))

const overview = (paid: number) => ({ gross_revenue_kopecks: paid * 10000, refunded_kopecks: 0, net_revenue_kopecks: paid * 10000, paid_orders: paid, new_students: 1 })

beforeEach(() => {
    mocks.sources.mockResolvedValue([{ source: "yandex", campaign: "launch", content: "ad-1", basis: "payment", date_basis: "paid_at_utc", orders: 1, paid_orders: 1, gross_revenue_kopecks: 10000, conversion_pct: null }])
    mocks.overview.mockResolvedValue(overview(1))
    mocks.delivery.mockResolvedValue({ sent: 0, total: 0, pending: 0, retry: 0, dead_letter: 0, success_rate_pct: 0 })
    mocks.csv.mockResolvedValue(new Blob(["source\n"], { type: "text/csv" }))
})
afterEach(() => { cleanup(); vi.clearAllMocks(); vi.useRealTimers() })

describe("advertising reporting", () => {
    it("shows campaign and ad dimensions and separate acquisition basis", async () => {
        render(<AdminAnalyticsPage />)
        await waitFor(() => expect(screen.getAllByText("launch").length).toBeGreaterThan(0))
        expect(screen.getAllByText("ad-1").length).toBeGreaterThan(0)
        expect(screen.getByText(/Деньги по дате оплаты/)).toBeInTheDocument()
        expect(screen.getByText(/Когорта заказов/)).toBeInTheDocument()
        expect(screen.getAllByText(/UTC/).length).toBeGreaterThan(0)
        fireEvent.change(screen.getByLabelText("Кампания"), { target: { value: "launch" } })
        fireEvent.change(screen.getByLabelText("Объявление"), { target: { value: "ad-1" } })
        fireEvent.click(screen.getByRole("button", { name: "Обновить" }))
        await waitFor(() => expect(mocks.sources).toHaveBeenCalledWith(expect.objectContaining({ campaign: "launch", content: "ad-1", basis: "payment" })))
    })
})

describe("independent report sections", () => {
    it("keeps other sections when one report fails, and retries only that one", async () => {
        mocks.delivery.mockRejectedValueOnce(new Error("HTTP 500"))
        render(<AdminAnalyticsPage />)
        expect(await screen.findByText(/Отчёт не загрузился: HTTP 500/)).toBeVisible()
        expect(await screen.findByText("Gross revenue")).toBeVisible()
        expect(screen.getAllByText("launch").length).toBeGreaterThan(0)
        fireEvent.click(screen.getByRole("button", { name: "Повторить" }))
        expect(await screen.findByText("Success rate")).toBeVisible()
        expect(mocks.delivery).toHaveBeenCalledTimes(2)
        expect(mocks.overview).toHaveBeenCalledTimes(1)
    })

    it("never shows numbers of the previous period under new dates", async () => {
        render(<AdminAnalyticsPage />)
        expect((await screen.findAllByText("100 ₽", { exact: false })).length).toBeGreaterThan(0)
        let resolveNew: (value: unknown) => void = () => {}
        mocks.overview.mockImplementationOnce(() => new Promise((resolve) => { resolveNew = resolve }))
        fireEvent.change(screen.getByLabelText("С даты"), { target: { value: "2026-01-01" } })
        fireEvent.change(screen.getByLabelText("По дату"), { target: { value: "2026-01-31" } })
        fireEvent.click(screen.getByRole("button", { name: "Обновить" }))
        await waitFor(() => expect(screen.getByText("2026-01-01 — 2026-01-31")).toBeVisible())
        expect(screen.queryByText("Gross revenue")).not.toBeInTheDocument()
        await act(async () => { resolveNew(overview(7)) })
        expect((await screen.findAllByText("700 ₽", { exact: false })).length).toBe(2)
        expect(mocks.overview).toHaveBeenLastCalledWith({ date_from: "2026-01-01", date_to: "2026-01-31" })
    })

    it("computes the default period when the page opens", async () => {
        vi.useFakeTimers({ toFake: ["Date"] })
        vi.setSystemTime(new Date("2031-05-20T12:00:00Z"))
        render(<AdminAnalyticsPage />)
        expect(screen.getByLabelText("По дату")).toHaveValue("2031-05-20")
        expect(screen.getByLabelText("С даты")).toHaveValue("2031-04-21")
        await waitFor(() => expect(mocks.overview).toHaveBeenCalledWith({ date_from: "2031-04-21", date_to: "2031-05-20" }))
    })

    it("downloads the CSV for the applied filter through the API client", async () => {
        const createUrl = vi.fn(() => "blob:csv")
        Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: vi.fn() })
        render(<AdminAnalyticsPage />)
        await screen.findByText("Gross revenue")
        // Typed but not applied: the tables still show the old filter.
        fireEvent.change(screen.getByLabelText("Кампания"), { target: { value: "not-applied" } })
        fireEvent.click(screen.getByRole("button", { name: /CSV источников/ }))
        await waitFor(() => expect(mocks.csv).toHaveBeenCalledTimes(1))
        const params = mocks.csv.mock.calls[0][0]
        expect(params).toMatchObject({ basis: "payment" })
        expect(params).not.toHaveProperty("campaign")
        await waitFor(() => expect(createUrl).toHaveBeenCalled())
    })
})
