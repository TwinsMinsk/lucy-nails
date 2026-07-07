"""
Renders a course completion certificate (PNG + PDF) for a given student/course.

Pure and synchronous: no DB access, no FastAPI imports. Takes the dynamic
certificate fields as arguments, draws them onto the static diploma template
(backend/app/assets/certificates/template.png) using the shared layout
constants (backend/app/services/certificate_layout.py), and returns
image/PDF bytes. Fully unit-testable in isolation.
"""

from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

import img2pdf
import qrcode
from PIL import Image, ImageDraw, ImageFont

from app.services import certificate_layout as layout

# certificate_layout.py defines a shrink floor for the student name
# (STUDENT_NAME_SIZE_FLOOR) but not for the course title — "~80px" is the
# approximate floor called for by the certificate design brief, kept local
# to the renderer since nothing else needs to share it.
_COURSE_TITLE_SIZE_FLOOR = 80

_RU_MONTHS_GENITIVE = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def _format_ru_date(value: date) -> str:
    """Formats a date as '7 июля 2026' with no locale dependency."""
    return f"{value.day} {_RU_MONTHS_GENITIVE[value.month - 1]} {value.year}"


def _strip_url_scheme(url: str) -> str:
    """Strips a leading http(s):// for display (the QR code still encodes the full URL)."""
    return re.sub(r"^https?://", "", url, flags=re.IGNORECASE)


def _fit_font_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    start_size: int,
    max_width: float,
    min_size: int,
    step: int = 6,
) -> ImageFont.FreeTypeFont:
    """Shrinks a font from start_size down to min_size until text fits max_width."""
    return _fit_font_size_for_lines(draw, [text], font_path, start_size, max_width, min_size, step)


def _fit_font_size_for_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font_path: Path,
    start_size: int,
    max_width: float,
    min_size: int,
    step: int = 6,
) -> ImageFont.FreeTypeFont:
    """Shrinks a single font size that fits ALL given lines within max_width."""
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(str(font_path), size)
        if all(draw.textlength(line, font=font) <= max_width for line in lines):
            return font
        size -= step
    return ImageFont.truetype(str(font_path), min_size)


def _wrap_course_title_two_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path: Path,
    start_size: int,
    max_width: float,
    min_size: int,
    step: int = 6,
) -> tuple[str, str, ImageFont.FreeTypeFont]:
    """
    Splits text into 2 balanced lines at a word boundary, then finds a single
    font size that fits both lines within max_width. Falls back to an
    (unsplit, "") pair if the text has no internal word boundary to split on.
    """
    words = text.split(" ")
    if len(words) < 2:
        return text, "", ImageFont.truetype(str(font_path), min_size)

    ref_font = ImageFont.truetype(str(font_path), start_size)
    best_split: tuple[str, str] | None = None
    best_diff: float | None = None
    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])
        diff = abs(draw.textlength(line1, font=ref_font) - draw.textlength(line2, font=ref_font))
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_split = (line1, line2)

    line1, line2 = best_split
    font = _fit_font_size_for_lines(draw, [line1, line2], font_path, start_size, max_width, min_size, step)
    return line1, line2, font


def _draw_student_name(draw: ImageDraw.ImageDraw, student_name: str) -> None:
    font = _fit_font_size(
        draw,
        student_name,
        layout.STUDENT_NAME_FONT,
        layout.STUDENT_NAME_SIZE_START,
        layout.STUDENT_NAME_MAX_WIDTH,
        layout.STUDENT_NAME_SIZE_FLOOR,
    )
    draw.text(
        (layout.STUDENT_NAME_CENTER_X, layout.STUDENT_NAME_Y),
        student_name,
        font=font,
        fill=layout.STUDENT_NAME_COLOR,
        anchor="mm",
    )


