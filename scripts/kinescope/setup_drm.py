"""
Setup-скрипт для DRM авторизационного бэкенда Kinescope.

Что делает:
  1. Генерирует RSA-2048 ключевую пару.
  2. Сохраняет приватный ключ в PEM-файл (по умолчанию `backend/secrets/kinescope_drm_private.pem`).
  3. Извлекает публичный ключ как JWK и заливает его в Kinescope (`POST /v1/jwk`).
  4. Регистрирует URL нашего webhook в настройках DRM проекта (`PUT /v1/drm/auth/{project_id}`).

Использование (Windows / PowerShell):

    python scripts/kinescope/setup_drm.py --project-id e82e1d55-... \
        --webhook-url https://api.lucysmirnova.ru/api/integrations/kinescope/drm/authorize \
        --basic-user kinescope-drm \
        --basic-pass <случайная_строка>

После запуска:
  - сохраните приватный ключ из PEM-файла в Railway secret KINESCOPE_JWT_PRIVATE_KEY_PEM
    (с экранированными \n) или положите файл по пути из KINESCOPE_JWT_PRIVATE_KEY_PATH;
  - в .env добавьте KINESCOPE_JWK_KID, KINESCOPE_DRM_BASIC_USER, KINESCOPE_DRM_BASIC_PASS
    (значения скрипт распечатает в финальном summary).

Безопасность: PEM из файла НЕ КОММИТИТЬ. Папка backend/secrets/ должна быть в .gitignore.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import secrets
import sys
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


_BASE_URL = "https://api.kinescope.io"


def _b64url_uint(value: int) -> str:
    """Кодирует целое число (RSA-параметр) в base64url без padding (RFC 7518)."""
    raw = value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _generate_rsa_pair(bits: int = 2048) -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


def _private_pem(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _public_jwk(key: rsa.RSAPrivateKey, kid: str) -> dict:
    numbers = key.public_key().public_numbers()
    return {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(numbers.n),
        "e": _b64url_uint(numbers.e),
    }


def _api_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _post_jwk(api_key: str, jwk: dict, expires_at_iso: str) -> dict:
    body = dict(jwk)
    body["expires_at"] = expires_at_iso
    with httpx.Client(timeout=20.0) as c:
        r = c.post(f"{_BASE_URL}/v1/jwk", headers=_api_headers(api_key), json=body)
        r.raise_for_status()
        return r.json()


def _put_drm_auth(
    api_key: str,
    project_id: str,
    webhook_url: str,
    basic_user: str,
    basic_pass: str,
) -> dict:
    body = {
        "url": webhook_url,
        "username": basic_user,
        "password": basic_pass,
        "strict": False,
    }
    with httpx.Client(timeout=20.0) as c:
        r = c.put(
            f"{_BASE_URL}/v1/drm/auth/{project_id}",
            headers=_api_headers(api_key),
            json=body,
        )
        if not r.is_success:
            raise httpx.HTTPStatusError(
                f"PUT /v1/drm/auth/{project_id} failed: HTTP {r.status_code} {r.text}",
                request=r.request,
                response=r,
            )
        try:
            return r.json()
        except json.JSONDecodeError:
            return {"raw": r.text}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-id",
        default=os.getenv("KINESCOPE_PROJECT_ID", ""),
        help="UUID проекта Kinescope. Берётся из env если не передан.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("KINESCOPE_API_KEY", ""),
        help="Bearer-токен Kinescope API. Берётся из env если не передан.",
    )
    parser.add_argument(
        "--webhook-url",
        required=True,
        help="Публичный HTTPS URL до /api/integrations/kinescope/drm/authorize",
    )
    parser.add_argument(
        "--key-path",
        default="backend/secrets/kinescope_drm_private.pem",
        help="Куда сохранить приватный PEM (рекомендуется вне git).",
    )
    parser.add_argument(
        "--kid",
        default=None,
        help="Key ID (kid). По умолчанию: kinescope-drm-YYYYMMDD-<rand>.",
    )
    parser.add_argument(
        "--basic-user",
        default=os.getenv("KINESCOPE_DRM_BASIC_USER", "kinescope-drm"),
    )
    parser.add_argument(
        "--basic-pass",
        default=os.getenv("KINESCOPE_DRM_BASIC_PASS") or secrets.token_urlsafe(32),
    )
    parser.add_argument(
        "--key-expires-days",
        type=int,
        default=730,
        help="Срок годности публичного JWK (дней).",
    )
    parser.add_argument(
        "--skip-drm-auth",
        action="store_true",
        help="Только сгенерировать ключ + JWK; не трогать /v1/drm/auth.",
    )
    args = parser.parse_args()

    if not args.project_id:
        print("ERROR: --project-id required (or set KINESCOPE_PROJECT_ID)", file=sys.stderr)
        return 2
    if not args.api_key:
        print("ERROR: --api-key required (or set KINESCOPE_API_KEY)", file=sys.stderr)
        return 2

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    kid = args.kid or f"kinescope-drm-{today}-{secrets.token_hex(3)}"

    print(f"[1/4] Generating RSA-2048 key pair, kid={kid}")
    key = _generate_rsa_pair(2048)

    pem_bytes = _private_pem(key)
    pem_path = Path(args.key_path).resolve()
    pem_path.parent.mkdir(parents=True, exist_ok=True)
    pem_path.write_bytes(pem_bytes)
    try:
        os.chmod(pem_path, 0o600)
    except OSError:
        pass
    print(f"[2/4] Private key written to {pem_path} ({len(pem_bytes)} bytes)")

    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=args.key_expires_days)
    expires_at_iso = expires_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    jwk = _public_jwk(key, kid)
    print(f"[3/4] Uploading public JWK to Kinescope (expires_at={expires_at_iso})")
    try:
        jwk_resp = _post_jwk(args.api_key, jwk, expires_at_iso)
    except httpx.HTTPStatusError as e:
        print(f"  -> ERROR: {e.response.status_code} {e.response.text}", file=sys.stderr)
        return 1
    print(f"  -> OK: {json.dumps(jwk_resp, ensure_ascii=False)}")

    if args.skip_drm_auth:
        drm_resp: dict = {"skipped": True}
    else:
        print(f"[4/4] Registering DRM auth backend on project {args.project_id}")
        try:
            drm_resp = _put_drm_auth(
                args.api_key,
                args.project_id,
                args.webhook_url,
                args.basic_user,
                args.basic_pass,
            )
        except httpx.HTTPStatusError as e:
            print(f"  -> ERROR: {e}", file=sys.stderr)
            return 1
        print(f"  -> OK: {json.dumps(drm_resp, ensure_ascii=False)}")

    print("\n=== ADD TO YOUR .env (and Railway secrets) ===")
    print(f"KINESCOPE_JWK_KID={kid}")
    print(f"KINESCOPE_JWT_PRIVATE_KEY_PATH={pem_path}")
    print("# OR (recommended for Railway): inline PEM with escaped \\n")
    inline = pem_bytes.decode("utf-8").replace("\n", "\\n")
    print(f"KINESCOPE_JWT_PRIVATE_KEY_PEM={inline}")
    print(f"KINESCOPE_DRM_BASIC_USER={args.basic_user}")
    print(f"KINESCOPE_DRM_BASIC_PASS={args.basic_pass}")
    print("KINESCOPE_DRM_TOKEN_TTL_SECONDS=300")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
