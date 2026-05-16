#!/usr/bin/env python3
"""Создаёт transcript_plain.txt и transcript_full_text.txt из уже сохранённых transcript.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "scripts" / "promo" / "output"


def write_plain(out_dir: Path) -> bool:
    cache = out_dir / "transcript.json"
    if not cache.is_file():
        return False
    data = json.loads(cache.read_text(encoding="utf-8"))
    segments = data.get("segments") or []
    plain = "\n\n".join(
        f"[{s['start']:.1f} – {s['end']:.1f}] {s['text']}" for s in segments
    )
    (out_dir / "transcript_plain.txt").write_text(plain, encoding="utf-8")
    (out_dir / "transcript_full_text.txt").write_text(
        " ".join(s["text"].strip() for s in segments if s.get("text")),
        encoding="utf-8",
    )
    return True


def main() -> int:
    if not OUT.is_dir():
        print(f"Нет каталога {OUT}", file=sys.stderr)
        return 1
    n = 0
    for sub in sorted(OUT.iterdir()):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        if write_plain(sub):
            print(f"OK {sub.name}")
            n += 1
    print(f"Готово: {n} папок.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
