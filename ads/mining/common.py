"""Shared paths and helpers for mining lesson footage for the Reels campaign.

Lessons carry burned-in subtitles (no separate track). Their band was already
measured per lesson by scripts/subtitles (video-lessons-remastered/<slug>/.work/band.json);
everything here keeps ad footage clear of it.

Detecting a subtitle in one frame: scripts/subtitles/detect_band.text_mask looks for
white pixels next to near-black ones, which works for measuring the band over many
frames but misses most single frames here: the text has a soft grey shadow, and on
white gloves no pixel around it drops below 90. A white top-hat (pixel minus its
7x7 opening) picks out thin bright strokes regardless of the background; on hand-
labelled folga frames text gave 17-57 text rows and 1700+ pixels, empty frames at
most 1 row and 188 pixels.
"""

from __future__ import annotations

import json
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.ndimage import grey_opening

REPO = Path(__file__).resolve().parents[2]
ADS = REPO / "ads"
CACHE = ADS / "cache"
LESSONS = REPO / "video-lessons"
REMASTERED = REPO / "video-lessons-remastered"
PROGRAM = REPO / "scripts" / "promo" / "program.json"
WORKS = REPO / "frontend" / "public" / "works"

BAND_MARGIN = 16   # px kept clear above the measured band when cropping
BAND_PAD = 8       # px added around the band when looking for text
STROKE_WHITE = 205  # text strokes are near-white
STROKE_LIFT = 14    # ...and brighter than their 7x7 surroundings by this much
ROW_PIXELS = 12     # stroke pixels that make a band row a "text row"
TEXT_ROWS = 4       # a subtitle is on screen from this many text rows...
TEXT_PIXELS = 300   # ...or this many stroke pixels (kept low: a false alarm only costs a full-frame shot)


@lru_cache
def program() -> dict[str, dict]:
    modules = json.loads(PROGRAM.read_text(encoding="utf-8"))["modules"]
    return {m["slug"]: m for m in modules}


def slugs() -> list[str]:
    return list(program())


def source(slug: str) -> Path:
    return LESSONS / program()[slug]["source_file"]


@lru_cache
def band(slug: str) -> dict:
    return json.loads((REMASTERED / slug / ".work" / "band.json").read_text(encoding="utf-8"))


def clean_bottom(slug: str) -> int:
    """Lowest frame row (exclusive) that is guaranteed free of old subtitles."""
    return band(slug)["top"] - BAND_MARGIN


def band_box(slug: str) -> tuple[int, int, int, int]:
    """(top, bottom, left, right) of the band, padded, clamped to the frame."""
    b = band(slug)
    return (
        max(0, b["top"] - BAND_PAD),
        min(b["height"], b["bottom"] + BAND_PAD),
        max(0, b["left"] - BAND_PAD),
        min(b["width"], b["right"] + BAND_PAD),
    )


def duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def grab_rgb(video: Path, t: float, width: int = 1280, height: int = 720) -> np.ndarray:
    """One full-resolution RGB frame at time t."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw[: width * height * 3], dtype=np.uint8).reshape(height, width, 3)


def band_gray(slug: str, start: float, end: float, fps: float) -> tuple[np.ndarray, np.ndarray]:
    """Grayscale band strips for [start, end) at fps. Returns (times, frames)."""
    top, bottom, _, _ = band_box(slug)
    width = band(slug)["width"]
    strip = bottom - top
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
         "-i", str(source(slug)),
         "-vf", f"fps={fps},crop={width}:{strip}:0:{top},format=gray",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True, capture_output=True,
    ).stdout
    size = width * strip
    count = len(raw) // size
    frames = np.frombuffer(raw[: count * size], dtype=np.uint8).reshape(count, strip, width)
    times = start + np.arange(count) / fps
    return times, frames


def has_subtitle(slug: str, strips: np.ndarray) -> np.ndarray:
    """Per strip: is an old subtitle on screen? Strips are already cropped to the band rows."""
    _, _, left, right = band_box(slug)
    s = strips[:, :, left:right].astype(np.float32)
    lift = s - grey_opening(s, size=(1, 7, 7))
    strokes = (lift >= STROKE_LIFT) & (s >= STROKE_WHITE)
    rows = (strokes.sum(axis=2) >= ROW_PIXELS).sum(axis=1)
    return (rows >= TEXT_ROWS) | (strokes.sum(axis=(1, 2)) >= TEXT_PIXELS)


def has_subtitle_rgb(slug: str, frame: np.ndarray) -> bool:
    """Same check for a single full RGB frame."""
    top, bottom, _, _ = band_box(slug)
    gray = frame[top:bottom].astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    return bool(has_subtitle(slug, gray[None])[0])


def fmt_time(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m:02d}:{s:02d}"
