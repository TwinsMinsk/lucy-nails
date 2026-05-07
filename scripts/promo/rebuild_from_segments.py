"""Локальный пересбор промо без транскрипции — берём сегменты из program.json."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.promo.cut_video import build_promo_video
from scripts.promo.paths import (
    local_promos_collect_dir,
    output_dir,
    program_json_path,
    video_lessons_dir,
)


def rebuild(slug: str, *, regen_intro: bool = False) -> Path:
    prog = json.loads(program_json_path().read_text(encoding="utf-8"))
    mod = next(m for m in prog["modules"] if m["slug"] == slug)
    segs = [(h["start_sec"], h["end_sec"]) for h in mod["promo"]["highlight_segments"]]
    if not segs:
        raise SystemExit(f"Нет сегментов для {slug}")
    src = video_lessons_dir() / mod["source_file"]
    work = output_dir() / slug
    work.mkdir(parents=True, exist_ok=True)
    promo = work / "promo.mp4"
    build_promo_video(
        src,
        segs,
        mod["title"],
        promo,
        work / "clips_tmp",
        slug=slug,
        lesson_order=int(mod["order"]),
        intro_cache_dir=work,
        regen_intro_bg=regen_intro,
    )
    collect = local_promos_collect_dir()
    collect.mkdir(parents=True, exist_ok=True)
    dest = collect / f"{mod['order']:02d}-{slug}-promo.mp4"
    shutil.copy2(promo, dest)
    return dest


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*", default=["folga"])
    ap.add_argument("--regen-intro", action="store_true", help="Перегенерировать AI-фон intro")
    args = ap.parse_args()
    for s in args.slugs:
        out = rebuild(s, regen_intro=args.regen_intro)
        print(f"OK -> {out}")
