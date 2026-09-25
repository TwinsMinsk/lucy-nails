"""Offer acceptance and personal-data consent captured at checkout and signup.

152-FZ requires the personal-data consent to be separate from other documents,
so both flags are collected and stored independently together with the
version of the texts the customer agreed to.
"""

from fastapi import HTTPException, status

# Bump whenever the offer or the personal-data consent text changes.
# Mirrored in frontend/src/lib/legal.ts.
CONSENT_VERSION = "2026-09-25"

CONSENT_REQUIRED_DETAIL = (
    "Чтобы продолжить, примите условия оферты и дайте согласие "
    "на обработку персональных данных"
)


def require_consent(offer_accepted: bool, personal_data_consent: bool) -> None:
    """Reject the request unless both the offer and the consent were accepted."""
    if not (offer_accepted and personal_data_consent):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=CONSENT_REQUIRED_DETAIL,
        )
