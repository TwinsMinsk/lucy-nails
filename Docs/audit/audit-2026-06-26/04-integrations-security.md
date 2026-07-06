# 04 — Интеграции и безопасность

Дата: 2026-06-26. Секреты в отчёте не раскрываются — только `file:line` и характер.

## Кластер «закоммиченные креды + auto-seed» (главный риск)

Три связанных пункта дают на выходе **рабочие учётки в любом non-prod окружении**:

### SEC-01 — `test-login.txt` в корне: плейнтекст-учётки, закоммичены · HIGH · поведение не меняется
- Файл `test-login.txt:1-5` содержит логины и пароли админа и студента открытым текстом.
- **Отслеживается в HEAD и присутствует в истории** (`git ls-tree -r HEAD`, первый коммит `084e40a "Initial commit for Railway deploy"`). НЕ gitignored.
- Те же пароли зашиты в seed (`main.py:83-84`), т.е. это **действующие** учётки для dev/staging.
- Исправление: `git rm test-login.txt`; считать пароли скомпрометированными; не хранить креды в репо. (Опц.: переписать историю — отдельное решение.)

### SEC-02 — `backend/test_courses.py`: хардкод пароля БД + деструктивный апдейт · HIGH · поведение не меняется (файл не импортируется)
- `test_courses.py:4-6` — `psycopg2.connect(... password=<plaintext>)` (значение не цитирую). Отслеживается в HEAD (коммит `058c9ac`).
- Дополнительно скрипт выполняет `UPDATE courses SET price_self=5900, price_support=11900` + `commit` (`:18-20`) — деструктивный one-off, опасный при случайном запуске.
- Исправление: удалить файл; **ротировать пароль БД**, если он используется где-либо ещё.

### SEC-03 — Seed известных слабых паролей в non-prod · MED · меняет поведение
- `main.py:79-101`: при `ENVIRONMENT != production` создаёт/обновляет `admin@nails-course.ru` (`admin123`) и `student@test.ru` (`student123`).
- Гард корректен (в production seed не выполняется) — поэтому это **MED, а не CRITICAL**. Но любой доступный из сети staging получает известные учётки.
- Исправление: брать пароли из env или генерировать случайные с разовым логом; сузить гард до `ENVIRONMENT == "development"` (исключить staging). **Меняет поведение** (другие пароли).

## Прочая security-гигиена

### SEC-04 — Утечка деталей исключения клиенту · LOW · поведение почти не меняется
- `upload.py:85-89`: `detail=f"Failed to save file: {str(e)}"` возвращает внутреннюю ошибку наружу. Логировать детально, отдавать обобщённый текст.

### CONF-02 — CORS: `allow_methods=["*"]`, `allow_headers=["*"]` с credentials · LOW · поведение не меняется
- `main.py:132-138`. **Важно:** origins НЕ wildcard — это явный allowlist (`_cors_allow_origins()` → `CORS_ORIGINS` или `FRONTEND_URL`, `main.py:29-33`). Поэтому риск низкий; методы/заголовки стоит сузить до явных списков. Предварительная оценка «широкий открытый CORS» — **переоценена**.

### INTEG-01 — Demo-подпись Prodamus принимается в production · MED · меняет поведение (требует продуктового решения)
- `prodamus_service.py:115-137`: `verify_signature` сначала проверяет стандартную подпись (`:128-130`), затем — demo-подпись `secret + "demo"` (`:134-137`). Ветка demo **не загейчена** ни на `ENVIRONMENT`, ни на `PRODAMUS_DEMO_MODE` — принимается всегда, включая prod.
- Контекст: фича «тестовые платежи на live-деплое» (`PRODAMUS_DEMO_MODE`, коммит `09eb605`). Сторона, знающая секрет, может прислать demo-подписанный вебхук на prod. Смягчение: сумма (±2 коп.) и валюта всё равно сверяются (`payments.py:252,261`) → **не CRITICAL**.
- Исправление (если не задумано): принимать demo-подпись только при `PRODAMUS_DEMO_MODE` или non-prod. **Меняет поведение** — сперва подтвердить намерение с владельцем продукта.

## Что сделано хорошо (подтверждено)
- **Production-safety fail-fast** (`config.py:129-160`): валит старт при DEBUG, дефолтном `JWT_SECRET_KEY`, отсутствии Kinescope/Prodamus-ключей, localhost в URL, пустом `TRUSTED_HOSTS`.
- **CSRF** double-submit, активен только при наличии auth-cookie, корректно исключает auth-эндпоинты (`main.py:45-74`).
- **SecurityHeaders** (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`) — `main.py:36-42`.
- **Prodamus webhook**: подпись + идемпотентность + сверка суммы/валюты (см. [02-backend.md](02-backend.md)).
- **Kinescope**: таймауты на всех HTTP, DRM-JWT (RS256, TTL 300s), watermark с email — секреты не логируются.
- Docs (`payments.py`/`kinescope`) реализуют DRM/idempotency согласно skill-знаниям `prodamus`/`kinescope`.

## Гигиена секретов в Git — чисто
- Закоммичены только шаблоны: `.env.example`, `frontend/.env.example` (`git ls-files "*.env*"`).
- `.env`, `backend/.env`, `frontend/.env.local` — игнорируются (`git check-ignore` подтверждает); `.pem` в `.gitignore`.
- Исключение из чистоты — `test-login.txt` и `test_courses.py` выше (это не `.env`, поэтому проскочили мимо ignore-правил).
