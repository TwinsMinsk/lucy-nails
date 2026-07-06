"""Regression tests for the Prodamus payment-link signature.

Audit 2026-07-06 (LIVE-1): Prodamus validates the request signature over the
NESTED structure it reconstructs from the flat `products[0][...]` GET params
(i.e. `{"products": [ {...} ]}`), not over the flat dict. Signing the flat dict
produced a signature Prodamus always rejected ("Ошибка подписи передаваемых
данных"), so no payment link ever validated. These tests lock in the fix.
"""

import urllib.parse

from app.core.config import settings
from app.services.prodamus_service import ProdamusService, _make_signature


def _reconstruct_nested(params: dict) -> dict:
    """Rebuild the nested products structure Prodamus derives from products[0][...]."""
    product: dict = {}
    scalars: dict = {}
    for key, value in params.items():
        if key.startswith("products[0]["):
            product[key[len("products[0][") : -1]] = value
        else:
            scalars[key] = value
    return {**scalars, "products": [product]}


def test_payment_link_signature_is_over_nested_products():
    url = ProdamusService.generate_payment_link(
        course_name="Nail Design PRO: 11 техник",
        price=5900,
        tariff="self",
        order_id="course|11111111-1111-1111-1111-111111111111|self|deadbeef",
        customer_email="Buyer@Example.com",
    )

    query = urllib.parse.urlparse(url).query
    params = dict(urllib.parse.parse_qsl(query, keep_blank_values=True))
    signature = params.pop("signature")

    # The URL still carries the flat products[0][...] params that Prodamus parses.
    assert "products[0][name]" in params
    assert "products[0][price]" in params

    # The signature must match the nested canonical form Prodamus validates against.
    nested = _reconstruct_nested(params)
    assert signature == _make_signature(nested, settings.PRODAMUS_SECRET_KEY)


def test_payment_link_signature_is_not_the_old_flat_form():
    """Guard against regressing back to signing the flat dict."""
    url = ProdamusService.generate_payment_link(
        course_name="Nail Design PRO",
        price=11900,
        tariff="support",
        customer_email="guest@example.com",
    )

    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query, keep_blank_values=True))
    signature = params.pop("signature")

    flat_signature = _make_signature(params, settings.PRODAMUS_SECRET_KEY)
    assert signature != flat_signature
