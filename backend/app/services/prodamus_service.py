"""
Prodamus Service: генерация платёжной ссылки и проверка HMAC-подписи webhook.

Алгоритм подписи (из документации Prodamus):
  1. Все значения привести к строкам.
  2. Отсортировать по ключам в алфавитном порядке (рекурсивно).
  3. Перевести в JSON-строку.
  4. Экранировать символ "/" → "\\/"
  5. HMAC-SHA256 с секретным ключом.
"""

import hashlib
import hmac
import json
import logging
import re
import urllib.parse
from collections.abc import Iterable
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_BRACKET_KEY_RE = re.compile(r"^([^\[\]]+)((?:\[[^\[\]]*\])+)$")
_BRACKET_SEGMENT_RE = re.compile(r"\[([^\[\]]*)\]")
# PHP's default max_input_nesting_level: deeper form keys never reach $_POST.
_MAX_INPUT_NESTING_LEVEL = 64

# Up to 4096 characters; must not carry secrets, Prodamus emails it as is.
PAID_CONTENT_TEMPLATE = (
    "Доступ к курсу откроется в личном кабинете {site}/dashboard в течение пары минут "
    "после оплаты. Если вы оплачивали без регистрации, ссылка для входа придёт на email, "
    "указанный при оплате."
)

# 54-FZ receipt line for the course. The seller is on УСН with the VAT exemption;
# access opens right after payment, so the receipt is «полный расчёт» for «услуга».
# Without these fields Prodamus falls back to the shop defaults.
RECEIPT_TAX_TYPE_NO_VAT = "0"
RECEIPT_PAYMENT_METHOD_FULL_PAYMENT = "4"
RECEIPT_PAYMENT_OBJECT_SERVICE = "4"
# Fiscal tag 1030 (item name) holds at most 128 characters.
RECEIPT_NAME_MAX_LENGTH = 128


def _days_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "день"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "дня"
    return "дней"


def receipt_item_name(course_title: str, access_days: int) -> str:
    """Receipt item name: «Онлайн-курс «Nail Design PRO», доступ 30 дней»."""
    prefix = "Онлайн-курс «"
    suffix = f"», доступ {access_days} {_days_word(access_days)}"
    room = RECEIPT_NAME_MAX_LENGTH - len(prefix) - len(suffix)
    title = course_title.strip()
    if len(title) > room:
        title = title[: room - 1].rstrip() + "…"
    return f"{prefix}{title}{suffix}"


def _bracket_fields(prefix: str, value: dict[str, Any]) -> dict[str, Any]:
    """Flatten a nested dict into the products[0][tax][tax_type]-style GET keys."""
    fields: dict[str, Any] = {}
    for key, item in value.items():
        name = f"{prefix}[{key}]"
        if isinstance(item, dict):
            fields.update(_bracket_fields(name, item))
        else:
            fields[name] = item
    return fields


