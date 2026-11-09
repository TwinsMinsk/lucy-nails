"""Map where old burned-in subtitles are on screen across a lesson.

Writes ads/cache/subs/<slug>.json with a per-sample flag and the intervals that are
free of subtitles long enough to use the full 720 px frame.

    python ads/mining/subs_map.py folga            # one lesson
    python ads/mining/subs_map.py --all            # every lesson
    python ads/mining/subs_map.py folga --check 67 76   # verdict for one clip
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from common import CACHE, band_gray, duration, has_subtitle, slugs, source

FPS = 10
EDGE_PAD = 0.3      # s of margin before/after a subtitle
MIN_CLEAN = 1.0     # s; shorter gaps are not worth a full-frame shot


CHUNK = 60.0        # s decoded at a time; a whole lesson at once needs several GB


def scan(slug: str, start: float = 0.0, end: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    end = duration(source(slug)) if end is None else end
    all_times, all_flags = [], []
    for a in np.arange(start, end, CHUNK):
        times, strips = band_gray(slug, float(a), float(min(a + CHUNK, end)), FPS)
        all_times.append(times)
        all_flags.append(has_subtitle(slug, strips))
    return np.concatenate(all_times), np.concatenate(all_flags)


def clean_intervals(times: np.ndarray, has_text: np.ndarray, min_len: float = MIN_CLEAN) -> list[list[float]]:
    """Intervals with no subtitle, shrunk by EDGE_PAD on both sides."""
    out, run_start = [], None
    step = 1.0 / FPS
    for t, txt in zip(times, has_text):
        if not txt and run_start is None:
            run_start = t
        elif txt and run_start is not None:
            out.append([run_start, t])
            run_start = None
    if run_start is not None:
        out.append([run_start, float(times[-1]) + step])
    shrunk = [[round(a + EDGE_PAD, 2), round(b - EDGE_PAD, 2)] for a, b in out]
    return [iv for iv in shrunk if iv[1] - iv[0] >= min_len]


def build_map(slug: str) -> dict:
    times, has_text = scan(slug)
    data = {
        "slug": slug,
        "fps": FPS,
        "duration": round(float(times[-1]) + 1.0 / FPS, 2),
        "text_share": round(float(has_text.mean()), 3),
        "clean": clean_intervals(times, has_text),
        "has_text": "".join("1" if x else "0" for x in has_text),
    }
    out = CACHE / "subs" / f"{slug}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    total_clean = sum(b - a for a, b in data["clean"])
    print(f"{slug}: subtitles on {data['text_share']:.0%} of samples, "
          f"{len(data['clean'])} clean spans >= {MIN_CLEAN}s, {total_clean:.0f}s total -> {out}")
    return data


def check(slug: str, start: float, end: float) -> bool:
    times, has_text = scan(slug, start, end)
    hits = times[has_text]
    if hits.size:
        print(f"{slug} {start}-{end}: subtitles in {hits.size}/{times.size} samples, "
              f"first at {hits[0]:.1f}s, last at {hits[-1]:.1f}s -> crop_above_band")
        return False
    print(f"{slug} {start}-{end}: no subtitles in {times.size} samples -> full_frame_clean")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", nargs=2, type=float, metavar=("START", "END"))
    args = ap.parse_args()
    if args.check:
        check(args.slug, *args.check)
        return
    for slug in (slugs() if args.all else [args.slug]):
        build_map(slug)


if __name__ == "__main__":
    main()
