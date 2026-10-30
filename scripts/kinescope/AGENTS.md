# scripts/kinescope

**Parent context:** `../AGENTS.md`
**Generated:** 2026-07-06 · **Updated:** 2026-10-30

## Purpose

Автономные Python CLI для настройки и отладки Kinescope DRM Authorization Backend: генерация RSA-ключей и загрузка публичного JWK, регистрация webhook-URL для проверки доступа, подпись/проверка тестовых `drmauthtoken`, инспекция зарегистрированных JWK и конфигурации webhook. Работают рядом с рантайм-подписью в [`backend/app/services/kinescope_jwt_service.py`](../../backend/app/services/kinescope_jwt_service.py), но не зависят от backend-кода.

## Key Files

| File | Description |
|------|-------------|
| [`setup_drm.py`](setup_drm.py) | Разовая настройка: генерирует RSA-2048 пару, сохраняет приватный PEM (`--key-path`, по умолчанию `backend/secrets/kinescope_drm_private.pem`), заливает публичный ключ как JWK (`POST /v1/jwk`, срок `--key-expires-days`), регистрирует webhook DRM-проекта (`PUT /v1/drm/auth/{project_id}`, пропускается через `--skip-drm-auth`). Обязателен `--webhook-url`; также `--project-id`, `--api-key`, `--kid`, `--basic-user`, `--basic-pass`. В конце печатает в stdout env-блок с приватным PEM и Basic-паролем |
| [`put_drm_auth_from_env.py`](put_drm_auth_from_env.py) | Перерегистрирует webhook Authorization Backend из переменных `.env` (`KINESCOPE_API_KEY`, `KINESCOPE_PROJECT_ID`, `KINESCOPE_DRM_BASIC_USER/PASS`) без генерации новых ключей; флаги `--env-file`, `--webhook-base` (по умолчанию production `https://api.lucysmirnova.ru`) |
| [`drm_actions.py`](drm_actions.py) | Отладочный CLI: `sign-token` (подписать тестовый `drmauthtoken` RS256, обязателен `--user-id`; опционально собрать embed-URL через `--video-id`), `decode-token` (декод + верификация JWT, `--token <jwt или @file>`, `--verify`), `list-jwks` (`GET /v1/jwk`), `get-drm-auth` (`GET /v1/drm/auth/<project_id>`); состояние Kinescope не меняет |
| `.last-setup-output.txt` | Скрипты его не создают и в Git его нет; если файл есть — это сохранённый вручную вывод `setup_drm.py`. Исключён из Git (`scripts/*/.last-setup-output.txt`), может содержать приватный PEM и пароль; не читать и не цитировать |

## For AI Agents

### Working In This Directory

- Источник конфигурации у скриптов разный. `setup_drm.py` берёт только флаги и переменные ОС, `.env` не читает. `put_drm_auth_from_env.py` читает `--env-file` (по умолчанию корневой `.env`, без файла завершается ошибкой), переменные ОС приоритетнее. `drm_actions.py` подгружает из корневого `.env` только недостающие ключи.
- Используемые переменные: `KINESCOPE_API_KEY`, `KINESCOPE_PROJECT_ID`, `KINESCOPE_JWT_PRIVATE_KEY_PATH`/`KINESCOPE_JWT_PRIVATE_KEY_PEM`, `KINESCOPE_JWK_KID`, `KINESCOPE_DRM_BASIC_USER`/`KINESCOPE_DRM_BASIC_PASS`, `KINESCOPE_DRM_TOKEN_TTL_SECONDS`, `BACKEND_URL` (claim `iss` в `drm_actions.py`).
- `setup_drm.py` и парный [`scripts/railway/push_drm_variables.ps1`](../railway/push_drm_variables.ps1) — операции с секретами и side-эффектами на реальном Kinescope workspace; выполнять по явному запросу пользователя, не проактивно.
- `setup_drm.py` перезаписывает PEM по `--key-path` без проверки и до загрузки JWK. При ротации указывать новый путь, иначе прежний приватный ключ будет потерян.
- `put_drm_auth_from_env.py` без `--webhook-base` регистрирует production-URL; для другого окружения передавать флаг явно.
- Никогда не печатать/коммитить содержимое приватного PEM, реальные `user_id`/`lesson_id` из подписанных токенов или `.last-setup-output.txt`. Вывод `sign-token` — настоящий JWT, обращаться с ним как с секретом.
- `drm_actions.py` безопасен для повторных запусков (read-only к Kinescope, кроме локальной подписи тестовых токенов).

### Testing Requirements

- Автотестов нет; проверка — `drm_actions.py sign-token --user-id ... --lesson-id ... --print-token`, затем `decode-token --token ... --verify` на тестовых значениях; embed-URL — `sign-token ... --video-id ... --print-embed`.
- Реальную интеграцию (`setup_drm.py`, `put_drm_auth_from_env.py`) проверять на staging-проекте Kinescope, не на production workspace.

### Common Patterns

- Docstring-заголовок модуля описывает «что делает» / подкоманды и нужные env-переменные.
- `.env` разбирается вручную, без `python-dotenv`, и не перекрывает уже заданные переменные (см. `_load_dotenv_if_missing` / `_load_env`).
- RSA/JWK-кодирование (base64url) — вручную, без сторонних JWK-библиотек; для decode/verify JWT — `python-jose`.

## Dependencies

### Internal

- [`backend/app/services/kinescope_jwt_service.py`](../../backend/app/services/kinescope_jwt_service.py) — рантайм-подпись токенов в production (PyJWT), должна оставаться совместимой с ключами/claims, которые генерируют эти скрипты (`aud=lucy-nails-drm`, `iss` из `BACKEND_URL`)
- [`backend/app/api/integrations/kinescope.py`](../../backend/app/api/integrations/kinescope.py) — webhook `/api/integrations/kinescope/drm/authorize`, на который регистрируется Authorization Backend
- [`scripts/railway/push_drm_variables.ps1`](../railway/push_drm_variables.ps1) — заливает в Railway PEM/env, подготовленные `setup_drm.py`
- [`.claude/skills/kinescope-actions/SKILL.md`](../../.claude/skills/kinescope-actions/SKILL.md) — скилл-обёртка над `drm_actions.py`
- [`Docs/integrations/KINESCOPE_AUTH_BACKEND.md`](../../Docs/integrations/KINESCOPE_AUTH_BACKEND.md), [`Docs/integrations/KINESCOPE_API.md`](../../Docs/integrations/KINESCOPE_API.md)

### External

- Kinescope REST API (`api.kinescope.io`: `/v1/jwk`, `/v1/drm/auth/{project_id}`)
- `httpx` (`setup_drm.py`, `put_drm_auth_from_env.py`), `cryptography` (`setup_drm.py`, `drm_actions.py`), `python-jose`, `requests` (`drm_actions.py`). Последних двух нет в `backend/requirements.lock`, их нужно ставить отдельно

## Manual Notes

Notes under this heading are written by humans and preserved on regeneration.
