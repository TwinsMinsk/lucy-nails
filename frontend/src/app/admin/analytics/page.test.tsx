import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import AdminAnalyticsPage from "./page"

const sources = vi.hoisted(() => vi.fn().mockResolvedValue([{ source: "yandex", campaign: "launch", content: "ad-1", basis: "payment", date_basis: "paid_at_utc", orders: 1, paid_orders: 1, gross_revenue_kopecks: 10000, conversion_pct: 100 }]))
vi.mock("@/lib/api", () => ({
    adminGetReportOverview: vi.fn().mockResolvedValue({ gross_revenue_kopecks: 10000, refunded_kopecks: 0, net_revenue_kopecks: 10000, paid_orders: 1, new_students: 1 }),
    adminGetReportTimeseries: vi.fn().mockResolvedValue([]),
    adminGetReportFunnel: vi.fn().mockResolvedValue({ stages: [] }),
    adminGetReportSources: sources,
    adminGetReportTariffs: vi.fn().mockResolvedValue([]),
    adminGetReportCohorts: vi.fn().mockResolvedValue([]),
    adminGetReportProgress: vi.fn().mockResolvedValue({ active_students: 0, completed_lessons: 0, certificates_issued: 0 }),
    adminGetReportRefunds: vi.fn().mockResolvedValue([]),
    adminGetReportDelivery: vi.fn().mockResolvedValue({ sent: 0, total: 0, pending: 0, retry: 0, dead_letter: 0, success_rate_pct: 0 }),
    adminReportSourcesCsvUrl: () => "/csv",
}))
afterEach(cleanup)

describe("advertising reporting", () => {
    it("shows campaign and ad dimensions and separate acquisition basis", async () => {
        render(<AdminAnalyticsPage />)
        await waitFor(() => expect(screen.getAllByText("launch").length).toBeGreaterThan(0))
        expect(screen.getAllByText("ad-1").length).toBeGreaterThan(0)
        expect(screen.getByText(/Деньги по дате оплаты/)).toBeInTheDocument()
        expect(screen.getByText(/Когорта заказов/)).toBeInTheDocument()
        expect(screen.getByText(/UTC/)).toBeInTheDocument()
        fireEvent.change(screen.getByLabelText("Кампания"), { target: { value: "launch" } })
        fireEvent.change(screen.getByLabelText("Объявление"), { target: { value: "ad-1" } })
        fireEvent.click(screen.getByRole("button", { name: "Обновить" }))
        await waitFor(() => expect(sources).toHaveBeenCalledWith(expect.objectContaining({ campaign: "launch", content: "ad-1", basis: "payment" })))
    })
})
