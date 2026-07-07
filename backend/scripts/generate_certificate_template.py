"""Generate the static diploma background (backend/app/assets/certificates/template.png).

Draws every STATIC certificate element (frame, ornaments, header, title,
static labels/lines) onto the cream canvas. Dynamic elements (student name,
course title, date value, certificate number, QR code) are drawn at request
time by the renderer on top of this template, using the same layout module.

Usage (from repo root):
  backend/venv/Scripts/python backend/scripts/generate_certificate_template.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from app.services import certificate_layout as layout  # noqa: E402


def _diamond_points(center: tuple[float, float], half_diagonal: float) -> list[tuple[float, float]]:
    """Return the 4 vertices of a rotated square (diamond) around center."""
    cx, cy = center
    return [
        (cx, cy - half_diagonal),
        (cx + half_diagonal, cy),
        (cx, cy + half_diagonal),
        (cx - half_diagonal, cy),
    ]


def _draw_diamond(draw: ImageDraw.ImageDraw, center: tuple[float, float], half_diagonal: float, fill: str) -> None:
    draw.polygon(_diamond_points(center, half_diagonal), fill=fill)


def _spaced_text_width(font: ImageFont.FreeTypeFont, text: str, spacing: float) -> float:
    total = sum(font.getlength(ch) for ch in text)
    return total + spacing * max(len(text) - 1, 0)


def _draw_spaced_text(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    spacing: float,
    fill: str,
) -> None:
    """Draw text char-by-char with extra tracking (Pillow has no native letter-spacing)."""
    x = center_x - _spaced_text_width(font, text, spacing) / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="lm")
        x += font.getlength(ch) + spacing


def _draw_ornament_divider(draw: ImageDraw.ImageDraw, y: float, width: float) -> None:
    """Two gold lines flanking a gold diamond, centered on the canvas."""
    half_width = width / 2
    gap = layout.DIVIDER_DIAMOND_HALF_DIAGONAL
    draw.line(
        [(layout.CENTER_X - half_width, y), (layout.CENTER_X - gap, y)],
        fill=layout.DIVIDER_COLOR,
        width=layout.DIVIDER_LINE_STROKE,
    )
    draw.line(
        [(layout.CENTER_X + gap, y), (layout.CENTER_X + half_width, y)],
        fill=layout.DIVIDER_COLOR,
        width=layout.DIVIDER_LINE_STROKE,
    )
    _draw_diamond(draw, (layout.CENTER_X, y), gap, layout.DIVIDER_COLOR)


def _draw_underline_with_diamond(
    draw: ImageDraw.ImageDraw, center_x: float, y: float, width: float, stroke: float, color: str, diamond_half_diagonal: float
) -> None:
    """A continuous line with a diamond overlaid at its center."""
    draw.line([(center_x - width / 2, y), (center_x + width / 2, y)], fill=color, width=int(stroke))
    _draw_diamond(draw, (center_x, y), diamond_half_diagonal, color)


def _draw_plain_line(draw: ImageDraw.ImageDraw, center_x: float, y: float, width: float, stroke: float, color: str) -> None:
    draw.line([(center_x - width / 2, y), (center_x + width / 2, y)], fill=color, width=int(stroke))


def generate_template() -> Image.Image:
    canvas = Image.new("RGB", (layout.CANVAS_WIDTH, layout.CANVAS_HEIGHT), layout.COLOR_BACKGROUND)
    draw = ImageDraw.Draw(canvas)

    # Frames.
    draw.rectangle(layout.OUTER_FRAME_BOUNDS, outline=layout.OUTER_FRAME_COLOR, width=layout.OUTER_FRAME_STROKE)
    draw.rectangle(layout.INNER_FRAME_BOUNDS, outline=layout.INNER_FRAME_COLOR, width=layout.INNER_FRAME_STROKE)
    for corner in layout.CORNER_DIAMOND_POSITIONS:
        _draw_diamond(draw, corner, layout.CORNER_DIAMOND_HALF_DIAGONAL, layout.CORNER_DIAMOND_COLOR)

    # Watermark: composited as a low-alpha RGBA overlay behind the name zone.
    watermark_font = ImageFont.truetype(str(layout.WATERMARK_FONT), layout.WATERMARK_SIZE)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    wm_r, wm_g, wm_b = Image.new("RGB", (1, 1), layout.WATERMARK_COLOR).getpixel((0, 0))
    wm_alpha = int(round(layout.WATERMARK_ALPHA * 255))
    overlay_draw.text(
        layout.WATERMARK_CENTER,
        layout.WATERMARK_TEXT,
        font=watermark_font,
        fill=(wm_r, wm_g, wm_b, wm_alpha),
        anchor="mm",
    )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # Header: "LUCY NAILS ACADEMY".
    header_font = ImageFont.truetype(str(layout.HEADER_FONT), layout.HEADER_SIZE)
    _draw_spaced_text(
        draw, layout.CENTER_X, layout.HEADER_Y, layout.HEADER_TEXT, header_font, layout.HEADER_LETTER_SPACING, layout.HEADER_COLOR
    )
    _draw_diamond(
        draw,
        (layout.CENTER_X, layout.HEADER_Y - layout.HEADER_DIAMOND_OFFSET_Y),
        layout.HEADER_DIAMOND_HALF_DIAGONAL,
        layout.HEADER_DIAMOND_COLOR,
    )

    # Title: "СЕРТИФИКАТ".
    title_font = ImageFont.truetype(str(layout.TITLE_FONT), layout.TITLE_SIZE)
    _draw_spaced_text(
        draw, layout.CENTER_X, layout.TITLE_Y, layout.TITLE_TEXT, title_font, layout.TITLE_LETTER_SPACING, layout.TITLE_COLOR
    )

    # First ornament divider.
    _draw_ornament_divider(draw, layout.DIVIDER_1_Y, layout.DIVIDER_1_WIDTH)

    # Subtitle: "настоящим подтверждается, что".
    subtitle_font = ImageFont.truetype(str(layout.SUBTITLE_FONT), layout.SUBTITLE_SIZE)
    draw.text(
        (layout.CENTER_X, layout.SUBTITLE_Y), layout.SUBTITLE_TEXT, font=subtitle_font, fill=layout.SUBTITLE_COLOR, anchor="mm"
    )

    # Name underline (student name itself is dynamic, drawn later by the renderer).
    _draw_underline_with_diamond(
        draw,
        layout.CENTER_X,
        layout.NAME_UNDERLINE_Y,
        layout.NAME_UNDERLINE_WIDTH,
        layout.NAME_UNDERLINE_STROKE,
        layout.NAME_UNDERLINE_COLOR,
        layout.NAME_UNDERLINE_DIAMOND_HALF_DIAGONAL,
    )

    # Course intro: "успешно прошла курс".
    course_intro_font = ImageFont.truetype(str(layout.COURSE_INTRO_FONT), layout.COURSE_INTRO_SIZE)
    draw.text(
        (layout.CENTER_X, layout.COURSE_INTRO_Y),
        layout.COURSE_INTRO_TEXT,
        font=course_intro_font,
        fill=layout.COURSE_INTRO_COLOR,
        anchor="mm",
    )

    # Second ornament divider.
    _draw_ornament_divider(draw, layout.DIVIDER_2_Y, layout.DIVIDER_2_WIDTH)

    # Date block: static line + label (the date VALUE is dynamic, not drawn here).
    _draw_plain_line(
        draw, layout.DATE_BLOCK_CENTER_X, layout.DATE_LINE_Y, layout.DATE_LINE_WIDTH, layout.DATE_LINE_STROKE, layout.DATE_LINE_COLOR
    )
    date_label_font = ImageFont.truetype(str(layout.DATE_LABEL_FONT), layout.DATE_LABEL_SIZE)
    draw.text(
        (layout.DATE_BLOCK_CENTER_X, layout.DATE_LABEL_Y),
        layout.DATE_LABEL_TEXT,
        font=date_label_font,
        fill=layout.DATE_LABEL_COLOR,
        anchor="mm",
    )

    # Signature block: static signature, line and label.
    _draw_plain_line(
        draw,
        layout.SIGNATURE_BLOCK_CENTER_X,
        layout.SIGNATURE_LINE_Y,
        layout.SIGNATURE_LINE_WIDTH,
        layout.SIGNATURE_LINE_STROKE,
        layout.SIGNATURE_LINE_COLOR,
    )
    signature_font = ImageFont.truetype(str(layout.SIGNATURE_FONT), layout.SIGNATURE_SIZE)
    draw.text(
        (layout.SIGNATURE_BLOCK_CENTER_X, layout.SIGNATURE_BASELINE_Y),
        layout.SIGNATURE_TEXT,
        font=signature_font,
        fill=layout.SIGNATURE_COLOR,
        anchor="mm",
    )
    signature_label_font = ImageFont.truetype(str(layout.SIGNATURE_LABEL_FONT), layout.SIGNATURE_LABEL_SIZE)
    draw.text(
        (layout.SIGNATURE_BLOCK_CENTER_X, layout.SIGNATURE_LABEL_Y),
        layout.SIGNATURE_LABEL_TEXT,
        font=signature_label_font,
        fill=layout.SIGNATURE_LABEL_COLOR,
        anchor="mm",
    )

    return canvas


def main() -> int:
    layout.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    canvas = generate_template()
    canvas.save(layout.TEMPLATE_PATH, format="PNG")
    print(f"Saved template: {layout.TEMPLATE_PATH} ({canvas.width}x{canvas.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
