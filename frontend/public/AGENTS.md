<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# public

## Purpose

Статические ассеты, отдаваемые Next.js напрямую по корневому пути (`/...`): фото работ для лендинга, галерея на главной, брендовые изображения инструктора, юридические документы и директория для пользовательских загрузок админки.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `landing/` | Медиа лендинга (например `instructor-master.webp`) |
| `legal/` | Юридические файлы: `offer-example.pdf`, `privacy-policy.docx`, `favicon-ls.ico` |
| `nails-gallery/` | Фото + SVG-фолбэки для секции "Галерея работ" на главной (`src/lib/landing/course-content.ts`) |
| `uploads/` | Runtime-загрузки из админки (обложки курсов и т.п.); содержимое игнорируется Git (`uploads/.gitignore` держит только сам каталог) |
| `works/` | 11 категорий фото работ для карусели модулей программы: `aerografiya`, `akvarium`, `folga`, `french`, `gradient`, `pigmenty`, `slaidery`, `stemping`, `strazy`, `tekstury`, `vtirka`. Каждая пара `*-thumb.webp` / `*.webp` — путь регистрируется в `src/lib/landing/works-photos.ts` (auto-generated) |

## For AI Agents

### Working In This Directory

- `works/*` и `works-photos.ts` — сгенерированная пара: файл `src/lib/landing/works-photos.ts` помечен `AUTO-GENERATED — DO NOT EDIT` и должен ссылаться на реально существующие файлы здесь. Добавление/удаление фото вручную без обновления генератора (`scripts/works_photos/process.py`, вне зоны `frontend/`) рассинхронизирует список.
- `uploads/` — не коммитить содержимое (только `.gitignore` внутри). Файлы туда попадают через `adminUploadFile` (`src/lib/api.ts` → `POST /admin/upload`).
- Не путать `public/legal/*` (сырые юридические файлы) со страницами `/privacy` и `/terms` в `app/` — это разные вещи.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
