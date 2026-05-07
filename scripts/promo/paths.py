"""Пути относительно корня репозитория."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def video_lessons_dir() -> Path:
    return repo_root() / "video-lessons"


def output_dir() -> Path:
    return Path(__file__).resolve().parent / "output"


def program_json_path() -> Path:
    return Path(__file__).resolve().parent / "program.json"


def local_promos_collect_dir() -> Path:
    """Единая папка с готовыми промо для ручной выкладки (без БД)."""
    return repo_root() / "promo-clips"


def shared_promo_assets_dir() -> Path:
    """Общие ассеты промо (например outro.png)."""
    return output_dir() / "_shared"
