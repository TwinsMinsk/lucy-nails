"""Unit tests for the certificate PNG/PDF renderer.

Pure and synchronous (no DB, no FastAPI) — must not require any test DB
fixtures. See conftest.py: the session-scoped `prepare_database` fixture is
autouse and still connects to the test DB regardless of what an individual
test file needs, so running this file alone requires DATABASE_URL/ENVIRONMENT
overrides just like any other test in this suite.
"""

from datetime import date
from io import BytesIO

from PIL import Image, ImageDraw

from app.services import certificate_layout as layout
from app.services.certificate_renderer import (
    _COURSE_TITLE_SIZE_FLOOR,
    _fit_font_size,
    _wrap_course_title_two_lines,
    png_to_pdf,
    render_certificate_png,
)

_TYPICAL_KWARGS = {
    "student_name": "Анна Иванова",
    "course_title": "Идеальный маникюр с нуля",
    "certificate_number": "LN-2026-A7K3MX",
    "issued_date": date(2026, 7, 7),
    "verify_url": "https://lucysmirnova.ru/certificate/LN-2026-A7K3MX",
}


def test_render_certificate_png_happy_path():
    png_bytes = render_certificate_png(**_TYPICAL_KWARGS)

    assert png_bytes.startswith(b"\x89PNG")
    image = Image.open(BytesIO(png_bytes))
    assert image.size == (layout.CANVAS_WIDTH, layout.CANVAS_HEIGHT)
    assert image.mode == "RGB"


def test_render_certificate_png_long_name_does_not_raise():
    kwargs = {**_TYPICAL_KWARGS, "student_name": "Александра-Виктория Константинопольская"}

    png_bytes = render_certificate_png(**kwargs)

    assert png_bytes.startswith(b"\x89PNG")


def test_fit_font_size_shrinks_long_text_but_never_below_floor():
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    min_size = layout.STUDENT_NAME_SIZE_FLOOR

    short_font = _fit_font_size(
        draw,
        "Яна Ли",
        layout.STUDENT_NAME_FONT,
        layout.STUDENT_NAME_SIZE_START,
        layout.STUDENT_NAME_MAX_WIDTH,
        min_size,
    )
    assert short_font.size == layout.STUDENT_NAME_SIZE_START

    long_font = _fit_font_size(
        draw,
        "Александра-Виктория Константинопольская",
        layout.STUDENT_NAME_FONT,
        layout.STUDENT_NAME_SIZE_START,
        layout.STUDENT_NAME_MAX_WIDTH,
        min_size,
    )
    assert long_font.size < short_font.size
    assert long_font.size >= min_size


def test_render_certificate_png_long_course_title_wraps_to_two_lines():
    long_title = (
        "Аппаратный маникюр, педикюр и сложные покрытия: продвинутый курс "
        "для мастеров индустрии красоты"
    )
    assert len(long_title) > 90
    kwargs = {**_TYPICAL_KWARGS, "course_title": long_title}

    png_bytes = render_certificate_png(**kwargs)

    assert png_bytes.startswith(b"\x89PNG")


def test_wrap_course_title_two_lines_splits_long_title_at_word_boundary():
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    long_title = (
        "Аппаратный маникюр, педикюр и сложные покрытия: продвинутый курс "
        "для мастеров индустрии красоты"
    )
    assert len(long_title) > 90

    line1, line2, font = _wrap_course_title_two_lines(
        draw,
        long_title,
        layout.COURSE_TITLE_FONT,
        layout.COURSE_TITLE_SIZE,
        layout.COURSE_TITLE_MAX_WIDTH,
        _COURSE_TITLE_SIZE_FLOOR,
    )

    assert line1 and line2
    width1 = draw.textlength(line1, font=font)
    width2 = draw.textlength(line2, font=font)
    assert width1 <= layout.COURSE_TITLE_MAX_WIDTH
    assert width2 <= layout.COURSE_TITLE_MAX_WIDTH

    # Split happened at a word boundary: rejoining with a single space
    # reconstructs the original title exactly.
    assert f"{line1} {line2}" == long_title

    # Reasonably balanced: the shorter line is at least 25% of the longer
    # line's width. A degenerate split (e.g. everything crammed onto one
    # line and an empty/near-empty second line) would fail this.
    shorter_width, longer_width = sorted((width1, width2))
    assert shorter_width >= 0.25 * longer_width


def test_wrap_course_title_two_lines_short_single_word_stays_on_one_line():
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    short_title = "Маникюр"

    line1, line2, font = _wrap_course_title_two_lines(
        draw,
        short_title,
        layout.COURSE_TITLE_FONT,
        layout.COURSE_TITLE_SIZE,
        layout.COURSE_TITLE_MAX_WIDTH,
        _COURSE_TITLE_SIZE_FLOOR,
    )

    assert line1 == short_title
    assert line2 == ""
    assert font.size == _COURSE_TITLE_SIZE_FLOOR


def test_wrap_course_title_two_lines_unsplittable_long_token_does_not_raise():
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    long_token = "А" * 90

    line1, line2, font = _wrap_course_title_two_lines(
        draw,
        long_token,
        layout.COURSE_TITLE_FONT,
        layout.COURSE_TITLE_SIZE,
        layout.COURSE_TITLE_MAX_WIDTH,
        _COURSE_TITLE_SIZE_FLOOR,
    )

    assert line1 == long_token
    assert line2 == ""
    assert font.size == _COURSE_TITLE_SIZE_FLOOR


def test_png_to_pdf_produces_pdf_bytes():
    png_bytes = render_certificate_png(**_TYPICAL_KWARGS)

    pdf_bytes = png_to_pdf(png_bytes)

    assert pdf_bytes.startswith(b"%PDF")


def test_render_certificate_png_is_deterministic():
    first = render_certificate_png(**_TYPICAL_KWARGS)
    second = render_certificate_png(**_TYPICAL_KWARGS)

    if first == second:
        return

    # Fall back to comparing decoded pixel data in case PNG metadata (e.g. a
    # timestamp chunk) makes the raw bytes differ despite identical pixels.
    first_image = Image.open(BytesIO(first))
    second_image = Image.open(BytesIO(second))
    assert list(first_image.getdata()) == list(second_image.getdata())
