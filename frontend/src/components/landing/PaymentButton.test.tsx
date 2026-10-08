import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"
import { PaymentButton } from "@/components/landing/PaymentButton"
vi.mock("@/components/landing/GuestCheckoutDialog", () => ({ GuestCheckoutDialog: () => null }))
afterEach(cleanup)
it("disables payment when the canonical course is unavailable", () => {
    render(<PaymentButton courseId={null} tariff="self">Начать обучение</PaymentButton>)
    expect(screen.getByRole("button", { name: "Начать обучение" })).toBeDisabled()
})
