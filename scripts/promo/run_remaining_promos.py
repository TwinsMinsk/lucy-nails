#!/usr/bin/env python3
"""Пакетный запуск generate_promos для оставшихся уроков (подстроки --only в NFC)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Явные NFC-строки (избегаем битой кодировки при сохранении файла)
ONLY_SUBSTRINGS = [
    "\u0441\u043b\u0430\u0439\u0434\u0435\u0440",  # слайдер
    "\u0444\u0440\u0435\u043d\u0447",  # френч
    "\u0441\u0442\u0435\u043c\u043f\u0438\u043d\u0433",  # стемпинг
    "\u0441\u0442\u0440\u0430\u0437",  # страз
    "\u0442\u0435\u043a\u0441\u0442\u0443\u0440",  # текстур
    "\u0433\u0440\u0430\u0434\u0438\u0435\u043d\u0442",  # градиент
    "\u0430\u044d\u0440\u043e\u0433\u0440\u0430\u0444",  # аэрограф
]


def main() -> int:
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8"}
    for sub in ONLY_SUBSTRINGS:
        print(f"\n=== --only {sub!r} ===\n", flush=True)
        r = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "promo" / "generate_promos.py"),
                "--local-only",
                "--only",
                sub,
                "--device",
                "auto",
                "--model",
                "large-v3",
            ],
            cwd=ROOT,
            env=env,
        )
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
