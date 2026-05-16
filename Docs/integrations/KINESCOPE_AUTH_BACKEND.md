# Kinescope DRM Authorization Backend

> Как мы технически защищаем платные видеоуроки в Lucy-nails.
> Связанные файлы: [`backend/app/services/kinescope_jwt_service.py`](../../backend/app/services/kinescope_jwt_service.py), [`backend/app/api/integrations/kinescope.py`](../../backend/app/api/integrations/kinescope.py), [`backend/app/services/kinescope_service.py`](../../backend/app/services/kinescope_service.py), [`scripts/kinescope/setup_drm.py`](../../scripts/kinescope/setup_drm.py).
> Документация Kinescope: [`Docs/integrations/KINESCOPE_API.md`](./KINESCOPE_API.md).

## Зачем это

Простого `<iframe>` Kinescope недостаточно: ссылку на embed можно скопировать
и открыть на чужом устройстве. Чтобы доступ был **только у оплатившего**
пользователя, мы используем штатный механизм Kinescope:

- **DRM** (Widevine / FairPlay / PlayReady) — Kinescope шифрует поток.
  Для воспроизведения плеер должен получить ключ дешифровки **через нас**.
- **Authorization Backend** — Kinescope, прежде чем отдать ключ, дёргает наш
  webhook и спрашивает «можно ли этому юзеру смотреть это видео?».
- **JWT (RS256) в `?drmauthtoken=`** — мы кладём в URL плеера
  короткоживущий токен с `user_id`/`lesson_id`. Kinescope передаёт его в
  webhook без изменений; мы верифицируем подпись своим публичным JWK,
  который заранее загрузили в Kinescope.
- **Динамический watermark** — поверх видео накладывается e-mail зрителя,
  чтобы расшаренный экран был «именной».

## Поток воспроизведения

```text
Browser                Backend (Lucy-nails)              Kinescope
   │                          │                              │
   │  GET /api/lessons/{id}   │                              │
   │ ───────────────────────► │                              │
   │                          │ create_drm_token(JWT, 5 мин) │
   │   embed_url с            │                              │
   │   ?drmauthtoken=...      │                              │
   │ ◄─────────────────────── │                              │
   │                                                         │
   │  GET kinescope.io/embed/<vid>?drmauthtoken=...          │
   │ ──────────────────────────────────────────────────────► │
   │                                                         │
   │       (Kinescope видит DRM-видео и нашу авторизацию)   │
   │                          ◄────  POST /drm/authorize  ──┤
   │                          │   Basic auth + { token }    │
   │                          │                             │
   │                          │ verify_drm_token() →        │
   │                          │ check_access(user, lesson)  │
   │                          │                             │
   │                          ├──── 200 allowed / 403 ────►│
   │                                                         │
   │   ◄──── DRM-ключ дешифровки (если 200) ──────────────  │
```

## Переменные окружения

Добавляются в **корневой** `.env` (см. [`.env.example`](../../.env.example)):

```env
# приватный RSA-ключ — один из двух способов:
KINESCOPE_JWT_PRIVATE_KEY_PATH=backend/secrets/kinescope-drm.pem
KINESCOPE_JWT_PRIVATE_KEY_PEM=

# kid, которым подписан JWK (печатается setup_drm.py)
KINESCOPE_JWK_KID=lucy-nails-drm-2026-05

# TTL drmauthtoken (рекомендуется 300 сек)
KINESCOPE_DRM_TOKEN_TTL_SECONDS=300

# Basic Auth для входящего webhook /api/integrations/kinescope/drm/authorize
KINESCOPE_DRM_BASIC_USER=kinescope-drm
KINESCOPE_DRM_BASIC_PASS=<сильный длинный секрет>
```

> **Хранение**: PEM-файл лежит в `backend/secrets/` (папка в `.gitignore`).
> На Railway удобнее хранить инлайн в `KINESCOPE_JWT_PRIVATE_KEY_PEM`,
> экранируя переводы строк как `\n` (сервис умеет преобразовать обратно).

## Первичный setup (один раз на проект)

