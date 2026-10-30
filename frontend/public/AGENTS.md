# public

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Статические ассеты, отдаваемые Next.js напрямую по корневому пути (`/...`): фото работ для лендинга, галерея на главной, брендовые изображения инструктора, юридические документы и директория для пользовательских загрузок админки.

## Key Files

| File | Description |
|------|-------------|
| `icon.svg` | Иконка сайта: `metadata.icons` в `src/app/layout.tsx` |
| `yandex_408ae9938caf9983.html` | Подтверждение прав на `https://lucysmirnova.ru` в Яндекс Вебмастере. Не удалять и не менять: Вебмастер периодически перепроверяет файл |

Остальные файлы в корне (`favicon.ico`, `icon.png`, `hero-bg-fluid.png`, `Whisk_*.png`, `instructor-placeholder.svg`, `file.svg`, `globe.svg`, `next.svg`, `vercel.svg`, `window.svg`) из кода не используются.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `landing/` | Медиа лендинга: `instructor-master.webp` — фото инструктора и OG-картинка в `src/app/page.tsx`, если `landing_instructor_image_url` не задан |
| `legal/` | Юридические файлы: `offer-example.pdf`, `privacy-policy.docx`, `favicon-ls.ico`. Код на них не ссылается |
| `nails-gallery/` | 7 фото (`galleryItems`) и 4 SVG-заглушки (`fallbackGalleryImages`), списки — в `src/lib/landing/course-content.ts`. Фото показываются на лендинге только при отказе API и импортируются в БД кнопкой в `/admin/landing`; SVG код не импортирует |
| `uploads/` | Локальное хранилище загрузок админки (обложки курсов и т.п.): backend пишет сюда, только если `UPLOAD_STORAGE_DIR` пуст (`backend/app/core/uploads.py`). При заданной переменной (Railway Volume) файлы хранит и раздаёт backend по `/uploads`. Содержимое игнорируется Git (`uploads/.gitignore` держит только сам каталог) |
| `works/` | 11 категорий фото работ для карусели модулей программы: `aerografiya`, `akvarium`, `folga`, `french`, `gradient`, `pigmenty`, `slaidery`, `stemping`, `strazy`, `tekstury`, `vtirka`. Каждая пара `*-thumb.webp` / `*.webp` — путь регистрируется в `src/lib/landing/works-photos.ts` (auto-generated) |

## For AI Agents

### Working In This Directory

- `works/*` и `works-photos.ts` — сгенерированная пара: файл `src/lib/landing/works-photos.ts` помечен `AUTO-GENERATED — DO NOT EDIT` и должен ссылаться на реально существующие файлы здесь. Добавление/удаление фото вручную без обновления генератора (`scripts/works_photos/process.py`, вне зоны `frontend/`) рассинхронизирует список.
- `uploads/` — не коммитить содержимое (только `.gitignore` внутри). Файлы туда попадают через `adminUploadFile` (`src/lib/api.ts` → `POST /admin/upload`), когда backend работает без `UPLOAD_STORAGE_DIR`.
- Не путать `public/legal/*` (сырые юридические файлы) со страницами `/privacy` и `/terms` в `app/` — это разные вещи.

### Testing Requirements

Соответствие `works-photos.ts` файлам в `works/` тестами не проверяется: после перегенерации убедиться, что все пути существуют.

## Dependencies

### Internal

- `src/lib/landing/course-content.ts`, `src/lib/landing/works-photos.ts`, `src/app/page.tsx`, `src/app/layout.tsx` — потребители ассетов.
- `scripts/works_photos/process.py` — генератор `works/` и `works-photos.ts`; `backend/app/core/uploads.py` — выбор каталога загрузок.

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
