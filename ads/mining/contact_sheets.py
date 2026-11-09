"""Contact sheets of lesson frames for picking ad shots.

Each thumbnail shows its timestamp, a red line at the lowest row that is safe from
old subtitles, and a SUB tag when a subtitle is on screen in that frame.

    python ads/mining/contact_sheets.py folga --every 15
    python ads/mining/contact_sheets.py folga --range 60:80 --range 140:160 --every 1 --name fix
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from common import CACHE, clean_bottom, duration, fmt_time, grab_rgb, has_subtitle_rgb, source

COLS, ROWS = 5, 6
THUMB_W, THUMB_H = 384, 216
LABEL_H = 26
FONT = Path(__file__).resolve().parents[2] / "scripts" / "subtitles" / "fonts" / "Inter-Medium.ttf"


def sample_times(slug: str, every: float, ranges: list[tuple[float, float]]) -> list[float]:
    if ranges:
        return [float(t) for a, b in ranges for t in np.arange(a, b, every)]
    return [float(t) for t in np.arange(every / 2, duration(source(slug)), every)]


def thumb(slug: str, t: float, font: ImageFont.FreeTypeFont) -> Image.Image:
    frame = grab_rgb(source(slug), t)
    has_sub = has_subtitle_rgb(slug, frame)
    img = Image.fromarray(frame).resize((THUMB_W, THUMB_H), Image.LANCZOS)
    cell = Image.new("RGB", (THUMB_W, THUMB_H + LABEL_H), (24, 20, 22))
    cell.paste(img, (0, LABEL_H))
    draw = ImageDraw.Draw(cell)
    y = LABEL_H + round(clean_bottom(slug) * THUMB_H / frame.shape[0])
    draw.line([(0, y), (THUMB_W, y)], fill=(255, 40, 60), width=2)
    draw.text((6, 3), f"{fmt_time(t)}  {t:.1f}s", fill=(255, 255, 255), font=font)
    if has_sub:
        draw.text((THUMB_W - 46, 3), "SUB", fill=(255, 80, 100), font=font)
    return cell


def build(slug: str, every: float, ranges: list[tuple[float, float]], name: str) -> list[Path]:
    font = ImageFont.truetype(str(FONT), 17)
    times = sample_times(slug, every, ranges)
    with ThreadPoolExecutor(max_workers=8) as pool:
        cells = list(pool.map(lambda t: thumb(slug, t, font), times))
    out_dir = CACHE / "sheets" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    per_sheet = COLS * ROWS
    paths = []
    for n, i in enumerate(range(0, len(cells), per_sheet), start=1):
        chunk = cells[i : i + per_sheet]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * THUMB_W, rows * (THUMB_H + LABEL_H)), (12, 10, 11))
        for k, cell in enumerate(chunk):
            sheet.paste(cell, ((k % COLS) * THUMB_W, (k // COLS) * (THUMB_H + LABEL_H)))
        path = out_dir / f"{name}-{n:02d}.jpg"
        sheet.save(path, quality=85)
        paths.append(path)
    print(f"{slug}: {len(times)} frames -> {len(paths)} sheets in {out_dir}")
    return paths


def parse_range(text: str) -> tuple[float, float]:
    a, b = text.split(":")
    return float(a), float(b)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--every", type=float, default=15.0, help="seconds between frames")
    ap.add_argument("--range", dest="ranges", action="append", type=parse_range, default=[],
                    help="START:END in seconds, repeatable")
    ap.add_argument("--name", default="overview")
    args = ap.parse_args()
    build(args.slug, args.every, args.ranges, args.name)


if __name__ == "__main__":
    main()
