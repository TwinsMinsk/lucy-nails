"""AI-фон для intro-карточки + единая типографика Pillow (бренд Lucy Nails)."""

from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Цвета сайта — см. frontend/src/app/globals.css
COLOR_BG_TOP = (253, 251, 249)
COLOR_BG_BOTTOM = (242, 215, 217)
COLOR_GOLD = (212, 175, 55)
COLOR_TITLE = (45, 45, 45)
COLOR_SUBTITLE = (90, 75, 75)
CARD_WIDTH = 1280
CARD_HEIGHT = 720

GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
OPENAI_IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2")

# Тематика для промпта (англ., чтобы модель стабильнее следовала стилю)
SLUG_THEMES: dict[str, str] = {
    "folga": "metallic foil shimmer, golden and silver leaf flakes on glossy nails",
    "akvarium": "transparent jelly-like nail art with embedded micro-decorations",
    "vtirka": "pearl chrome powder, mirror-like iridescent finish",
    "slaidery": "delicate nail decals and water-slide patterns, soft pastel",
    "french": "classic French manicure tips, nude base, crisp white smile line",
    "pigmenty": "vibrant pigment powders blended in soft gradients",
    "stemping": "fine stamping plates, lace-like painted patterns on nails",
    "strazy": "rhinestones and 3D crystal embellishments catching light",
    "tekstury": "matte velvet texture nails with subtle relief",
    "gradient": "smooth ombre gradient pastel manicure",
    "aerografiya": "airbrushed soft nail art with misted color transitions",
}

BASE_IMAGE_PROMPT = """Premium minimalist background for a luxury nail-art online course.
Aesthetic: warm off-white #FDFBF9, soft nude pink #F2D7D9, delicate gold accents #D4AF37.
Style: high-end editorial, soft studio lighting, abstract glossy surface,
out-of-focus elegant manicure detail in the lower-right third,
thin gold filigree, generous empty space in the upper-left for typography overlay.
Strictly NO text, NO letters, NO digits, NO logos, NO watermarks, NO words anywhere.
1280x720 composition intent, 16:9 wide frame, photo-realistic, clean.
Theme of the lesson: {thematic}
"""


def _find_serif_title_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/playfairdisplay-variable.ttf",
        "C:/Windows/Fonts/PlayfairDisplay-Bold.ttf",
        "C:/Windows/Fonts/PlayfairDisplay-Italic.ttf",
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/seguiui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _find_sans_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
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


def _gradient_fallback() -> Image.Image:
    """Pillow-фон как раньше, без текста."""
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), color=COLOR_BG_TOP)
    draw = ImageDraw.Draw(img)
    for y in range(CARD_HEIGHT):
        t = y / CARD_HEIGHT
        r = int(COLOR_BG_TOP[0] + t * (COLOR_BG_BOTTOM[0] - COLOR_BG_TOP[0]))
        g = int(COLOR_BG_TOP[1] + t * (COLOR_BG_BOTTOM[1] - COLOR_BG_TOP[1]))
        b = int(COLOR_BG_TOP[2] + t * (COLOR_BG_BOTTOM[2] - COLOR_BG_TOP[2]))
        draw.line([(0, y), (CARD_WIDTH, y)], fill=(r, g, b))
    return img


def _resize_cover(img: Image.Image, w: int, h: int) -> Image.Image:
    img = img.convert("RGB")
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _overlay_brand(
    base: Image.Image,
    *,
    lesson_title: str,
    lesson_order: int,
    subtitle: str = "Lucy Nails Academy · Превью урока",
) -> None:
    """Рисует типографику поверх base (in-place)."""
    draw = ImageDraw.Draw(base)
    margin = 60
    gold = COLOR_GOLD
    for i in range(2):
        draw.rectangle(
            [margin - i, margin - i, CARD_WIDTH - margin + i, CARD_HEIGHT - margin + i],
            outline=gold,
            width=1,
        )

    font_badge = _find_sans_font(22)
    font_title = _find_serif_title_font(56)
    font_sub = _find_sans_font(26)
    font_star = _find_serif_title_font(36)

    cx = CARD_WIDTH // 2
    cy = CARD_HEIGHT // 2 - 20

    # декор
    draw.text((cx, cy - 120), "✦", font=font_star, fill=gold, anchor="mm")

    badge = f"Урок {lesson_order}"
    bbox_b = draw.textbbox((0, 0), badge, font=font_badge)
    bw, bh = bbox_b[2] - bbox_b[0], bbox_b[3] - bbox_b[1]
    pad_x, pad_y = 14, 8
    bx0 = cx - bw // 2 - pad_x
    bx1 = cx + bw // 2 + pad_x
    by0 = cy - 95
    by1 = by0 + bh + pad_y * 2
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, fill=(255, 248, 249))
    draw.text((cx, by0 + pad_y), badge, font=font_badge, fill=COLOR_SUBTITLE, anchor="mt")

    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text(
            (cx + dx, cy + dy),
            lesson_title,
            font=font_title,
            fill=(255, 255, 255),
            anchor="mm",
        )
    draw.text((cx, cy), lesson_title, font=font_title, fill=COLOR_TITLE, anchor="mm")
    draw.text((cx, cy + 72), subtitle, font=font_sub, fill=COLOR_SUBTITLE, anchor="mm")


def _save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")