def _to_str(value: Any) -> Any:
    """Рекурсивно приводит все значения к строкам и сортирует ключи."""
    if isinstance(value, dict):
        return {k: _to_str(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_to_str(item) for item in value]
    # Match PHP strval(), which Prodamus applies before signing.
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else ""
    if isinstance(value, float) and value.is_integer():
        # PHP strval(5900.0) is "5900"; other floats keep the shortest repr.
        return str(int(value))
    return str(value)


def _sequential_levels_to_lists(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    converted = {key: _sequential_levels_to_lists(item) for key, item in value.items()}
    indexes = [str(index) for index in range(len(converted))]
    if converted and set(converted) == set(indexes):
        return [converted[index] for index in indexes]
    return converted


def nest_form_fields(items: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    """Rebuild the nested data PHP's ``$_POST`` derives from bracketed form keys.

    Prodamus signs webhooks over that nested structure, so
    ``products[0][name]=x`` must become ``{"products": [{"name": "x"}]}``.
    A bracketed level whose keys are exactly ``0..n-1`` becomes a list, any
    other level stays a dict with string keys. Repeated keys keep the last
    value, as in PHP. Non-string values (uploaded files) and keys nested
    deeper than PHP's ``max_input_nesting_level`` are ignored.
    """
    root: dict[str, Any] = {}
    for key, value in items:
        if not isinstance(value, str):
            continue
        match = _BRACKET_KEY_RE.match(key)
        if match is None:
            root[key] = value
            continue
        segments = _BRACKET_SEGMENT_RE.findall(match.group(2))
        if len(segments) > _MAX_INPUT_NESTING_LEVEL:
            continue
        path = [match.group(1), *segments]
        node = root
        for depth, segment in enumerate(path):
            if depth and segment == "":
                # PHP appends for an empty "[]" segment.
                segment = str(len(node))
            if depth == len(path) - 1:
                node[segment] = value
                break
            child = node.get(segment)
            if not isinstance(child, dict):
                child = node[segment] = {}
            node = child
    return {key: _sequential_levels_to_lists(value) for key, value in root.items()}


def _make_signature(data: dict, secret_key: str) -> str:
    """Формирует HMAC-SHA256 подпись по алгоритму Prodamus."""
    sorted_data = _to_str(data)
    json_str = json.dumps(sorted_data, ensure_ascii=False, separators=(",", ":"))
    # Шаг 4: экранируем /
    json_str = json_str.replace("/", "\\/")
    return hmac.new(
        secret_key.encode("utf-8"),
        json_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class ProdamusService:

    # Информация о тарифах привязана к конкретным товарам на стороне Prodamus.
    # Здесь хранятся только названия и цены для формирования ссылки «на лету».
    TARIFF_CONFIG = {
        "self": {
            "name": "Курс по дизайну ногтей — Самостоятельный",
        },
        "support": {
            "name": "Курс по дизайну ногтей — С поддержкой",
        },
    }

    @staticmethod
    def generate_payment_link(
        course_name: str,
        price: float,
        tariff: str,
        order_id: str | None = None,
        customer_email: str | None = None,
        customer_phone: str | None = None,
        success_url: str | None = None,
    ) -> str:
        """
        Генерирует прямую ссылку на оплату (GET-параметры + подпись).

        Покупатель может быть гостём: email/телефон опциональны (Prodamus попросит при оплате).
        """
        base_url = settings.PRODAMUS_URL.rstrip("/") + "/"
        secret = settings.PRODAMUS_SECRET_KEY
        frontend_url = settings.FRONTEND_URL.rstrip("/")

        # Backend API URL for webhook notifications
        backend_url = settings.BACKEND_URL.rstrip("/") if settings.BACKEND_URL else "http://localhost:8000"

        product: dict[str, Any] = {
            "name": course_name,
            "price": str(price),
            "quantity": "1",
            "type": "course",
            "tax": {"tax_type": RECEIPT_TAX_TYPE_NO_VAT},
            "paymentMethod": RECEIPT_PAYMENT_METHOD_FULL_PAYMENT,
            "paymentObject": RECEIPT_PAYMENT_OBJECT_SERVICE,
        }

        params: dict[str, Any] = {
            "do": "pay",
            **_bracket_fields("products[0]", product),
            "urlSuccess": success_url or f"{frontend_url}/payment-success",
            "urlReturn": f"{frontend_url}/#pricing",
            # Prodamus posts to the URL set in the cabinet; this one is ignored
            # (observed 2026-10-31) but kept for forms that honour it.
            "urlNotification": f"{backend_url}/api/payments/webhook",
            # callbackType=json — вебхуки будут приходить в JSON
            "callbackType": "json",
            # «Доступы к материалам»: Prodamus' cash register issues the 54-FZ
            # full-settlement receipt only when the link names what the buyer
            # receives. Prodamus also shows and emails this text after payment.
            "paid_content": PAID_CONTENT_TEMPLATE.format(site=frontend_url),
        }

        if order_id:
            params["order_id"] = order_id
        if customer_email:
            params["customer_email"] = customer_email.strip().lower()
        if customer_phone:
            params["customer_phone"] = str(customer_phone).strip()

        # demo_mode=1 for test payments: always outside production, and on demand
        # in production via PRODAMUS_DEMO_MODE (for test payments on a live deploy).
        if settings.PRODAMUS_DEMO_MODE or settings.ENVIRONMENT.lower() != "production":
            params["demo_mode"] = "1"

        # The signature MUST be computed over the NESTED structure that Prodamus
        # reconstructs from the flat products[0][...] GET params, i.e. with a real
        # "products": [ {...} ] list — not over the flat dict. Signing the flat dict
        # produces a signature Prodamus rejects ("Ошибка подписи передаваемых
        # данных"), so no payment link ever validated. See audit 2026-07-06 (LIVE-1).
        sign_data = {k: v for k, v in params.items() if not k.startswith("products[")}
        sign_data["products"] = [product]
        params["signature"] = _make_signature(sign_data, secret)

        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        link = f"{base_url}?{query}"
        logger.debug("Prodamus link generated (order_id present: %s)", bool(order_id))
        return link

    @staticmethod
    def demo_payments_allowed() -> bool:
        """Test payments are honoured outside production or when forced on."""
        return settings.PRODAMUS_DEMO_MODE or settings.ENVIRONMENT.lower() != "production"

    @staticmethod
    def verify_signature(payload: dict, signature: str) -> bool:
        """
        Проверяет HMAC-подпись вебхука от Prodamus.

        payload  — тело запроса (dict), signature — значение заголовка 'Sign'.
        """
        secret = settings.PRODAMUS_SECRET_KEY
        if not secret:
            logger.error("PRODAMUS_SECRET_KEY is not configured")
            return False

        # PHP Hmac::verify compares case-insensitively; our digest is lowercase hex.
        signature = signature.strip().lower()
        # Compare bytes: compare_digest() raises on non-ASCII str (headers are latin-1).
        received = signature.encode("utf-8")

        # First, try standard signature
        try:
            expected = _make_signature(payload, secret)
        except RecursionError:
            # Prodamus never signs payloads nested this deeply.
            logger.warning("Prodamus webhook payload is nested too deeply to verify")
            return False
        if hmac.compare_digest(expected.encode("ascii"), received):
            return True

        # Demo-mode signature uses the secret with a "demo" suffix. Accept it ONLY
        # when demo mode is explicitly enabled (or outside production), otherwise a
        # leaked secret could forge a demo-signed webhook against a live shop and
        # grant free access. See audit 2026-07-06 (P0-2 / INTEG-01).
        demo_allowed = ProdamusService.demo_payments_allowed()
        if demo_allowed:
            expected_demo = _make_signature(payload, secret + "demo")
            if hmac.compare_digest(expected_demo.encode("ascii"), received):
                logger.info("Matched demo signature for Prodamus webhook")
                return True

        logger.warning(
            "Prodamus signature mismatch. Expected normal=%s, Got=%s (demo_allowed=%s)",
            expected[:16] + "...",
            signature[:16] + "...",
            demo_allowed,
        )
        return False
