# Пайплайн промо-роликов

Офлайн-скрипты для нарезки коротких превью из `video-lessons/*.mp4`, загрузки в Kinescope и заполнения [`program.json`](program.json).

## Требования

- Python 3.11+
- `ffmpeg` в `PATH`
- Зависимости: `pip install -r scripts/promo/requirements.txt`
- Переменные в корневом `.env`:
  - `ANTHROPIC_API_KEY` — выбор фрагментов и тексты (опционально; без ключа — эвристика)
  - `KINESCOPE_API_KEY`, `KINESCOPE_PROJECT_ID` — загрузка промо в Kinescope

## Команды

Из корня репозитория:

```powershell
pip install -r scripts/promo/requirements.txt
python scripts/promo/generate_promos.py --only пигмент --skip-upload
```

Флаги:

- `--skip-upload` / **`--local-only`** — не загружать в Kinescope; готовые mp4 дублируются в **`promo-clips/`**
- `--no-program-json` — не менять `scripts/promo/program.json`
- **`--collect-dir ПУТЬ`** — другая папка для итоговых промо вместо `promo-clips/`
- `--skip-cut` — не собирать `promo.mp4` (если нужен только транскрипт/LLM)
- `--skip-transcribe` — взять готовый `scripts/promo/output/<slug>/transcript.json`
- `--device cuda` — GPU для Whisper (если доступна)

Артефакты: `scripts/promo/output/<slug>/` — `transcript.json`, `highlights.json`, `promo.mp4`; копия финала — **`promo-clips/NN-slug-promo.mp4`** (корень репозитория).

После успешной загрузки в Kinescope обновляется [`program.json`](program.json). Для сайта через API затем миграции БД и при необходимости [`sync_program_to_db.py`](sync_program_to_db.py) или полный [`seed_data.py`](../../backend/scripts/seed_data.py).

## Режим «только файлы на диске» (без PostgreSQL и без Kinescope)

База данных для нарезки **не нужна**. Достаточно исходников в `video-lessons/` и установленных зависимостей.

После успешной сборки каждого ролика файл копируется в **`promo-clips/`** в корне репозитория с именем вида  
`01-folga-promo.mp4`, `06-pigmenty-promo.mp4` (порядок и slug из каталога).

```powershell
pip install -r scripts\promo\requirements.txt
python scripts\promo\generate_promos.py --local-only
```

Один урок для проверки:

```powershell
python scripts\promo\generate_promos.py --local-only --only пигмент
```

- Промежуточные артефакты остаются в `scripts/promo/output/<slug>/` (транскрипт, нарезки).
- По умолчанию обновляется `scripts/promo/program.json` (тексты для будущей интеграции). Полностью без JSON:  
  `--no-program-json`
- Другая папка для итоговых mp4:  
  `--collect-dir D:\Exports\promos`

### Потом выложить на главную

Когда будете готовы: либо загрузить ролики в Kinescope и подставить id в БД / `sync_program_to_db.py`, либо положить файлы в `frontend/public/...` и подключить обычный `<video>` или плеер — это отдельный шаг.

---

## Постер по умолчанию

Если API не вернул URL постера, используется шаблон `https://kinescope.io/{video_id}/poster.jpg`.

---

## Пошагово: от видео до главной страницы (Windows)

Ниже три независимые части: **БД**, **нарезка промо**, **показ на сайте**.

### 1. Исправить `.env` и поднять Postgres

- В **корне репозитория** файл `.env` должен содержать **одну строку** без переносов и без лишних символов (ошибка `Could not parse SQLAlchemy URL` часто из‑за битой строки или `}` в значении):

  ```env
  DATABASE_URL=postgresql+asyncpg://postgres:ВАШ_ПАРОЛЬ@localhost:5432/nails_course
  ```

- Запустите службу PostgreSQL (локально или Docker). Проверка: `Test-NetConnection localhost -Port 5432`.

### 2. Миграции (колонки промо в таблице `lessons`)

Из каталога **`backend`** (PowerShell):

```powershell
cd C:\Projects\Oleg\Lucy-nails\backend
$env:PYTHONPATH = "."
$env:ENVIRONMENT = "development"
alembic upgrade head
```

Если команда не находит `alembic`, используйте тот же Python, где установлен backend:  
`python -m alembic upgrade head`.

### 3. Данные курса в БД

**Вариант А — полный сид (очищает таблицы и заново создаёт курс и модули):**

```powershell
cd C:\Projects\Oleg\Lucy-nails
$env:PYTHONPATH = "backend"
python backend\scripts\seed_data.py
```

Перед этим задайте в `.env` или в сессии: `POSTGRES_PASSWORD`, при необходимости `POSTGRES_HOST`, `POSTGRES_DB`, как в [`backend/scripts/seed_data.py`](../backend/scripts/seed_data.py).

**Вариант Б — у вас уже есть курс и модули:** после генерации промо выполните только синхронизацию JSON → БД:

```powershell
cd C:\Projects\Oleg\Lucy-nails
python scripts\promo\sync_program_to_db.py
```

Названия модулей в БД должны совпадать с полем `"title"` в [`program.json`](program.json) (например «Пигменты»).

### 4. Установить инструменты пайплайна

```powershell
pip install -r scripts\promo\requirements.txt
ffmpeg -version
```

Первый запуск Whisper скачает модель **large-v3** (несколько ГБ) — нужен интернет и время.

### 5. Ключи в `.env` (корень репозитория)

```env
ANTHROPIC_API_KEY=...          # умный выбор фрагментов и тексты (можно не задавать — будет простая эвристика)
KINESCOPE_API_KEY=...
KINESCOPE_PROJECT_ID=...       # UUID проекта/папки в Kinescope (обязателен для загрузки)
```

### 6. Сгенерировать промо для одного урока (проверка без загрузки в облако)

```powershell
cd C:\Projects\Oleg\Lucy-nails
python scripts\promo\generate_promos.py --only пигмент --skip-upload
```

Результат:

- `scripts/promo/output/pigmenty/` — `transcript.json`, `highlights.json`, `promo.mp4`
- обновится [`program.json`](program.json)

Флаг `--skip-upload` — только локальные файлы, без Kinescope.

### 7. Загрузить промо в Kinescope и обновить сайт

Уберите `--skip-upload` (или запустите без него для нужных файлов):

```powershell
python scripts\promo\generate_promos.py --only пигмент
```

После успешной загрузки в [`program.json`](program.json) появятся `kinescope_id` и `poster`. Затем:

```powershell
python scripts\promo\sync_program_to_db.py
```

Перезапуск backend не обязателен; главная подтягивает данные через API при следующем запросе (кеш revalidate ~2 мин).

### 8. Как главная показывает промо

Страница вызывает `GET /api/courses` → первый курс → `GET /api/courses/{id}/modules`.  
У каждого урока в ответе поля `promo_kinescope_video_id`, `promo_poster_url`, `promo_description`, `promo_bullets`. Без БД и синхронизации блок «Программа» показывает статический текст из лендинга.

### Что я сделал за вас в этой среде

- Запуск **миграции** здесь невозможен без работающего PostgreSQL на `localhost:5432` и корректного `DATABASE_URL`.
- Зависимости пайплайна можно установить командой из п. 4 (при необходимости дождитесь окончания `pip install`).
- Добавлен скрипт **`scripts/promo/sync_program_to_db.py`** — чтобы не обязательно гонять полный `seed_data.py` после каждой генерации промо.