def _bytes_from_gemini_response(response: object) -> bytes | None:
    cand = response.candidates
    if not cand:
        return None
    parts = cand[0].content.parts if cand[0].content else []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline and getattr(inline, "data", None):
            data = inline.data
            if isinstance(data, str):
                return base64.b64decode(data)
            return bytes(data)
        if hasattr(part, "as_image") and callable(part.as_image):
            try:
                pil = part.as_image()
                if pil is not None:
                    buf = io.BytesIO()
                    pil.save(buf, format="PNG")
                    return buf.getvalue()
            except Exception:
                pass
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=60))
def _generate_bg_gemini(slug: str, thematic: str, out_bg: Path) -> bool:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if not api_key:
        return False

    prompt = BASE_IMAGE_PROMPT.format(thematic=thematic)
    client = genai.Client(api_key=api_key)
    models_try = [GEMINI_IMAGE_MODEL, "gemini-3.1-flash-image-preview"]

    for model in models_try:
        try:
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
            )
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            raw = _bytes_from_gemini_response(response)
            if raw:
                img = Image.open(io.BytesIO(raw))
                img = _resize_cover(img, CARD_WIDTH, CARD_HEIGHT)
                _save_png(img, out_bg)
                logger.info("Intro BG: Gemini model=%s -> %s", model, out_bg)
                return True
        except Exception as e:
            logger.warning("Gemini image %s: %s", model, e)
            continue
    return False


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=60))
def _generate_bg_openai(slug: str, thematic: str, out_bg: Path) -> bool:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return False

    prompt = BASE_IMAGE_PROMPT.format(thematic=thematic)
    client = OpenAI(api_key=api_key)
    sizes_try = ["1536x1024", "1792x1024", "1024x1024"]
    models_try = [OPENAI_IMAGE_MODEL, "gpt-image-2"]

    for model in models_try:
        for size in sizes_try:
            try:
                result = client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    n=1,
                )
                item = result.data[0]
                if getattr(item, "b64_json", None):
                    raw = base64.b64decode(item.b64_json)
                elif getattr(item, "url", None):
                    import httpx

                    raw = httpx.get(item.url, timeout=120).content
                else:
                    continue
                img = Image.open(io.BytesIO(raw))
                img = _resize_cover(img, CARD_WIDTH, CARD_HEIGHT)
                _save_png(img, out_bg)
                logger.info("Intro BG: OpenAI model=%s size=%s -> %s", model, size, out_bg)
                return True
            except Exception as e:
                logger.warning("OpenAI image model=%s size=%s: %s", model, size, e)
                continue
    return False


def ensure_intro_background(
    slug: str,
    cache_path: Path,
    *,
    force: bool = False,
) -> Path:
    """Возвращает путь к intro_bg.png (создаёт при необходимости)."""
    if cache_path.is_file() and not force:
        return cache_path

    thematic = SLUG_THEMES.get(slug, "luxury nail art, soft studio aesthetic")

    # Приоритет изображений: Gemini (Nano Banana Pro) → OpenAI (gpt-image-2) → градиент
    if _generate_bg_gemini(slug, thematic, cache_path):
        return cache_path
    if _generate_bg_openai(slug, thematic, cache_path):
        return cache_path

    logger.warning("Intro BG: AI недоступен, градиент для slug=%s", slug)
    img = _gradient_fallback()
    _save_png(img, cache_path)
    return cache_path


def build_intro_card(
    slug: str,
    lesson_title: str,
    out_png: Path,
    *,
    lesson_order: int,
    subtitle: str = "Lucy Nails Academy · Превью урока",
    cache_dir: Path | None = None,
    regen_background: bool = False,
) -> Path:
    """
    Собирает финальный intro.png: AI/градиент фон + единая типографика.
    Кэш фона: cache_dir / intro_bg.png (по умолчанию рядом с out_png).
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)
    bg_cache = (cache_dir or out_png.parent) / "intro_bg.png"
    ensure_intro_background(slug, bg_cache, force=regen_background)

    base = Image.open(bg_cache).convert("RGB")
    base = _resize_cover(base, CARD_WIDTH, CARD_HEIGHT)
    _overlay_brand(base, lesson_title=lesson_title, lesson_order=lesson_order, subtitle=subtitle)
    _save_png(base, out_png)
    return out_png


def ensure_shared_outro_png(out_path: Path) -> Path:
    """Общая outro-карточка (градиент + типографика без номера урока)."""
    if out_path.is_file():
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base = _gradient_fallback()
    draw = ImageDraw.Draw(base)
    margin = 60
    gold = COLOR_GOLD
    for i in range(2):
        draw.rectangle(
            [margin - i, margin - i, CARD_WIDTH - margin + i, CARD_HEIGHT - margin + i],
            outline=gold,
            width=1,
        )
    font_title = _find_serif_title_font(52)
    font_sub = _find_sans_font(26)
    cx, cy = CARD_WIDTH // 2, CARD_HEIGHT // 2 - 10
    title = "Полный урок — в онлайн-курсе"
    sub = "Lucy Nails Academy"
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        draw.text((cx + dx, cy + dy), title, font=font_title, fill=(255, 255, 255), anchor="mm")
    draw.text((cx, cy), title, font=font_title, fill=COLOR_TITLE, anchor="mm")
    draw.text((cx, cy + 70), sub, font=font_sub, fill=COLOR_SUBTITLE, anchor="mm")
    draw.text((cx, cy - 100), "✦", font=font_title, fill=gold, anchor="mm")
    _save_png(base, out_path)
    return out_path
