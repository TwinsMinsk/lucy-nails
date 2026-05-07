#!/usr/bin/env python3
"""
Залить поля промо из scripts/promo/program.json в БД (только UPDATE, без truncate).

Использует те же переменные, что и backend: корневой .env, DATABASE_URL
или POSTGRES_HOST / POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB.

Пример (из корня репозитория):
  python scripts/promo/sync_program_to_db.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "backend" / ".env")

PROGRAM_JSON = Path(__file__).resolve().parent / "program.json"


def get_connection():
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        if raw.startswith("postgresql+asyncpg://"):
            raw = raw.replace("postgresql+asyncpg://", "postgresql://", 1)
        return psycopg2.connect(raw)

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "nails_course"),
    )


def main() -> int:
    if not PROGRAM_JSON.is_file():
        print(f"Нет файла {PROGRAM_JSON}", file=sys.stderr)
        return 1

    data = json.loads(PROGRAM_JSON.read_text(encoding="utf-8"))
    conn = get_connection()
    cur = conn.cursor()
    total = 0
    try:
        for mod in data.get("modules", []):
            title = mod.get("title")
            promo = mod.get("promo") or {}
            if not title:
                continue
            hid = promo.get("kinescope_id")
            poster = promo.get("poster")
            desc = promo.get("description")
            bullets = promo.get("bullets") or []
            segments = promo.get("highlight_segments") or []
            highlights_obj = {"bullets": bullets, "segments": segments}
            cur.execute(
                """
                UPDATE lessons AS l SET
                  promo_kinescope_video_id = COALESCE(%s, l.promo_kinescope_video_id),
                  promo_poster_url = COALESCE(%s, l.promo_poster_url),
                  promo_description = COALESCE(%s, l.promo_description),
                  promo_highlights = COALESCE(%s, l.promo_highlights)
                FROM modules m
                WHERE l.module_id = m.id AND m.title = %s AND l.order_index = 1
                """,
                (
                    hid,
                    poster,
                    desc,
                    Json(highlights_obj),
                    title,
                ),
            )
            total += cur.rowcount
        conn.commit()
        print(f"OK: обновлено строк уроков (промо): {total}")
        if total == 0:
            print(
                "Подсказка: названия модулей в БД должны совпадать с полем «title» "
                "в program.json (например «Пигменты»). Первый прогон лучше сделать через seed.",
                file=sys.stderr,
            )
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
