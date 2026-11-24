"""Signed order references for support bot deep links (``/start o_<token>``).

Telegram allows at most 64 characters of ``A-Z a-z 0-9 _ -`` in a start
parameter, so the token is the 16 raw bytes of the order UUID followed by a
16-byte truncated HMAC-SHA256, base64url without padding (43 characters).
With the ``o_`` prefix the parameter is 45 characters long, which also tells
it apart from a 43-character account link token that happens to start with
``o_``.

The reference only lets the support bot attach an order to a conversation for
the operators; the customer never gets order data back from the bot.
"""

import base64
import binascii
import hashlib
import hmac
from uuid import UUID

from app.core.config import settings

ORDER_START_PREFIX = "o_"
_SIGNATURE_BYTES = 16
_TOKEN_BYTES = 16 + _SIGNATURE_BYTES
ORDER_START_PARAM_LENGTH = len(ORDER_START_PREFIX) + 43
# Account link tokens are secrets.token_urlsafe(32) (app/api/telegram.py).
ACCOUNT_LINK_TOKEN_LENGTH = 43


def order_reference(order_id: UUID) -> str:
    """How alerts and the customer card name an order (Prodamus ``order_num``)."""
    return f"order|{order_id}"


def _order_link_key() -> bytes:
    # A key of its own, derived from the application secret with a purpose
    # label, so a signature made here is useless anywhere else.
    return hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        b"support-bot-order-link:v1",
        hashlib.sha256,
    ).digest()


def _signature(order_bytes: bytes) -> bytes:
    return hmac.new(_order_link_key(), order_bytes, hashlib.sha256).digest()[:_SIGNATURE_BYTES]


def issue_order_start_param(order_id: UUID) -> str:
    """Return ``o_<token>`` for https://t.me/<bot>?start=<param>."""
    raw = order_id.bytes + _signature(order_id.bytes)
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{ORDER_START_PREFIX}{token}"


def is_order_start_param(param: str) -> bool:
    return param.startswith(ORDER_START_PREFIX) and len(param) == ORDER_START_PARAM_LENGTH


def is_account_link_param(param: str) -> bool:
    """Whether a start parameter goes to account linking.

    Anything starting with ``o_`` is an order reference attempt, except a
    43-character account token that happens to start that way.
    """
    return not param.startswith(ORDER_START_PREFIX) or len(param) == ACCOUNT_LINK_TOKEN_LENGTH


def verify_order_start_param(param: str) -> UUID | None:
    """The order id of a genuine parameter, None for anything else."""
    if not is_order_start_param(param):
        return None
    token = param[len(ORDER_START_PREFIX):]
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (binascii.Error, ValueError):
        return None
    if len(raw) != _TOKEN_BYTES:
        return None
    order_bytes, supplied = raw[:16], raw[16:]
    if not hmac.compare_digest(supplied, _signature(order_bytes)):
        return None
    return UUID(bytes=order_bytes)
