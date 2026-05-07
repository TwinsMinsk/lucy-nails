"""Загрузка готового промо-ролика в Kinescope (uploader v2, один POST)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

UPLOAD_URL = "https://uploader.kinescope.io/v2/video"
API_INFO_URL = "https://api.kinescope.io/v1/videos/{video_id}"


def upload_video_file(
    file_path: Path,
    *,
    title: str,
    description: str = "",
    parent_id: str | None = None,
    api_key: str | None = None,
) -> dict:
    """
    Возвращает dict с ключами: id (str), poster (str|None), title (str).
    poster: прямая ссылка kinescope.io/.../poster.jpg при отсутствии в ответе.
    """
    key = (api_key or os.environ.get("KINESCOPE_API_KEY", "")).strip()
    pid = (parent_id or os.environ.get("KINESCOPE_PROJECT_ID", "")).strip()
    if not key:
        raise RuntimeError("KINESCOPE_API_KEY не задан")
    if not pid:
        raise RuntimeError("KINESCOPE_PROJECT_ID не задан (X-Parent-ID)")

    body = file_path.read_bytes()
    headers = {
        "Authorization": f"Bearer {key}",
        "X-Parent-ID": pid,
        "X-Video-Title": title[:500],
        "Content-Type": "video/mp4",
    }
    if description:
        headers["X-Video-Description"] = description[:2000]

    with httpx.Client(timeout=600.0) as client:
        r = client.post(UPLOAD_URL, headers=headers, content=body)
        r.raise_for_status()

    data = {}
    try:
        data = r.json()
    except json.JSONDecodeError:
        data = {}

    vid = (
        data.get("id")
        or data.get("data", {}).get("id")
        or (data.get("data") or {}).get("video_id")
    )
    if not vid:
        loc = r.headers.get("Location") or ""
        # .../videos/{uuid}
        if "/videos/" in loc:
            vid = loc.rstrip("/").split("/")[-1]

    if not vid:
        raise RuntimeError(f"Не удалось извлечь video id из ответа загрузки: {r.text[:500]}")

    poster_url = None
    if isinstance(data.get("poster"), dict):
        poster_url = data["poster"].get("url")

    if not poster_url:
        with httpx.Client(timeout=30.0) as client:
            info_r = client.get(
                API_INFO_URL.format(video_id=vid),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
            if info_r.is_success:
                info = info_r.json()
                poster_url = (info.get("poster") or {}).get("url")

    if not poster_url:
        poster_url = f"https://kinescope.io/{vid}/poster.jpg"

    return {"id": vid, "poster": poster_url, "title": title}


def build_embed_url(video_id: str) -> str:
    return f"https://kinescope.io/embed/{video_id}"
