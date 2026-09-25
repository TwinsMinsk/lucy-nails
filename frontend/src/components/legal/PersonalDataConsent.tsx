interface PersonalDataConsentProps {
    id: string
    checked: boolean
    onCheckedChange: (checked: boolean) => void
    /** Show the validation message when the user tries to continue without consent */
    showError?: boolean
    disabled?: boolean
}

const linkClassName = "font-medium text-[#db3f6e] underline-offset-2 hover:underline"

export function PersonalDataConsent({
    id,
    checked,
    onCheckedChange,
    showError = false,
    disabled = false,
}: PersonalDataConsentProps) {
    const errorId = `${id}-error`

    return (
        <div className="space-y-1.5">
            <div className="flex items-start gap-3">
                <input
                    id={id}
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => onCheckedChange(event.target.checked)}
                    disabled={disabled}
                    aria-invalid={showError || undefined}
                    aria-describedby={showError ? errorId : undefined}
                    className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded border-input accent-[#db3f6e] disabled:cursor-not-allowed"
                />
                <label htmlFor={id} className="cursor-pointer text-sm leading-snug text-text-secondary">
                    Я принимаю условия{" "}
                    <a href="/terms" target="_blank" rel="noopener noreferrer" className={linkClassName}>
                        оферты
                    </a>{" "}
                    и даю согласие на обработку персональных данных в соответствии с{" "}
                    <a href="/privacy" target="_blank" rel="noopener noreferrer" className={linkClassName}>
                        политикой конфиденциальности
                    </a>
                </label>
            </div>
            {showError && (
                <p id={errorId} className="pl-7 text-sm text-destructive">
                    Отметьте согласие, чтобы продолжить
                </p>
            )}
        </div>
    )
}
