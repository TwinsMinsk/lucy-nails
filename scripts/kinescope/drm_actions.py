"""
Kinescope DRM actions CLI — debug & verification helpers around the
Authorization Backend pattern.

Pairs with:
  - scripts/kinescope/setup_drm.py            (one-shot keypair + JWK upload + DRM auth)
  - scripts/kinescope/put_drm_auth_from_env.py (re-register webhook from env)
  - backend/app/services/kinescope_jwt_service.py (runtime token signing in production)

This CLI is standalone (only python-jose + cryptography + requests).
It does NOT mutate state on Kinescope; the only writes happen via setup_drm.py.

Subcommands:
  sign-token        Sign a test drmauthtoken (RS256) and optionally build the embed URL.
  decode-token      Decode and verify a JWT against the configured public key.
  list-jwks         GET /v1/jwk on Kinescope to see which kids are active.
  get-drm-auth      GET /v1/drm/auth/<project_id> to inspect the webhook config.

Env (auto-loaded from repo .env if missing):
  KINESCOPE_API_KEY                  Workspace API token (Bearer)
  KINESCOPE_PROJECT_ID               UUID of the project owning the videos
  KINESCOPE_JWT_PRIVATE_KEY_PATH     Path to RSA PEM (PKCS8)
  KINESCOPE_JWT_PRIVATE_KEY_PEM      Inline PEM (\\n-escaped allowed)
  KINESCOPE_JWK_KID                  kid header value to put on signed JWTs
  KINESCOPE_DRM_TOKEN_TTL_SECONDS    Default token TTL (seconds, default 300)
  BACKEND_URL                        Used as `iss` claim; defaults to "lucy-nails"

Usage:
  python scripts/kinescope/drm_actions.py sign-token --user-id u-1 --lesson-id lesson-42 \\
      --video-id pcFNnQGsD59CMKte2SQQaz --print-embed
  python scripts/kinescope/drm_actions.py decode-token --token "eyJhbG..." --verify
  python scripts/kinescope/drm_actions.py list-jwks
  python scripts/kinescope/drm_actions.py get-drm-auth
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from cryptography.hazmat.primitives import serialization
from jose import jwt
from jose.constants import ALGORITHMS


_JWT_AUDIENCE = "lucy-nails-drm"
_KINESCOPE_API = "https://api.kinescope.io"


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


def _load_private_pem(cli_pem_path: str | None) -> str:
    if cli_pem_path:
        return Path(cli_pem_path).read_text(encoding="utf-8")
    _load_dotenv_if_missing(["KINESCOPE_JWT_PRIVATE_KEY_PEM", "KINESCOPE_JWT_PRIVATE_KEY_PATH"])
    inline = (os.environ.get("KINESCOPE_JWT_PRIVATE_KEY_PEM") or "").strip()
    if inline:
        return inline.replace("\\n", "\n")
    path = (os.environ.get("KINESCOPE_JWT_PRIVATE_KEY_PATH") or "").strip()
    if path:
        p = Path(path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
    print(
        "ERROR: private key not found. Pass --pem-path, or set KINESCOPE_JWT_PRIVATE_KEY_PEM "
        "or KINESCOPE_JWT_PRIVATE_KEY_PATH in env / .env.",
        file=sys.stderr,
    )
    sys.exit(2)


def _derive_public_pem(private_pem: str) -> str:
    priv = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
    return (
        priv.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )


def _api_headers() -> dict[str, str]:
    _load_dotenv_if_missing(["KINESCOPE_API_KEY"])
    key = (os.environ.get("KINESCOPE_API_KEY") or "").strip()
    if not key:
        print("ERROR: KINESCOPE_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _project_id(cli_project: str | None) -> str:
    if cli_project:
        return cli_project
    _load_dotenv_if_missing(["KINESCOPE_PROJECT_ID"])
    proj = (os.environ.get("KINESCOPE_PROJECT_ID") or "").strip()
    if not proj:
        print("ERROR: --project-id not given and KINESCOPE_PROJECT_ID not set", file=sys.stderr)
        sys.exit(2)
    return proj


# === subcommands =============================================================

def cmd_sign_token(args: argparse.Namespace) -> int:
    private_pem = _load_private_pem(args.pem_path)
    _load_dotenv_if_missing(["KINESCOPE_JWK_KID", "KINESCOPE_DRM_TOKEN_TTL_SECONDS", "BACKEND_URL"])

    kid = (args.kid or os.environ.get("KINESCOPE_JWK_KID") or "").strip()
    if not kid:
        print("ERROR: --kid not given and KINESCOPE_JWK_KID not set", file=sys.stderr)
        return 2

    ttl = int(args.ttl_seconds or os.environ.get("KINESCOPE_DRM_TOKEN_TTL_SECONDS") or 300)
    issuer = (args.issuer or os.environ.get("BACKEND_URL") or "lucy-nails").rstrip("/")

    now = int(time.time())
    payload: dict[str, Any] = {
        "aud": args.audience,
        "iss": issuer,
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        "user_id": args.user_id,
    }
    if args.email:
        payload["email"] = args.email
    if args.lesson_id:
        payload["lesson_id"] = args.lesson_id

    token = jwt.encode(payload, private_pem, algorithm=ALGORITHMS.RS256, headers={"kid": kid})
    result: dict[str, Any] = {
        "token": token,
        "payload": payload,
        "kid": kid,
        "ttl_seconds": ttl,
    }
    if args.video_id:
        result["embed_url"] = (
            f"https://kinescope.io/embed/{args.video_id}?drmauthtoken={token}"
        )
    if args.print_embed and args.video_id:
        print(result["embed_url"])
    elif args.print_token:
        print(token)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_decode_token(args: argparse.Namespace) -> int:
    token = args.token
    if token.startswith("@"):
        token = Path(token[1:]).read_text(encoding="utf-8").strip()

    header = jwt.get_unverified_header(token)
    unverified = jwt.get_unverified_claims(token)
    out: dict[str, Any] = {"header": header, "claims": unverified, "verified": False}

    if args.verify:
        private_pem = _load_private_pem(args.pem_path)
        public_pem = _derive_public_pem(private_pem)
        _load_dotenv_if_missing(["BACKEND_URL"])
        issuer = (args.issuer or os.environ.get("BACKEND_URL") or "lucy-nails").rstrip("/")
        decoded = jwt.decode(
            token,
            public_pem,
            algorithms=[ALGORITHMS.RS256],
            audience=args.audience,
            issuer=issuer,
            options={"require_exp": True, "require_iat": True, "require_nbf": False},
        )
        out["verified"] = True
        out["claims"] = decoded

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_list_jwks(args: argparse.Namespace) -> int:
    headers = _api_headers()
    r = requests.get(f"{_KINESCOPE_API}/v1/jwk", headers=headers, timeout=20)
    try:
        body = r.json()
    except ValueError:
        body = {"text": r.text}
    print(json.dumps({"status_code": r.status_code, "body": body}, ensure_ascii=False, indent=2))
    return 0 if 200 <= r.status_code < 300 else 1


def cmd_get_drm_auth(args: argparse.Namespace) -> int:
    headers = _api_headers()
    project = _project_id(args.project_id)
    r = requests.get(f"{_KINESCOPE_API}/v1/drm/auth/{project}", headers=headers, timeout=20)
    try:
        body = r.json()
    except ValueError:
        body = {"text": r.text}
    print(json.dumps({"status_code": r.status_code, "body": body}, ensure_ascii=False, indent=2))
    return 0 if 200 <= r.status_code < 300 else 1


# === argparse wiring =========================================================

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Kinescope DRM debug/verification CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("sign-token", help="Sign a test drmauthtoken (RS256)")
    ps.add_argument("--user-id", required=True, help="user_id claim")
    ps.add_argument("--lesson-id", dest="lesson_id", help="lesson_id claim (optional)")
    ps.add_argument("--email", help="email claim (optional)")
    ps.add_argument("--video-id", dest="video_id", help="Kinescope video id (to build embed URL)")
    ps.add_argument("--ttl-seconds", dest="ttl_seconds", type=int, help="Token TTL (default 300)")
    ps.add_argument("--kid", help="Override KINESCOPE_JWK_KID")
    ps.add_argument("--issuer", help="Override iss claim (default = BACKEND_URL)")
    ps.add_argument("--audience", default=_JWT_AUDIENCE, help="aud claim")
    ps.add_argument("--pem-path", dest="pem_path", help="Override private key PEM path")
    ps.add_argument("--print-embed", dest="print_embed", action="store_true",
                    help="Print only the embed URL (requires --video-id)")
    ps.add_argument("--print-token", dest="print_token", action="store_true",
                    help="Print only the JWT string")
    ps.set_defaults(func=cmd_sign_token)

    pd = sub.add_parser("decode-token", help="Decode (and optionally verify) a JWT")
    pd.add_argument("--token", required=True, help="JWT string or @file containing it")
    pd.add_argument("--verify", action="store_true", help="Verify signature against derived public key")
    pd.add_argument("--issuer", help="Override iss claim for verification")
    pd.add_argument("--audience", default=_JWT_AUDIENCE, help="Expected aud claim")
    pd.add_argument("--pem-path", dest="pem_path", help="Override private key PEM path")
    pd.set_defaults(func=cmd_decode_token)

    pl = sub.add_parser("list-jwks", help="GET /v1/jwk — list registered JWKs")
    pl.set_defaults(func=cmd_list_jwks)

    pg = sub.add_parser("get-drm-auth", help="GET /v1/drm/auth/<project_id>")
    pg.add_argument("--project-id", dest="project_id", help="Override KINESCOPE_PROJECT_ID")
    pg.set_defaults(func=cmd_get_drm_auth)

    return p


def main() -> None:
    args = _build_parser().parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
