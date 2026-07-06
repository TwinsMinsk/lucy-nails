<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-07-06 | Updated: 2026-07-06 -->

# scripts/kinescope

## Purpose

Автономные Python CLI для настройки и отладки Kinescope DRM Authorization Backend: генерация RSA-ключей и загрузка публичного JWK, регистрация webhook-URL для проверки доступа, подпись/проверка тестовых `drmauthtoken`, инспекция зарегистрированных JWK и конфигурации webhook. Работают рядом с рантайм-подписью в [`backend/app/services/kinescope_jwt_service.py`](../../backend/app/services/kinescope_jwt_service.py), но не зависят от backend-кода.

## Key Files

| File | Description |
|------|-------------|
| [`setup_drm.py`](setup_drm.py) | Разовая настройка: генерирует RSA-2048 пару, сохраняет приватный PEM (по умолчанию `backend/secrets/kinescope_drm_private.pem`), заливает публичный ключ как JWK (`POST /v1/jwk`), регистрирует webhook DRM-проекта (`PUT /v1/drm/auth/{project_id}`) |
| [`put_drm_auth_from_env.py`](put_drm_auth_from_env.py) | Перерегистрирует webhook Authorization Backend из переменных `.env` (`KINESCOPE_API_KEY`, `KINESCOPE_PROJECT_ID`, `KINESCOPE_DRM_BASIC_USER/PASS`) без генерации новых ключей |
| [`drm_actions.py`](drm_actions.py) | Отладочный CLI: `sign-token` (подписать тестовый `drmauthtoken` RS256, опционально собрать embed-URL), `decode-token` (декод + верификация JWT), `list-jwks` (`GET /v1/jwk`), `get-drm-auth` (`GET /v1/drm/auth/<project_id>`); состояние Kinescope не меняет |
| `.last-setup-output.txt` | Локальный вывод последнего запуска `setup_drm.py` — исключён из Git (`scripts/*/.last-setup-output.txt`), может содержать чувствительные значения; не читать вслух и не цитировать |

## For AI Agents

### Working In This Directory

- Все скрипты читают/используют корневой `.env`: `KINESCOPE_API_KEY`, `KINESCOPE_PROJECT_ID`, `KINESCOPE_JWT_PRIVATE_KEY_PATH`/`KINESCOPE_JWT_PRIVATE_KEY_PEM`, `KINESCOPE_JWK_KID`, `KINESCOPE_DRM_BASIC_USER`/`KINESCOPE_DRM_BASIC_PASS`, `KINESCOPE_DRM_TOKEN_TTL_SECONDS`.
- `setup_drm.py` и парный [`scripts/railway/push_drm_variables.ps1`](../railway/push_drm_variables.ps1) — операции с секретами и side-эффектами на реальном Kinescope workspace; выполнять по явному запросу пользователя, не проактивно.
- Никогда не печатать/коммитить содержимое приватного PEM, реальные `user_id`/`lesson_id` из подписанных токенов или `.last-setup-output.txt`.
- `drm_actions.py` безопасен для повторных запусков (read-only к Kinescope, кроме локальной подписи тестовых токенов).

### Testing Requirements

- Автотестов нет; проверка — `drm_actions.py sign-token ... --print-embed`, затем `decode-token --token ... --verify` на тестовом `video_id`/`lesson_id`.
- Реальную интеграцию (`setup_drm.py`, `put_drm_auth_from_env.py`) проверять на staging-проекте Kinescope, не на production workspace.

### Common Patterns

- Docstring-заголовок модуля описывает «что делает» / подкоманды и полный список нужных env-переменных.
- `.env` подгружается лениво, только если переменных ещё нет в `os.environ` (см. `_load_dotenv_if_missing` / `_load_env`).
- RSA/JWK-кодирование (base64url) — вручную, без сторонних JWK-библиотек; для decode/verify JWT — `python-jose`.

## Dependencies

### Internal

- [`backend/app/services/kinescope_jwt_service.py`](../../backend/app/services/kinescope_jwt_service.py) — рантайм-подпись токенов в production, должна оставаться совместимой с ключами/claims, которые генерируют эти скрипты
- [`backend/app/api/integrations/kinescope.py`](../../backend/app/api/integrations/kinescope.py) — webhook, на который регистрируется Authorization Backend
- [`scripts/railway/push_drm_variables.ps1`](../railway/push_drm_variables.ps1) — заливает в Railway PEM/env, подготовленные `setup_drm.py`
- [`Docs/integrations/KINESCOPE_AUTH_BACKEND.md`](../../Docs/integrations/KINESCOPE_AUTH_BACKEND.md), [`Docs/integrations/KINESCOPE_API.md`](../../Docs/integrations/KINESCOPE_API.md)

### External

- Kinescope REST API (`api.kinescope.io`: `/v1/jwk`, `/v1/drm/auth/{project_id}`)
- `httpx`, `cryptography`, `python-jose`, `requests`

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
