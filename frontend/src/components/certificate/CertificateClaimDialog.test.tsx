import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"

import { CertificateClaimDialog } from "./CertificateClaimDialog"
import { CertificateResponse } from "@/lib/api"

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }))
afterEach(cleanup)

it("shows revoked status without download or claim actions", () => {
    render(<CertificateClaimDialog open onOpenChange={vi.fn()} courseId="course" courseTitle="Course" onClaimed={vi.fn()} certificate={{ certificate_number: "LN-2026-ABCDEF", status: "revoked", issued_at: "2026-10-08T00:00:00", revoke_reason: "Refund processed" } as CertificateResponse} />)
    expect(screen.getByRole("heading", { name: "Сертификат отозван" })).toBeVisible()
    expect(screen.queryByRole("link", { name: /Скачать/ })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Получить сертификат" })).not.toBeInTheDocument()
})
