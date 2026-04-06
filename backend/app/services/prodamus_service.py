"""
Prodamus Service: генерация платёжной ссылки и проверка HMAC-подписи webhook.

Алгоритм подписи (из документации Prodamus):
  1. Все значения привести к строкам.
  2. Отсортировать по ключам в алфавитном порядке (рекурсивно).
  3. Перевести в JSON-строку.
  4. Экранировать символ "/" → "\/"
  5. HMAC-SHA256 с секретным ключом.
"""

import hashlib
import hmac
import json
import logging
import urllib.parse
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _to_str(value: Any) -> Any:
    """Рекурсивно приводит все значения к строкам и сортирует ключи."""
    if isinstance(value, dict):
        return {k: _to_str(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_to_str(item) for item in value]
    return str(value)


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
    ) -> str:
        """
        Генерирует прямую ссылку на оплату (GET-параметры + подпись).

        Покупатель — гость, email пока неизвестен, Prodamus попросит его сам.
        """
        base_url = settings.PRODAMUS_URL.rstrip("/") + "/"
        secret   = settings.PRODAMUS_SECRET_KEY

        params: dict[str, Any] = {
            "do": "pay",
            "products[0][name]":     course_name,
            "products[0][price]":    str(price),
            "products[0][quantity]": "1",
            "products[0][type]":     "course",
            "urlSuccess":  f"{settings.FRONTEND_URL}/dashboard",
            "urlReturn":   f"{settings.FRONTEND_URL}/",
            # callbackType=json — вебхуки будут приходить в JSON
            "callbackType": "json",
        }

        if order_id:
            params["order_id"] = order_id

        # Подпись считается по «плоскому» dict (без вложенности product[0][name])
        # Prodamus принимает как flat params в URL, так и подпись по исходному dict.
        # Для простоты подписываем flat dict.
        flat_for_sign = {k: v for k, v in params.items()}
        params["signature"] = _make_signature(flat_for_sign, secret)

        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        link  = f"{base_url}?{query}"
        logger.debug("Generated Prodamus link: %s", link)
        return link

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

        expected = _make_signature(payload, secret)
        result   = hmac.compare_digest(expected, signature)
        if not result:
            logger.warning(
                "Prodamus signature mismatch. Expected=%s, Got=%s",
                expected[:16] + "...",
                signature[:16] + "...",
            )
        return result
