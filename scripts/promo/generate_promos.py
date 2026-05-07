#!/usr/bin/env python3
"""
Генерация промо-роликов из video-lessons/ и обновление scripts/promo/program.json.

Пример:
  pip install -r scripts/promo/requirements.txt
  python scripts/promo/generate_promos.py --only пигмент --skip-upload

Только локальные файлы (без Kinescope и без БД): готовые ролики копируются в папку
`promo-clips/` в корне репозитория (`01-folga-promo.mp4`, …).

Переменные окружения (корневой `.env`):
  OPENAI_API_KEY — выбор highlight-сегментов (gpt-5.4-mini) и/или gpt-image-2 для intro
  GEMINI_API_KEY или GOOGLE_API_KEY — Gemini highlight / Nano Banana Pro для фона intro
  ANTHROPIC_API_KEY — запасной провайдер для хайлайтов
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import unicodedata
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Корень репозитория на PYTHONPATH
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.promo.catalog import DEFAULT_DESCRIPTIONS, find_catalog_entry
from scripts.promo.cut_video import build_promo_video
from scripts.promo.paths import (
    local_promos_collect_dir,
    output_dir,
    program_json_path,
    video_lessons_dir,
)
from scripts.promo.select_highlights import HighlightsPlan, select_highlights
from scripts.promo.transcribe import transcribe_video
from scripts.promo.upload_kinescope import upload_video_file


def load_program() -> dict:
    path = program_json_path()
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": 1, "modules": []}


def save_program(data: dict) -> None:
    path = program_json_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_module(program: dict, entry: dict) -> None:
    mods = program.setdefault("modules", [])
    slug = entry["slug"]
    for i, m in enumerate(mods):
        if m.get("slug") == slug:
            mods[i] = entry
            return
    mods.append(entry)
    mods.sort(key=lambda x: x.get("order", 999))


def enrich_plan_defaults(plan: HighlightsPlan, slug: str) -> HighlightsPlan:
    desc, bullets = DEFAULT_DESCRIPTIONS.get(
        slug,
        ("Ключевые приёмы и практические советы из урока.", ["Техника", "Материалы", "Финиш"]),
    )
    if not plan.description.strip():
        plan = plan.model_copy(update={"description": desc})
    if not plan.bullets:
        plan = plan.model_copy(update={"bullets": list(bullets)})
    return plan


def resolve_whisper_device(device_arg: str) -> tuple[str, str]:
    """Возвращает (device, compute_type) для faster-whisper."""
    if device_arg == "auto":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                logger.info("Whisper: device=cuda compute_type=float16")
                return "cuda", "float16"
        except Exception as e:
            logger.warning("Whisper auto-detect GPU failed: %s — используем CPU", e)
        logger.info("Whisper: device=cpu compute_type=int8")
        return "cpu", "int8"
    if device_arg == "cuda":
        return "cuda", "float16"
    return "cpu", "int8"


def main() -> int:
    parser = argparse.ArgumentParser(description="Генерация промо для видео-уроков")
    parser.add_argument("--only", help="Подстрока имени файла (например пигмент)")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="То же что --skip-upload: только нарезка и файлы на диске (promo-clips/, program.json).",
    )
    parser.add_argument(
        "--no-program-json",
        action="store_true",
        help="Не обновлять scripts/promo/program.json (только transcript/highlights/promo.mp4 и promo-clips).",
    )
    parser.add_argument(
        "--collect-dir",
        type=str,
        default="",
        help="Куда копировать готовые промо (по умолчанию promo-clips/ в корне репозитория).",
    )
    parser.add_argument("--skip-cut", action="store_true")
    parser.add_argument("--skip-transcribe", action="store_true", help="Использовать только кеш transcript.json")
    parser.add_argument("--model", default="large-v3", help="Модель faster-whisper")
    parser.add_argument(
        "--device",
        default="auto",
        help="cpu, cuda или auto (CUDA через ctranslate2 при наличии GPU)",
    )
    parser.add_argument(
        "--regen-intro",
        action="store_true",
        help="Перегенерировать AI-фон intro_bg.png (игнорировать кеш)",
    )
    args = parser.parse_args()

    if args.local_only:
        args.skip_upload = True

    collect_root = Path(args.collect_dir).expanduser() if args.collect_dir else local_promos_collect_dir()

    load_dotenv(_ROOT / ".env")
    load_dotenv(_ROOT / "backend" / ".env")

    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    vdir = video_lessons_dir()
    if not vdir.is_dir():
        print(f"Нет каталога {vdir}", file=sys.stderr)
        return 1

    mp4s = sorted(vdir.glob("*.mp4"))
    if args.only:
        key = unicodedata.normalize("NFC", args.only.lower())
        mp4s = [
            p for p in mp4s if key in unicodedata.normalize("NFC", p.name.lower())
        ]

    if not mp4s:
        print("Не найдено ни одного подходящего .mp4", file=sys.stderr)
        return 1

    program = load_program() if not args.no_program_json else None

    w_device, w_compute = resolve_whisper_device(args.device)

    for video_path in mp4s:
        entry_meta = find_catalog_entry(video_path.name)
        if not entry_meta:
            print(f"Пропуск (нет в каталоге): {video_path.name}")
            continue

        slug = entry_meta.slug
        work = output_dir() / slug
        work.mkdir(parents=True, exist_ok=True)

        transcript_path = work / "transcript.json"
        if args.skip_transcribe and transcript_path.is_file():
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        else:
            print(f"Транскрибация: {video_path.name} …")
            try:
                transcript = transcribe_video(
                    video_path,
                    work,
                    model_size=args.model,
                    device=w_device,
                    compute_type=w_compute,
                )
            except RuntimeError as e:
                err = str(e).lower()
                if w_device == "cuda" and (
                    "cublas" in err or "cuda" in err or "dll" in err or "nvidia" in err
                ):
                    logger.warning(
                        "Whisper CUDA недоступен (%s), повтор на CPU int8",
                        e,
                    )
                    transcript = transcribe_video(
                        video_path,
                        work,
                        model_size=args.model,
                        device="cpu",
                        compute_type="int8",
                    )
                else:
                    raise

        prefer_llm = True
        duration_cap = float(transcript.get("duration_seconds") or 36000)
        plan = select_highlights(
            entry_meta.title,
            transcript,
            duration_cap,
            prefer_llm=prefer_llm,
        )
        plan = enrich_plan_defaults(plan, slug)

        highlights_path = work / "highlights.json"
        highlights_path.write_text(
            json.dumps(json.loads(plan.model_dump_json()), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        promo_file = work / "promo.mp4"
        if not args.skip_cut:
            segs = [(h.start_sec, h.end_sec) for h in plan.highlights]
            if not segs:
                print(f"Нет сегментов для {slug}", file=sys.stderr)
                continue
            tmp_clips = work / "clips_tmp"
            print(f"Сборка промо: {slug} …")
            build_promo_video(
                video_path,
                segs,
                entry_meta.title,
                promo_file,
                tmp_clips,
                slug=slug,
                lesson_order=entry_meta.order,
                intro_cache_dir=work,
                regen_intro_bg=args.regen_intro,
            )

            collect_root.mkdir(parents=True, exist_ok=True)
            dest_name = f"{entry_meta.order:02d}-{slug}-promo.mp4"
            dest_path = collect_root / dest_name
            shutil.copy2(promo_file, dest_path)
            print(f"Готово в общую папку: {dest_path}")

        uploaded_id = None
        poster = None
        if not args.skip_upload and promo_file.is_file():
            try:
                print(f"Загрузка в Kinescope: {slug} …")
                up = upload_video_file(
                    promo_file,
                    title=f"Промо: {entry_meta.title}",
                    description=plan.description[:1800],
                )
                uploaded_id = up["id"]
                poster = up["poster"]
            except Exception as e:
                print(f"Загрузка не удалась ({slug}): {e}", file=sys.stderr)

        promo_payload = {
            "kinescope_id": uploaded_id,
            "poster": poster,
            "description": plan.description,
            "bullets": plan.bullets,
            "highlight_segments": [
                {"start_sec": h.start_sec, "end_sec": h.end_sec, "reason": h.reason}
                for h in plan.highlights
            ],
        }

        if program is not None:
            upsert_module(
                program,
                {
                    "slug": slug,
                    "title": entry_meta.title,
                    "order": entry_meta.order,
                    "source_file": video_path.name,
                    "duration_seconds": int(duration_cap),
                    "promo": promo_payload,
                },
            )
            save_program(program)
            print(f"OK: {slug} -> program.json обновлен")
        else:
            print(f"OK: {slug} (program.json не трогали)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
