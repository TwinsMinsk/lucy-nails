"""Пути пайплайна субтитров. Переиспользует карту уроков из scripts/promo."""

from __future__ import annotations

import sys
from pathlib import Path

# Консоль Windows по умолчанию в cp1251 и роняет вывод на «×» и прочей типографике
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_MODULE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MODULE_DIR.parents[1]

# run_lesson.py запускается как скрипт, поэтому корень репозитория в sys.path не попадает
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.promo.catalog import VIDEO_CATALOG, find_catalog_entry  # noqa: E402
from scripts.promo.paths import video_lessons_dir  # noqa: E402

__all__ = [
    "VIDEO_CATALOG",
    "find_catalog_entry",
    "video_lessons_dir",
    "repo_root",
    "module_dir",
    "fonts_dir",
    "glossary_path",
    "remaster_root",
    "lesson_dirs",
    "promo_output_dir",
    "resolve_lesson",
]


def repo_root() -> Path:
    return _REPO_ROOT


def module_dir() -> Path:
    return _MODULE_DIR


def fonts_dir() -> Path:
    return _MODULE_DIR / "fonts"


def glossary_path() -> Path:
    return _MODULE_DIR / "glossary.json"


def remaster_root() -> Path:
    """Копии уроков с новыми субтитрами. Исходники в video-lessons/ не трогаем."""
    return _REPO_ROOT / "video-lessons-remastered"


def promo_output_dir(slug: str) -> Path:
    """Папка промо-пайплайна: там уже лежит audio_16k.wav и старый transcript.json."""
    return _REPO_ROOT / "scripts" / "promo" / "output" / slug


def lesson_dirs(slug: str) -> dict[str, Path]:
    base = remaster_root() / slug
    return {
        "base": base,
        "subs": base / "subs",
        "qa": base / "qa",
        "work": base / ".work",
    }


def resolve_lesson(slug: str) -> tuple[Path, str]:
    """slug -> (путь к исходному mp4, человекочитаемый заголовок)."""
    for entry in VIDEO_CATALOG:
        if entry.slug != slug:
            continue
        for candidate in sorted(video_lessons_dir().glob("*.mp4")):
            found = find_catalog_entry(candidate.name)
            if found and found.slug == slug:
                return candidate, entry.title
        raise FileNotFoundError(
            f"Урок '{slug}' есть в каталоге, но файла нет в {video_lessons_dir()}"
        )
    known = ", ".join(e.slug for e in VIDEO_CATALOG)
    raise KeyError(f"Неизвестный урок '{slug}'. Доступны: {known}")
