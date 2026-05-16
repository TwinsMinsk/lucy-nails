"""
Prodamus actions CLI — standalone wrapper around the Prodamus payment-page
parameters and the REST API for subscriptions (клубная система).

Self-contained: only stdlib + requests. The signature algorithm mirrors the
backend service `app.services.prodamus_service` so payloads stay compatible.

Configuration (env or CLI flags; CLI wins):
  PRODAMUS_URL              base payment-page URL, e.g. https://edu2.payform.ru/
  PRODAMUS_SECRET_KEY       merchant secret key (sign + verify)
  PRODAMUS_DEMO_MODE        if "1"/"true", append demo_mode=1 and sign with
                            secret_key + "demo" suffix on verify-sign fallback

Subcommands:
  link               Build a signed checkout URL.
  verify-sign        Verify the Sign header of a webhook body.
  set-activity       POST setActivity (активация/деактивация подписки).
  set-payment-date   POST setSubscriptionPaymentDate (сдвинуть дату списания).
  set-discount       POST setSubscriptionDiscount (скидка на следующие списания).

Usage examples:
  python scripts/prodamus/actions.py link --course "Test" --price 1 --tariff self --demo
  python scripts/prodamus/actions.py verify-sign --sign <hex> --body @body.json
  python scripts/prodamus/actions.py set-activity --subscription 123 --profile 456 --active 0
  python scripts/prodamus/actions.py set-payment-date --subscription 123 --profile 456 --date 2026-08-01
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import requests


# === signature (mirrors backend/app/services/prodamus_service.py) ============

def _to_str(value: Any) -> Any:
    """Recursively stringify values and sort dict keys."""
    if isinstance(value, dict):
        return {k: _to_str(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_to_str(item) for item in value]
    return str(value)


def make_signature(data: dict, secret_key: str) -> str:
    """HMAC-SHA256 of sorted-stringified-JSON with `/` escaped — Prodamus spec."""
    sorted_data = _to_str(data)
    json_str = json.dumps(sorted_data, ensure_ascii=False, separators=(",", ":"))
    json_str = json_str.replace("/", "\\/")
    return hmac.new(
        secret_key.encode("utf-8"),
        json_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# === env / .env loader =======================================================

def _load_dotenv_if_missing(keys: list[str]) -> None:
    if all(os.environ.get(k) for k in keys):
        return
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k in keys and not os.environ.get(k):
            os.environ[k] = v


def _require(env_key: str, cli_value: str | None) -> str:
    if cli_value:
        return cli_value
    val = os.environ.get(env_key)
    if not val:
        print(f"ERROR: --{env_key.lower().replace('_', '-')} not given and {env_key} not in env",
              file=sys.stderr)
        sys.exit(2)
    return val


def _read_body_arg(value: str) -> dict:
    """Accepts JSON literal or @path/to/file.json"""
    if value.startswith("@"):
        path = Path(value[1:])
        if not path.is_file():
            print(f"ERROR: body file not found: {path}", file=sys.stderr)
            sys.exit(2)
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


# === subcommands =============================================================

def cmd_link(args: argparse.Namespace) -> int:
    _load_dotenv_if_missing(["PRODAMUS_URL", "PRODAMUS_SECRET_KEY"])
    base = _require("PRODAMUS_URL", args.url).rstrip("/") + "/"
    secret = _require("PRODAMUS_SECRET_KEY", args.secret)

    params: dict[str, Any] = {
        "do": "pay",
        "products[0][name]": args.course,
        "products[0][price]": f"{args.price}",
        "products[0][quantity]": "1",
        "products[0][type]": "course",
        "callbackType": "json",
    }
    if args.success_url:
        params["urlSuccess"] = args.success_url
    if args.return_url:
        params["urlReturn"] = args.return_url
    if args.notification_url:
        params["urlNotification"] = args.notification_url
    if args.order_id:
        params["order_id"] = args.order_id
    if args.email:
        params["customer_email"] = args.email.strip().lower()
    if args.phone:
        params["customer_phone"] = str(args.phone).strip()
    if args.demo or os.environ.get("PRODAMUS_DEMO_MODE", "").lower() in ("1", "true", "yes"):
        params["demo_mode"] = "1"

    params["signature"] = make_signature(params, secret)
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    print(f"{base}?{query}")
    return 0


def cmd_verify_sign(args: argparse.Namespace) -> int:
    _load_dotenv_if_missing(["PRODAMUS_SECRET_KEY"])
    secret = _require("PRODAMUS_SECRET_KEY", args.secret)
    body = _read_body_arg(args.body)

    expected = make_signature(body, secret)
    if hmac.compare_digest(expected, args.sign):
        print("OK (production secret)")
        return 0
    expected_demo = make_signature(body, secret + "demo")
    if hmac.compare_digest(expected_demo, args.sign):
        print("OK (demo secret = secret_key + 'demo')")
        return 0
    print("MISMATCH", file=sys.stderr)
    print(f"  expected_prod = {expected}", file=sys.stderr)
    print(f"  expected_demo = {expected_demo}", file=sys.stderr)
    print(f"  got           = {args.sign}", file=sys.stderr)
    return 1


def _post_rest(base_url: str, endpoint: str, payload: dict) -> dict:
    """POST to /rest/<endpoint>/ on the Prodamus payment domain."""
    url = base_url.rstrip("/") + f"/rest/{endpoint}/"
    resp = requests.post(url, data=payload, timeout=20)
    try:
        return {"status_code": resp.status_code, "body": resp.json()}
    except ValueError:
        return {"status_code": resp.status_code, "text": resp.text}


def _build_auth_params(args: argparse.Namespace) -> dict:
    """Build the auth_type-dependent identification block."""
    if args.profile:
        return {"auth_type": "profile", "profile": str(args.profile)}
    if args.vk_user_id:
        return {"auth_type": "vk_user_id", "vk_user_id": str(args.vk_user_id)}
    if args.phone:
        return {"auth_type": "customer_phone", "customer_phone": str(args.phone)}
    print("ERROR: pass one of --profile / --vk-user-id / --phone", file=sys.stderr)
    sys.exit(2)


def cmd_set_activity(args: argparse.Namespace) -> int:
    _load_dotenv_if_missing(["PRODAMUS_URL", "PRODAMUS_SECRET_KEY"])
    base = _require("PRODAMUS_URL", args.url)
    secret = _require("PRODAMUS_SECRET_KEY", args.secret)

    payload = {"subscription": str(args.subscription), "active": "1" if args.active else "0"}
    payload.update(_build_auth_params(args))
    payload["signature"] = make_signature(payload, secret)
    result = _post_rest(base, "setActivity", payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if 200 <= result["status_code"] < 300 else 1


def cmd_set_payment_date(args: argparse.Namespace) -> int:
    _load_dotenv_if_missing(["PRODAMUS_URL", "PRODAMUS_SECRET_KEY"])
    base = _require("PRODAMUS_URL", args.url)
    secret = _require("PRODAMUS_SECRET_KEY", args.secret)

    payload = {"subscription": str(args.subscription), "date": args.date}
    payload.update(_build_auth_params(args))
    payload["signature"] = make_signature(payload, secret)
    result = _post_rest(base, "setSubscriptionPaymentDate", payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if 200 <= result["status_code"] < 300 else 1


def cmd_set_discount(args: argparse.Namespace) -> int:
    _load_dotenv_if_missing(["PRODAMUS_URL", "PRODAMUS_SECRET_KEY"])
    base = _require("PRODAMUS_URL", args.url)
    secret = _require("PRODAMUS_SECRET_KEY", args.secret)

    payload = {
        "subscription": str(args.subscription),
        "discount": str(args.discount),
        "discount_type": args.discount_type,
        "count": str(args.count),
    }
    payload.update(_build_auth_params(args))
    payload["signature"] = make_signature(payload, secret)
    result = _post_rest(base, "setSubscriptionDiscount", payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if 200 <= result["status_code"] < 300 else 1


# === argparse wiring =========================================================

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Prodamus actions CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    common_creds = argparse.ArgumentParser(add_help=False)
    common_creds.add_argument("--url", help="PRODAMUS_URL override (e.g. https://edu2.payform.ru)")
    common_creds.add_argument("--secret", help="PRODAMUS_SECRET_KEY override")

    common_auth = argparse.ArgumentParser(add_help=False)
    common_auth.add_argument("--profile", help="Prodamus profile id (auth_type=profile)")
    common_auth.add_argument("--vk-user-id", dest="vk_user_id", help="VK user id (auth_type=vk_user_id)")
    common_auth.add_argument("--phone", help="customer phone +79XXXXXXXXX (auth_type=customer_phone)")

    pl = sub.add_parser("link", parents=[common_creds], help="Build signed checkout URL")
    pl.add_argument("--course", required=True, help="products[0][name]")
    pl.add_argument("--price", required=True, type=float, help="products[0][price]")
    pl.add_argument("--tariff", help="info-only (self|support); not sent to Prodamus")
    pl.add_argument("--email", help="customer_email (optional)")
    pl.add_argument("--phone", help="customer_phone (optional)")
    pl.add_argument("--order-id", dest="order_id", help="order_id (optional)")
    pl.add_argument("--success-url", dest="success_url", help="urlSuccess")
    pl.add_argument("--return-url", dest="return_url", help="urlReturn")
    pl.add_argument("--notification-url", dest="notification_url", help="urlNotification (webhook)")
    pl.add_argument("--demo", action="store_true", help="Force demo_mode=1")
    pl.set_defaults(func=cmd_link)

    pv = sub.add_parser("verify-sign", parents=[common_creds], help="Verify a webhook signature")
    pv.add_argument("--sign", required=True, help="Sign header value (hex)")
    pv.add_argument("--body", required=True, help="JSON body literal or @file.json")
    pv.set_defaults(func=cmd_verify_sign)

    pa = sub.add_parser("set-activity", parents=[common_creds, common_auth],
                        help="setActivity (activate/deactivate subscription)")
    pa.add_argument("--subscription", required=True, help="subscription id")
    pa.add_argument("--active", type=int, choices=[0, 1], required=True, help="1 to activate, 0 to deactivate")
    pa.set_defaults(func=cmd_set_activity)

    pd = sub.add_parser("set-payment-date", parents=[common_creds, common_auth],
                        help="setSubscriptionPaymentDate")
    pd.add_argument("--subscription", required=True, help="subscription id")
    pd.add_argument("--date", required=True, help="YYYY-MM-DD or YYYY-MM-DD HH:MM (future only)")
    pd.set_defaults(func=cmd_set_payment_date)

    ps = sub.add_parser("set-discount", parents=[common_creds, common_auth],
                        help="setSubscriptionDiscount")
    ps.add_argument("--subscription", required=True, help="subscription id")
    ps.add_argument("--discount", required=True, help="discount value")
    ps.add_argument("--discount-type", dest="discount_type", choices=["percent", "amount"],
                    default="percent")
    ps.add_argument("--count", type=int, default=1, help="how many upcoming charges to apply to")
    ps.set_defaults(func=cmd_set_discount)

    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
