# scripts/promo

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Офлайн Python-пайплайн, превращающий сырые уроки `video-lessons/*.mp4` в короткие промо-ролики: извлечение аудио и транскрипция (faster-whisper) → подбор ярких фрагментов через LLM или эвристику → сборка `promo.mp4` (нарезки + crossfade + intro/outro-карточки через Pillow/ffmpeg) → опциональная загрузка в Kinescope → запись метаданных в [`program.json`](program.json) → опциональная синхронизация в БД. Работает независимо от backend-venv, своим `requirements.txt`.

## Key Files

| File | Description |
|------|-------------|
| [`transcribe.py`](transcribe.py) | `ffmpeg` извлекает mono 16kHz wav, `faster-whisper` (по умолчанию `large-v3`) транскрибирует, результат кешируется в `output/<slug>/transcript.json`, рядом пишутся `transcript_plain.txt` и `transcript_full_text.txt` |
| [`select_highlights.py`](select_highlights.py) | Подбор highlight-сегментов и title/description/bullets. Порядок провайдеров: OpenAI (`OPENAI_HIGHLIGHT_MODEL`, по умолчанию `gpt-5.4-mini`) → Gemini (`GEMINI_HIGHLIGHT_MODEL`, по умолчанию `gemini-3-flash`) → Anthropic (`claude-sonnet-4-20250514`); без ключей или при сбое — эвристика. Pydantic-модели `HighlightSegment`/`HighlightsPlan` |
| [`cut_video.py`](cut_video.py) | Склейка `promo.mp4`: нарезки + crossfade + Pillow-карточки intro/outro + `ffmpeg` |
| [`intro_image.py`](intro_image.py) | AI-фон intro-карточки: Gemini (`GEMINI_IMAGE_MODEL`) → OpenAI (`OPENAI_IMAGE_MODEL`) → Pillow-градиент; кеш `intro_bg.png`. Единая типографика и цвета бренда Lucy Nails заданы константами в файле; `frontend/src/app/globals.css` теперь на oklch, совпадает только `--text-primary` |
| [`catalog.py`](catalog.py) | `VIDEO_CATALOG` — сопоставление подстроки имени файла со slug/title/порядком модуля (порядок как в `frontend/src/lib/landing/course-content.ts`), плюс `DEFAULT_DESCRIPTIONS` |
| [`paths.py`](paths.py) | Единые пути: `repo_root`, `video_lessons_dir`, `output_dir`, `program_json_path`, `local_promos_collect_dir` (→ `promo-clips/`), `shared_promo_assets_dir` |
| [`generate_promos.py`](generate_promos.py) | Главный CLI, оркестрирует весь пайплайн. Флаги: `--only`, `--skip-upload`/`--local-only`, `--no-program-json`, `--collect-dir`, `--skip-cut`, `--skip-transcribe`, `--model`, `--device` (`auto` по умолчанию, `cpu`, `cuda`), `--regen-intro` |
| [`rebuild_from_segments.py`](rebuild_from_segments.py) | Локальный пересбор `promo.mp4` из уже сохранённых сегментов в `program.json`, без повторной транскрипции; аргументы — список slug (по умолчанию `folga`), `--regen-intro`; результат копируется в `promo-clips/` |
| [`run_remaining_promos.py`](run_remaining_promos.py) | Пакетный прогон `generate_promos.py --local-only` по фиксированному списку модулей (NFC-эскейпнутые подстроки `--only`) |
| [`export_transcript_plain.py`](export_transcript_plain.py) | Из кешированного `transcript.json` делает `transcript_plain.txt` / `transcript_full_text.txt` (последний — источник истины для аудита копии лендинга) |
| [`sync_program_to_db.py`](sync_program_to_db.py) | UPDATE-only заливка promo-полей из `program.json` в таблицу `lessons` (без truncate): урок с `order_index = 1` модуля, у которого совпал `title`. Те же переменные, что у backend (`DATABASE_URL` или `POSTGRES_*`) |
| [`upload_kinescope.py`](upload_kinescope.py) | Один POST в Kinescope uploader v2 (`uploader.kinescope.io/v2/video`); возвращает `id`/`poster`/`title` |
| [`program.json`](program.json) | Метаданные по модулям: `slug`, `title`, `order`, `source_file`, `duration_seconds`, `promo` (`kinescope_id`, `poster`, `description`, `bullets`, `highlight_segments`). Сейчас `kinescope_id` и `poster` равны `null` у всех 11 модулей |
| [`requirements.txt`](requirements.txt) | Зависимости только пайплайна (`faster-whisper`, `httpx`, `anthropic`, `openai`, `google-genai`, `pillow`, `psycopg2-binary`, `tenacity`, `pydantic`, `python-dotenv`) — отдельно от backend venv |
| [`README.md`](README.md) | Полная пошаговая инструкция (Windows), флаги, режим «только файлы на диске» без Postgres/Kinescope. Из LLM-ключей описывает только `ANTHROPIC_API_KEY`; остальные — в docstring `generate_promos.py` и ниже |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `output/` | Генерируемые по-модульно артефакты (`audio_16k.wav`, `transcript.json`, `transcript_plain.txt`, `transcript_full_text.txt`, `highlights.json`, `intro_bg.png`, `promo.mp4`, `clips_tmp/`, `_shared/`) — исключены из Git (`scripts/promo/output/` в корневом `.gitignore` и `output/` в локальном), пересоздаются пайплайном |