def _draw_course_title(draw: ImageDraw.ImageDraw, course_title: str) -> None:
    full_text = layout.COURSE_TITLE_TEMPLATE.format(title=course_title)
    single_line_y = (layout.COURSE_TITLE_Y_LINE_1 + layout.COURSE_TITLE_Y_LINE_2) / 2

    font = _fit_font_size(
        draw,
        full_text,
        layout.COURSE_TITLE_FONT,
        layout.COURSE_TITLE_SIZE,
        layout.COURSE_TITLE_MAX_WIDTH,
        _COURSE_TITLE_SIZE_FLOOR,
    )
    if draw.textlength(full_text, font=font) <= layout.COURSE_TITLE_MAX_WIDTH:
        # Fits on one line even after shrinking: center it vertically between
        # the two designated line anchors.
        draw.text((layout.CENTER_X, single_line_y), full_text, font=font, fill=layout.COURSE_TITLE_COLOR, anchor="mm")
        return

    line1, line2, font = _wrap_course_title_two_lines(
        draw,
        full_text,
        layout.COURSE_TITLE_FONT,
        layout.COURSE_TITLE_SIZE,
        layout.COURSE_TITLE_MAX_WIDTH,
        _COURSE_TITLE_SIZE_FLOOR,
    )
    if not line2:
        # No word boundary to split on (single unsplittable token): render
        # unsplit at the floor size, even if it overflows slightly.
        draw.text((layout.CENTER_X, single_line_y), line1, font=font, fill=layout.COURSE_TITLE_COLOR, anchor="mm")
        return

    draw.text((layout.CENTER_X, layout.COURSE_TITLE_Y_LINE_1), line1, font=font, fill=layout.COURSE_TITLE_COLOR, anchor="mm")
    draw.text((layout.CENTER_X, layout.COURSE_TITLE_Y_LINE_2), line2, font=font, fill=layout.COURSE_TITLE_COLOR, anchor="mm")


def _draw_date_value(draw: ImageDraw.ImageDraw, issued_date: date) -> None:
    font = ImageFont.truetype(str(layout.DATE_VALUE_FONT), layout.DATE_VALUE_SIZE)
    draw.text(
        (layout.DATE_BLOCK_CENTER_X, layout.DATE_VALUE_Y),
        _format_ru_date(issued_date),
        font=font,
        fill=layout.DATE_VALUE_COLOR,
        anchor="mm",
    )


def _draw_number_and_verify_line(draw: ImageDraw.ImageDraw, certificate_number: str, verify_url: str) -> None:
    number_font = ImageFont.truetype(str(layout.CERTIFICATE_NUMBER_FONT), layout.CERTIFICATE_NUMBER_SIZE)
    draw.text(
        (layout.CERTIFICATE_NUMBER_CENTER_X, layout.CERTIFICATE_NUMBER_Y),
        layout.CERTIFICATE_NUMBER_TEMPLATE.format(number=certificate_number),
        font=number_font,
        fill=layout.CERTIFICATE_NUMBER_COLOR,
        anchor="mm",
    )

    verify_font = ImageFont.truetype(str(layout.VERIFY_URL_FONT), layout.VERIFY_URL_SIZE)
    draw.text(
        (layout.VERIFY_URL_CENTER_X, layout.VERIFY_URL_Y),
        _strip_url_scheme(verify_url),
        font=verify_font,
        fill=layout.VERIFY_URL_COLOR,
        anchor="mm",
    )


def _draw_qr_code(canvas: Image.Image, draw: ImageDraw.ImageDraw, verify_url: str) -> None:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color=layout.COLOR_INK, back_color=layout.COLOR_BACKGROUND).get_image().convert("RGB")

    box_x0, box_y0, box_x1, box_y1 = layout.QR_BOX
    box_size = (box_x1 - box_x0, box_y1 - box_y0)
    qr_image = qr_image.resize(box_size, Image.Resampling.LANCZOS)
    canvas.paste(qr_image, (box_x0, box_y0))

    caption_font = ImageFont.truetype(str(layout.QR_CAPTION_FONT), layout.QR_CAPTION_SIZE)
    draw.text(
        (layout.QR_CAPTION_CENTER_X, layout.QR_CAPTION_Y),
        layout.QR_CAPTION_TEXT,
        font=caption_font,
        fill=layout.QR_CAPTION_COLOR,
        anchor="mm",
    )


def render_certificate_png(
    student_name: str,
    course_title: str,
    certificate_number: str,
    issued_date: date,
    verify_url: str,
) -> bytes:
    """Renders the full diploma (template + dynamic fields + QR code) as PNG bytes."""
    canvas = Image.open(layout.TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    _draw_student_name(draw, student_name)
    _draw_course_title(draw, course_title)
    _draw_date_value(draw, issued_date)
    _draw_number_and_verify_line(draw, certificate_number, verify_url)
    _draw_qr_code(canvas, draw, verify_url)

    buf = io.BytesIO()
    canvas.save(buf, "PNG", dpi=(300, 300))
    return buf.getvalue()


def png_to_pdf(png_bytes: bytes) -> bytes:
    """Wraps a certificate PNG into a single A4-landscape PDF page."""
    layout_fun = img2pdf.get_layout_fun(pagesize=(img2pdf.mm_to_pt(297), img2pdf.mm_to_pt(210)))
    return img2pdf.convert(png_bytes, layout_fun=layout_fun)
