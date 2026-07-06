<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# scripts/promo

## Purpose

Офлайн Python-пайплайн, превращающий сырые уроки `video-lessons/*.mp4` в короткие промо-ролики: извлечение аудио и транскрипция (faster-whisper) → подбор ярких фрагментов через LLM или эвристику → сборка `promo.mp4` (нарезки + crossfade + intro/outro-карточки через Pillow/ffmpeg) → опциональная загрузка в Kinescope → запись метаданных в [`program.json`](program.json) → опциональная синхронизация в БД. Работает независимо от backend-venv, своим `requirements.txt`.

## Key Files

| File | Description |
|------|-------------|
| [`transcribe.py`](transcribe.py) | `ffmpeg` извлекает mono 16kHz wav, `faster-whisper` (по умолчанию `large-v3`) транскрибирует, результат кешируется в `output/<slug>/transcript.json` |
| [`select_highlights.py`](select_highlights.py) | Подбор highlight-сегментов и title/description/bullets через LLM (`gpt-5.4-mini`, `gemini-3-flash`) или эвристику без ключей; pydantic-модели `HighlightSegment`/`HighlightsPlan` |
| [`cut_video.py`](cut_video.py) | Склейка `promo.mp4`: нарезки + crossfade + Pillow-карточки intro/outro + `ffmpeg` |
| [`intro_image.py`](intro_image.py) | AI-фон intro-карточки (Gemini/OpenAI image-модели) с Pillow-фолбэком; единая типографика и цвета бренда Lucy Nails (сверены с `frontend/src/app/globals.css`) |
| [`catalog.py`](catalog.py) | `VIDEO_CATALOG` — сопоставление подстроки имени файла со slug/title/порядком модуля (порядок как в `frontend/src/app/page.tsx`) |
| [`paths.py`](paths.py) | Единые пути: `repo_root`, `video_lessons_dir`, `output_dir`, `program_json_path`, `local_promos_collect_dir` (→ `promo-clips/`), `shared_promo_assets_dir` |
| [`generate_promos.py`](generate_promos.py) | Главный CLI, оркестрирует весь пайплайн. Флаги: `--only`, `--skip-upload`/`--local-only`, `--no-program-json`, `--collect-dir`, `--skip-cut`, `--skip-transcribe`, `--device cuda` |
| [`rebuild_from_segments.py`](rebuild_from_segments.py) | Локальный пересбор `promo.mp4` из уже сохранённых сегментов в `program.json`, без повторной транскрипции |
| [`run_remaining_promos.py`](run_remaining_promos.py) | Пакетный прогон `generate_promos.py` по фиксированному списку модулей (NFC-эскейпнутые подстроки `--only`) |
| [`export_transcript_plain.py`](export_transcript_plain.py) | Из кешированного `transcript.json` делает `transcript_plain.txt` / `transcript_full_text.txt` (последний — источник истины для аудита копии лендинга) |
| [`sync_program_to_db.py`](sync_program_to_db.py) | UPDATE-only заливка promo-полей из `program.json` в таблицу `lessons` (без truncate); те же переменные, что у backend (`DATABASE_URL` или `POSTGRES_*`) |
| [`upload_kinescope.py`](upload_kinescope.py) | Один POST в Kinescope uploader v2 (`uploader.kinescope.io/v2/video`); возвращает `id`/`poster`/`title` |
| [`program.json`](program.json) | Метаданные по модулям: `source_file`, `duration_seconds`, `promo` (`kinescope_id`, `poster`, `description`, `bullets`, `highlight_segments`) |
| [`requirements.txt`](requirements.txt) | Зависимости только пайплайна (`faster-whisper`, `httpx`, `anthropic`, `openai`, `google-genai`, `pillow`, `psycopg2-binary`, `tenacity`, `pydantic`, `python-dotenv`) — отдельно от backend venv |
| [`README.md`](README.md) | Полная пошаговая инструкция (Windows), переменные окружения, флаги, режим «только файлы на диске» без Postgres/Kinescope |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `output/` | Генерируемые по-модульно артефакты (`transcript.json`, `highlights.json`, `promo.mp4`, `clips_tmp/`, `_shared/`) — исключены из Git (`scripts/promo/output/` в `.gitignore`), пересоздаются пайплайном |

## For AI Agents

### Working In This Directory

- Запуск из корня репозитория со своим venv/зависимостями: `pip install -r scripts/promo/requirements.txt`; нужен `ffmpeg` в `PATH`.
- Ключи — в корневом `.env`: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`/`GOOGLE_API_KEY` опциональны (без них — эвристика вместо LLM для хайлайтов и Pillow-фолбэк для intro); `KINESCOPE_API_KEY` + `KINESCOPE_PROJECT_ID` обязательны только для загрузки в облако.
- Первый запуск скачивает модель Whisper `large-v3` (несколько ГБ, нужен интернет).
- `--local-only`/`--skip-upload` — безопасный режим без сети и без БД: готовые ролики копируются в `promo-clips/` (корень репозитория, тоже gitignored).
- `program.json` — источник истины по promo-полям до синхронизации в БД; название модуля (`title`) должно совпадать с записью в БД для `sync_program_to_db.py`.

### Testing Requirements

- Автотестов нет; проверка — фактический прогон на одном уроке (`generate_promos.py --only <ключевое слово> --skip-upload`) и просмотр `output/<slug>/promo.mp4`.
- При изменении `select_highlights.py`/`cut_video.py` использовать `--skip-transcribe` на уже готовом `transcript.json`, чтобы не гонять Whisper заново.

### Common Patterns

- Каждый модуль — docstring на русском в одну строку сверху файла, `from __future__ import annotations`, ручное добавление корня репо в `sys.path` (`Path(__file__).resolve().parents[2]`).
- Пути — только через [`paths.py`](paths.py), не хардкодить.
- CLI-скрипты — `argparse` + docstring модуля с примером команды и списком нужных env-переменных.

## Dependencies

### Internal

- `video-lessons/*.mp4` (исходники, gitignored)
- [`program.json`](program.json) ↔ таблица `lessons` в БД (через `sync_program_to_db.py` или `backend/scripts/seed_data.py`)
- `frontend/src/app/page.tsx` — порядок/названия модулей, на которые ориентируется [`catalog.py`](catalog.py)
- `frontend/src/app/globals.css` — цветовая палитра, на которую ориентируется [`intro_image.py`](intro_image.py)
- [`backend/app/core/config.py`](../../backend/app/core/config.py) — та же конвенция чтения `.env`/`DATABASE_URL`

### External

- `ffmpeg` (в `PATH`), `faster-whisper`, `httpx`, `anthropic`/`openai`/`google-genai` (опционально), `pillow`, `psycopg2-binary`, `tenacity`, `pydantic`, `python-dotenv`
- Kinescope uploader API (`uploader.kinescope.io`, `api.kinescope.io`)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