## For AI Agents

### Working In This Directory

- Запуск из корня репозитория со своим venv/зависимостями: `pip install -r scripts/promo/requirements.txt`; нужен `ffmpeg` в `PATH`.
- Ключи — в корневом `.env`: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`/`GOOGLE_API_KEY` опциональны (без них — эвристика вместо LLM для хайлайтов и Pillow-фолбэк для intro); `KINESCOPE_API_KEY` + `KINESCOPE_PROJECT_ID` обязательны только для загрузки в облако.
- `.env` подгружается через `load_dotenv` без override: сначала корневой, затем `backend/.env`, поэтому значение из корневого файла выигрывает. У backend `Settings` приоритет обратный.
- Первый запуск скачивает модель Whisper `large-v3` (несколько ГБ, нужен интернет).
- `--local-only`/`--skip-upload` — режим без загрузки в Kinescope и без БД. Сеть всё равно нужна для первой загрузки модели Whisper и для LLM/image-API, если заданы ключи.
- Готовые ролики копируются в `promo-clips/` (корень репозитория, тоже gitignored) или в `--collect-dir` при любом запуске с нарезкой.
- Запуск без загрузки или с неудачной загрузкой перезаписывает запись модуля в `program.json` целиком, включая `kinescope_id` и `poster` = `null`. Чтобы сохранить файл, добавлять `--no-program-json`.
- `program.json` — источник истины по promo-полям до синхронизации в БД; название модуля (`title`) должно совпадать с записью в БД для `sync_program_to_db.py`. `catalog.py` и `program.json` содержат `Стразы/объемные украшения`, а [`sync_lessons_content.py`](../../backend/scripts/sync_lessons_content.py) переименовывает этот модуль в БД в `Стразы и объёмный декор`; такой модуль синхронизация пропустит без предупреждения.

### Testing Requirements

- Автотестов нет; проверка — фактический прогон на одном уроке (`generate_promos.py --only <ключевое слово> --skip-upload`) и просмотр `output/<slug>/promo.mp4`.
- При изменении `select_highlights.py`/`cut_video.py` использовать `--skip-transcribe` на уже готовом `transcript.json`, чтобы не гонять Whisper заново.

### Common Patterns

- Модули — docstring на русском сверху файла, `from __future__ import annotations`, импорты `from scripts.promo...`; точки входа добавляют корень репо в `sys.path` (`Path(__file__).resolve().parents[2]`).
- Пути — через [`paths.py`](paths.py), не хардкодить.
- CLI с флагами (`generate_promos.py`, `rebuild_from_segments.py`) — `argparse`; `sync_program_to_db.py`, `export_transcript_plain.py`, `run_remaining_promos.py` аргументов не принимают. Пример команды и env-переменные — в docstring модуля.

## Dependencies

### Internal

- `video-lessons/*.mp4` (исходники, gitignored)
- [`program.json`](program.json) ↔ таблица `lessons` в БД (через `sync_program_to_db.py` или `backend/scripts/seed_data.py`)
- `frontend/src/lib/landing/course-content.ts` — порядок модулей, на который ориентируется [`catalog.py`](catalog.py) (комментарий в `catalog.py` всё ещё ссылается на `page.tsx`)
- [`backend/app/core/config.py`](../../backend/app/core/config.py) — те же имена переменных (`DATABASE_URL`, `POSTGRES_*`), но другой приоритет `.env`-файлов

### External

- `ffmpeg` (в `PATH`), `faster-whisper`, `httpx`, `anthropic`/`openai`/`google-genai` (опционально), `pillow`, `psycopg2-binary`, `tenacity`, `pydantic`, `python-dotenv`
- Kinescope uploader API (`uploader.kinescope.io`, `api.kinescope.io`)

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
