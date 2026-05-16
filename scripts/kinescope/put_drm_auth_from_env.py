"""
Регистрирует DRM Authorization Backend в Kinescope (PUT /v1/drm/auth/{project}).

Читает из корневого .env рядом с репо (cwd = корень при запуске из корня):
  KINESCOPE_API_KEY, KINESCOPE_PROJECT_ID,
  KINESCOPE_DRM_BASIC_USER, KINESCOPE_DRM_BASIC_PASS

Пример:
  python scripts/kinescope/put_drm_auth_from_env.py
  python scripts/kinescope/put_drm_auth_from_env.py --webhook-base https://api.lucysmirnova.ru
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_env(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"missing env file: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"')
        os.environ.setdefault(k, v)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_REPO_ROOT / ".env",
        help="Path to .env",
    )
    parser.add_argument(
        "--webhook-base",
        default="https://api.lucysmirnova.ru",
        help="Backend public origin (no trailing slash), path /api/integrations/... appended",
    )
    args = parser.parse_args()

    _load_env(args.env_file)

    api_key = (os.environ.get("KINESCOPE_API_KEY") or "").strip()
    proj = (os.environ.get("KINESCOPE_PROJECT_ID") or "").strip()
    user = (os.environ.get("KINESCOPE_DRM_BASIC_USER") or "").strip()
    pw = os.environ.get("KINESCOPE_DRM_BASIC_PASS") or ""

    if not all([api_key, proj, user, pw]):
        print(
            "ERROR: need KINESCOPE_API_KEY, KINESCOPE_PROJECT_ID, "
            "KINESCOPE_DRM_BASIC_USER, KINESCOPE_DRM_BASIC_PASS in .env",
            file=sys.stderr,
        )
        return 2

    base = str(args.webhook_base).rstrip("/")
    webhook = f"{base}/api/integrations/kinescope/drm/authorize"
    body = {
        "url": webhook,
        "username": user,
        "password": pw,
        "strict": False,
    }

    with httpx.Client(timeout=30.0) as c:
        r = c.put(
            f"https://api.kinescope.io/v1/drm/auth/{proj}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    print("HTTP", r.status_code)
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(r.text[:800])

    return 0 if r.is_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
