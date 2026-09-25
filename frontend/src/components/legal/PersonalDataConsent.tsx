"use client"

export interface ConsentState {
    offer: boolean
    personalData: boolean
}

export const NO_CONSENT: ConsentState = { offer: false, personalData: false }

export const hasFullConsent = (consent: ConsentState): boolean => consent.offer && consent.personalData

/** Move focus to the first box the user still has to tick (after a blocked submit). */
export function focusFirstMissingConsent(id: string, consent: ConsentState) {
    const missing = !consent.offer ? `${id}-offer` : !consent.personalData ? `${id}-personal-data` : null
    if (missing) document.getElementById(missing)?.focus()
}

interface PersonalDataConsentProps {
    id: string
    value: ConsentState
    onChange: (value: ConsentState) => void
    /** Show validation messages for unchecked boxes after the user tries to continue */
    showError?: boolean
    disabled?: boolean
}

const linkClassName = "font-medium text-[#db3f6e] underline-offset-2 hover:underline"

interface ConsentCheckboxProps {
    id: string
    checked: boolean
    onCheckedChange: (checked: boolean) => void
    error: string | null
    disabled: boolean
    children: React.ReactNode
}

function ConsentCheckbox({ id, checked, onCheckedChange, error, disabled, children }: ConsentCheckboxProps) {
    const errorId = `${id}-error`

    return (
        <div className="space-y-1">
            <div className="flex items-start gap-3">
                <input
                    id={id}
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => onCheckedChange(event.target.checked)}
                    disabled={disabled}
                    aria-required="true"
                    aria-invalid={error ? true : undefined}
                    aria-describedby={error ? errorId : undefined}
                    className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded border-input accent-[#db3f6e] disabled:cursor-not-allowed"
                />
                <label htmlFor={id} className="cursor-pointer text-sm leading-snug text-text-secondary">
                    {children}
                </label>
            </div>
            {error && (
                <p id={errorId} role="alert" className="pl-7 text-sm text-destructive">
                    {error}
                </p>
            )}
        </div>
    )
}

/**
 * Two separate required checkboxes: the offer and the personal-data consent
 * (152-FZ requires the consent to be separate from other documents).
 */
export function PersonalDataConsent({
    id,
    value,
    onChange,
    showError = false,
    disabled = false,
}: PersonalDataConsentProps) {
    return (
        <div className="space-y-2">
            <ConsentCheckbox
                id={`${id}-offer`}
                checked={value.offer}
                onCheckedChange={(offer) => onChange({ ...value, offer })}
                error={showError && !value.offer ? "Примите условия оферты, чтобы продолжить" : null}
                disabled={disabled}
            >
                Я принимаю условия{" "}
                <a href="/terms" target="_blank" rel="noopener noreferrer" className={linkClassName}>
                    оферты
                </a>
            </ConsentCheckbox>
            <ConsentCheckbox
                id={`${id}-personal-data`}
                checked={value.personalData}
                onCheckedChange={(personalData) => onChange({ ...value, personalData })}
                error={
                    showError && !value.personalData
                        ? "Дайте согласие на обработку персональных данных, чтобы продолжить"
                        : null
                }
                disabled={disabled}
            >
                Даю согласие на{" "}
                <a href="/privacy" target="_blank" rel="noopener noreferrer" className={linkClassName}>
                    обработку персональных данных
                </a>
            </ConsentCheckbox>
        </div>
    )
}
