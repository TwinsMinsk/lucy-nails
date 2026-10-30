# public

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Статические ассеты, отдаваемые Next.js напрямую по корневому пути (`/...`): фото работ для лендинга, галерея на главной, брендовые изображения инструктора, юридические документы и директория для пользовательских загрузок админки (в локальной разработке).

## Key Files

| File | Description |
|------|-------------|
| `icon.svg` | Иконка сайта — подключена в `metadata.icons` корневого `src/app/layout.tsx` |
| `favicon.ico`, `icon.png` | Альтернативные иконки, в `src/` не ссылаются. `favicon.ico` дублирует metadata-файл `src/app/favicon.ico`, который App Router тоже отдаёт как `/favicon.ico` |
| `hero-bg-fluid.png`, `instructor-placeholder.svg`, `Whisk_*.png` | Дизайн-ассеты, на которые сейчас нет ссылок в `src/` |
| `file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg` | Остатки шаблона `create-next-app`, в коде не используются |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `landing/` | Медиа лендинга (например `instructor-master.webp`) |
| `legal/` | Юридические файлы: `offer-example.pdf`, `privacy-policy.docx`, `favicon-ls.ico` (из `src/` на них сейчас нет ссылок) |
| `nails-gallery/` | 7 фото (`SnapInsta.to_*.jpg`, статический `galleryItems`) + SVG-фолбэки `design-1..4.svg` (`fallbackGalleryImages`) для секции "Галерея работ" на главной (`src/lib/landing/course-content.ts`); используются, если галерея из API пуста |
| `uploads/` | Каталог загрузок из админки по умолчанию: backend (`backend/app/api/upload.py`) пишет сюда, только если не задан `UPLOAD_STORAGE_DIR`. В production файлы лежат в `UPLOAD_STORAGE_DIR` (Railway Volume) и раздаются backend-ом по `/uploads` (`api.lucysmirnova.ru/uploads/**` в `images.remotePatterns`). Содержимое игнорируется Git (`uploads/.gitignore` держит только сам каталог) |
| `works/` | 11 категорий фото работ для карусели модулей программы: `aerografiya`, `akvarium`, `folga`, `french`, `gradient`, `pigmenty`, `slaidery`, `stemping`, `strazy`, `tekstury`, `vtirka` (`gradient` и `aerografiya` добавлены 2026-07-06). Каждая пара `*-thumb.webp` / `*.webp` (сейчас 153 пары) регистрируется в `src/lib/landing/works-photos.ts` (auto-generated) |

## For AI Agents

### Working In This Directory

- `works/*` и `works-photos.ts` — сгенерированная пара: файл `src/lib/landing/works-photos.ts` помечен `AUTO-GENERATED — DO NOT EDIT` и должен ссылаться на реально существующие файлы здесь. Добавление/удаление фото вручную без обновления генератора (`scripts/works_photos/process.py`, вне зоны `frontend/`) рассинхронизирует список.
- `uploads/` — не коммитить содержимое (только `.gitignore` внутри). Файлы туда попадают через `adminUploadFile` (`src/lib/api.ts` → `POST /admin/upload`), и то лишь при пустом `UPLOAD_STORAGE_DIR` на backend.
- Новые картинки здесь отдаются same-origin и CSP не требуют; внешние URL картинок для `next/image` должны попадать в `images.remotePatterns` (`frontend/next.config.ts`).
- Не путать `public/legal/*` (сырые юридические файлы) со страницами `/privacy` и `/terms` в `app/` — это разные вещи.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
