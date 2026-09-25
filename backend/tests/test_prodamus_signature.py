"""Regression tests for the Prodamus payment-link signature.

Audit 2026-07-06 (LIVE-1): Prodamus validates the request signature over the
NESTED structure it reconstructs from the flat `products[0][...]` GET params
(i.e. `{"products": [ {...} ]}`), not over the flat dict. Signing the flat dict
produced a signature Prodamus always rejected ("Ошибка подписи передаваемых
данных"), so no payment link ever validated. These tests lock in the fix.
"""

import io
import urllib.parse

from starlette.datastructures import UploadFile

from app.core.config import settings
from app.services.prodamus_service import (
    ProdamusService,
    _make_signature,
    _to_str,
    nest_form_fields,
)

_WEBHOOK_PAYLOAD = {
    "order_id": "course|11111111-1111-1111-1111-111111111111|self|deadbeef",
    "sum": "5900",
    "currency": "rub",
    "payment_status": "success",
}


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


def test_demo_signature_rejected_in_production(monkeypatch):
    """P0-2: a demo-suffixed signature must NOT be accepted in production real mode."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "PRODAMUS_DEMO_MODE", False)

    demo_sig = _make_signature(_WEBHOOK_PAYLOAD, settings.PRODAMUS_SECRET_KEY + "demo")
    assert ProdamusService.verify_signature(_WEBHOOK_PAYLOAD, demo_sig) is False

    # A correctly (normally) signed webhook still verifies.
    normal_sig = _make_signature(_WEBHOOK_PAYLOAD, settings.PRODAMUS_SECRET_KEY)
    assert ProdamusService.verify_signature(_WEBHOOK_PAYLOAD, normal_sig) is True


def test_demo_signature_accepted_when_demo_mode_enabled(monkeypatch):
    """Demo signature is accepted only when demo mode is explicitly on."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "PRODAMUS_DEMO_MODE", True)

    demo_sig = _make_signature(_WEBHOOK_PAYLOAD, settings.PRODAMUS_SECRET_KEY + "demo")
    assert ProdamusService.verify_signature(_WEBHOOK_PAYLOAD, demo_sig) is True


def test_to_str_matches_php_strval_for_none_and_bool():
    assert _to_str({"b": True, "a": None, "c": False, "d": [None, True]}) == {
        "a": "",
        "b": "1",
        "c": "",
        "d": ["", "1"],
    }
    # Numbers keep Python str(); outgoing link signatures depend on it.
    assert _to_str(5900.0) == "5900.0"
    assert _to_str(1) == "1"


def test_nest_form_fields_rebuilds_php_post_structure():
    nested = nest_form_fields(
        [
            ("order_id", "300155"),
            ("products[1][name]", "Second"),
            ("products[0][name]", "First"),
            ("products[0][price]", "100.00"),
            ("meta[a][b][0]", "x"),
            ("sparse[1]", "one"),
            ("padded[01]", "p"),
            ("named[key]", "v"),
            ("tags[]", "t0"),
            ("tags[]", "t1"),
            ("order_id", "300156"),
        ]
    )

    assert nested == {
        "order_id": "300156",
        "products": [{"name": "First", "price": "100.00"}, {"name": "Second"}],
        "meta": {"a": {"b": ["x"]}},
        "sparse": {"1": "one"},
        "padded": {"01": "p"},
        "named": {"key": "v"},
        "tags": ["t0", "t1"],
    }


def test_nest_form_fields_orders_long_lists_numerically_and_skips_files():
    upload = UploadFile(file=io.BytesIO(b"file"), filename="receipt.txt")
    items = [(f"items[{index}]", str(index)) for index in reversed(range(12))]

    nested = nest_form_fields([*items, ("attachment", upload), ("receipt[0]", upload)])

    assert nested == {"items": [str(index) for index in range(12)]}


def test_form_webhook_signature_verifies_over_nested_products():
    """Prodamus signs the nested products list, not the flat bracket keys."""
    form_items = [
        ("order_id", "300155"),
        ("order_num", "order|11111111-1111-1111-1111-111111111111"),
        ("sum", "5900.00"),
        ("payment_status", "success"),
        ("products[0][name]", 'Курс "Nail Design" — Самостоятельный'),
        ("products[0][price]", "5900.00"),
        ("products[0][quantity]", "1"),
        ("products[0][sum]", "5900.00"),
    ]
    signature = _make_signature(
        {
            "order_id": "300155",
            "order_num": "order|11111111-1111-1111-1111-111111111111",
            "sum": "5900.00",
            "payment_status": "success",
            "products": [
                {
                    "name": 'Курс "Nail Design" — Самостоятельный',
                    "price": "5900.00",
                    "quantity": "1",
                    "sum": "5900.00",
                }
            ],
        },
        settings.PRODAMUS_SECRET_KEY,
    )

    assert ProdamusService.verify_signature(nest_form_fields(form_items), signature) is True
    assert ProdamusService.verify_signature(dict(form_items), signature) is False