1. Сгенерировать RSA-ключ + JWK, залить публичный JWK в Kinescope, прописать
   webhook + Basic Auth:

   ```powershell
   $env:PYTHONPATH = "backend"
   python scripts/kinescope/setup_drm.py `
     --project-id "<KINESCOPE_PROJECT_ID>" `
     --api-key   "<KINESCOPE_API_KEY>" `
     --webhook-url "https://api.lucysmirnova.ru/api/integrations/kinescope/drm/authorize" `
     --key-path "backend/secrets/kinescope-drm.pem" `
     --kid      "lucy-nails-drm-2026-05" `
     --basic-user "kinescope-drm" `
     --basic-pass "<сильный длинный секрет>"
   ```

   Скрипт:
   - создаёт PEM (если его нет);
   - публикует **публичный** JWK через `POST /v1/jwk`;
   - регистрирует webhook + Basic Auth через `PUT /v1/drm/auth/{project_id}`;
   - выводит подсказку, какие переменные окружения вписать в `.env`.

2. Перенести значения, которые напечатал скрипт, в `.env` / Railway env.

3. Перезапустить backend; проверить, что `KinescopeJwtService.is_configured`
   возвращает `True` (например, через `python -c "from app.services.kinescope_jwt_service import kinescope_jwt_service; print(kinescope_jwt_service.is_configured)"`).

4. Включить DRM на нужных видео в Kinescope (через UI личного кабинета — это
   единственный шаг, который API не покрывает):
   *Видео → Настройки → DRM* — включить шифрование.
   Без этого Kinescope **не будет** дёргать webhook (видео отдаётся как обычно).

## Что делает backend в runtime

- [`KinescopeJwtService.create_drm_token`](../../backend/app/services/kinescope_jwt_service.py)
  — подписывает RS256-JWT с `aud=lucy-nails-drm`, `iss=BACKEND_URL`,
  `exp=now + KINESCOPE_DRM_TOKEN_TTL_SECONDS`, claims `user_id`, `email`,
  `lesson_id`.
- [`KinescopeService.get_embed_url`](../../backend/app/services/kinescope_service.py)
  — добавляет `?drmauthtoken=<JWT>&watermark=<email|user_id>` в URL плеера,
  если сервис сконфигурирован. Если ключ не настроен (dev-режим) —
  embed URL отдаётся без `drmauthtoken` (DRM в таких видео всё равно не
  включен).
- [`POST /api/integrations/kinescope/drm/authorize`](../../backend/app/api/integrations/kinescope.py)
  — webhook для Kinescope:
  1. Проверяет HTTP Basic.
  2. Декодирует JWT публичным ключом.
  3. Берёт пользователя по `user_id` из JWT.
  4. Берёт урок по `lesson_id` из JWT (fallback — поиск по
     `kinescope_video_id == payload.id`).
  5. Сверяет, что `lesson.kinescope_video_id == payload.id` (защита от
     подмены видео в URL).
  6. Делегирует решение в `LessonService.check_access` (учитывает
     `is_preview`, роль `admin`, активную `Purchase`).
  7. Возвращает 200 с `{ status: "allowed", user_id, lesson_id }` или 403.

### Возможные ответы webhook

| Код | Когда |
| --- | --- |
| 200 | JWT валиден, пользователь найден, есть активная покупка / превью / админ |
| 401 | Basic auth не передан или неверный |
| 403 | Пустой токен, истёк/битый JWT, нет урока, video_id не совпадает, нет доступа |
| 503 | Не сконфигурирован (нет ключа или basic-пары) |

## Совместимость и режимы

- **Dev / mock** (нет `KINESCOPE_API_KEY`) — `KinescopeService.is_mock_mode=True`,
  embed URL генерируется с placeholder, `drmauthtoken` не нужен.
- **Prod без DRM** (видео не зашифрованы) — webhook никогда не вызывается,
  но `drmauthtoken` всё равно подкладывается; это безопасно, плеер его
  игнорирует на не-DRM видео.
- **Prod c DRM** — единственный режим, в котором фактически защищены файлы.
  Включение DRM на видео — отдельный шаг в UI Kinescope.

## Безопасность ключа

- Приватный PEM **никогда** не коммитится:
  - `backend/secrets/` целиком в `.gitignore`;
  - все `*.pem` тоже игнорятся (с исключением `*.example.pem`).
- На Railway хранить в зашифрованной env-переменной
  `KINESCOPE_JWT_PRIVATE_KEY_PEM`. Доступ к проекту — только у владельца.
- Для ротации:
  1. Сгенерировать новую пару с новым `kid`.
  2. Залить новый JWK через `setup_drm.py --skip-drm-auth` (старый JWK
     остаётся валиден).
  3. Подменить env (`KINESCOPE_JWT_PRIVATE_KEY_*`, `KINESCOPE_JWK_KID`),
     перезапустить backend.
  4. Через сутки удалить старый JWK через
     `DELETE /v1/jwk/{old_jwk_id}`.

## Тестирование локально

JWT-логику можно проверить без БД:

```powershell
$env:PYTHONPATH = "backend"
python -c "
import sys; sys.path.insert(0, 'backend')
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app.core.config import settings
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
settings.KINESCOPE_JWT_PRIVATE_KEY_PEM = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode('utf-8')
settings.KINESCOPE_JWK_KID = 'dev-kid'
from app.services.kinescope_jwt_service import KinescopeJwtService
svc = KinescopeJwtService()
tok = svc.create_drm_token(user_id='u-1', email='a@b.c', lesson_id='L-1')
print(svc.verify_drm_token(tok))
"
```

Полный набор интеграционных тестов webhook — в
[`backend/tests/test_kinescope_drm.py`](../../backend/tests/test_kinescope_drm.py).
Они требуют поднятой Postgres-инстанции (`nails_course`, `test_nails_course`),
как и весь backend pytest (см. `AGENTS.md`).

## Что ещё стоит проверить руками в дашборде Kinescope

API не покрывает 100% настроек, поэтому несколько шагов остаются за
человеком:

1. **Включить DRM** на каждом платном видео уроков (`Видео → DRM`).
   Промо-ролики на лендинге **не** трогаем — они должны быть открытыми.
2. Проверить, что в **Player Template** (`Plugin templates → Watermark`)
   включён динамический watermark. По умолчанию мы передаём `?watermark=`
   из embed URL — нужно, чтобы шаблон плеера это выводил.
3. Убедиться, что в проекте `Privacy → Domains` стоит `custom` со списком
   `lucysmirnova.ru`, `www.lucysmirnova.ru`, `*.lucysmirnova.ru` (это уже
   настроено через API, см. историю задачи).
4. После включения DRM — проверить, что в логах backend появляются POST на
   `/api/integrations/kinescope/drm/authorize` при попытке воспроизведения.
