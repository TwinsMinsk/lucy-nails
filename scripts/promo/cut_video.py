"""Склейка промо: нарезки + crossfade + intro/outro карточки (Pillow + ffmpeg)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.promo.intro_image import build_intro_card, ensure_shared_outro_png
from scripts.promo.paths import shared_promo_assets_dir


def _find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/seguiui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _render_title_card_fallback(
    out_png: Path,
    title: str,
    *,
    subtitle: str = "Превью урока",
    width: int = 1280,
    height: int = 720,
) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    # фон в духе лендинга
    img = Image.new("RGB", (width, height), color=(255, 241, 244))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        r = int(255 - t * 20)
        g = int(241 - t * 30)
        b = int(244 - t * 15)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    font_lg = _find_font(56)
    font_sm = _find_font(32)
    # обводка читаемости
    cx, cy = width // 2, height // 2 - 20
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text(
            (cx + dx, cy + dy),
            title,
            font=font_lg,
            fill=(255, 255, 255),
            anchor="mm",
        )
    draw.text((cx, cy), title, font=font_lg, fill=(90, 75, 75), anchor="mm")
    draw.text((cx, cy + 70), subtitle, font=font_sm, fill=(120, 100, 100), anchor="mm")
    img.save(out_png, format="PNG")


def _render_outro_card_fallback(
    out_png: Path,
    text: str = "Полный урок — в онлайн-курсе",
) -> None:
    _render_title_card_fallback(out_png, text, subtitle="Lucy Nails Academy")


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def png_to_video(
    png: Path,
    out_mp4: Path,
    duration: float = 1.5,
) -> None:
    """Статичное изображение → H.264 + немой AAC-трек.

    Немое аудио обязательно: иначе при склейке через concat demuxer
    ffmpeg выкидывает аудиодорожку из всех клипов, потому что у одного
    из входов её нет.
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(png),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-shortest",
        str(out_mp4),
    ]
    _run(cmd)


def extract_segment(
    src: Path,
    dst: Path,
    start: float,
    end: float,
) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dur = max(end - start, 0.5)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(src),
        "-t",
        str(dur),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
        "-ac",
        "2",
        "-avoid_negative_ts",
        "make_zero",
        str(dst),
    ]
    _run(cmd)


def concat_with_crossfade(
    parts: list[Path],
    out_path: Path,
) -> None:
    """Склеить клипы последовательно (единый кодек)."""

    if not parts:
        raise ValueError("Нет клипов")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if len(parts) == 1:
        _run(["ffmpeg", "-y", "-i", str(parts[0]), "-c", "copy", str(out_path)])
        return

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        list_path = Path(f.name)
        for p in parts:
            safe = str(p.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_path),
        ]
        _run(cmd)
    finally:
        list_path.unlink(missing_ok=True)


def build_promo_video(
    source_mp4: Path,
    segments: list[tuple[float, float]],
    lesson_title: str,
    out_mp4: Path,
    tmp_dir: Path,
    *,
    slug: str,
    lesson_order: int,
    intro_cache_dir: Path,
    card_duration: float = 2.0,
    regen_intro_bg: bool = False,
) -> None:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    import shutil

    intro_png = tmp_dir / "intro.png"
    build_intro_card(
        slug,
        lesson_title,
        intro_png,
        lesson_order=lesson_order,
        cache_dir=intro_cache_dir,
        regen_background=regen_intro_bg,
    )

    shared = shared_promo_assets_dir()
    shared.mkdir(parents=True, exist_ok=True)
    outro_src = ensure_shared_outro_png(shared / "outro.png")
    outro_png = tmp_dir / "outro.png"
    shutil.copy2(outro_src, outro_png)

    intro_v = tmp_dir / "intro.mp4"
    outro_v = tmp_dir / "outro.mp4"
    png_to_video(intro_png, intro_v, card_duration)
    png_to_video(outro_png, outro_v, card_duration)

    middle: list[Path] = []
    for i, (start, end) in enumerate(segments):
        seg_path = tmp_dir / f"seg_{i}.mp4"
        extract_segment(source_mp4, seg_path, start, end)
        middle.append(seg_path)

    all_parts = [intro_v, *middle, outro_v]
    concat_with_crossfade(all_parts, out_mp4)
