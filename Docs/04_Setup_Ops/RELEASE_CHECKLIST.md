# MVP Production Release Checklist

Этот чеклист закрывает релиз текущего MVP: покупка через Prodamus, доступ на 30 дней, кабинет ученика, уроки Kinescope и базовая админка.

## 1. Pre-Release

- [ ] Git рабочее дерево чистое или все изменения осознанно включены в PR.
- [ ] В CI зелёные проверки backend `ruff`, backend `pytest`, frontend `lint`, frontend `build`.
- [ ] В CI или вручную выполнено `alembic upgrade head` на staging БД.
- [ ] В релиз включена миграция `backend/alembic/versions/c8d41b2a9f01_production_user_phone_and_purchase_meta.py`.
- [ ] Первый админ создан через `ADMIN_EMAIL=... ADMIN_PASSWORD=... python backend/scripts/create_admin.py` в Railway shell.
- [ ] Production content проверен через `python backend/scripts/check_production_content.py`.

## 2. Railway Environment

Backend:

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `DATABASE_URL` указывает на production/staging PostgreSQL, не на локальную БД.
- [ ] `JWT_SECRET_KEY` заменён на длинный уникальный секрет.
- [ ] `FRONTEND_URL` и `BACKEND_URL` указывают на публичные HTTPS URL.
- [ ] `CORS_ORIGINS` содержит только frontend origin.
- [ ] `TRUSTED_HOSTS` содержит backend-домены без схемы.
- [ ] `KINESCOPE_API_KEY` задан.
- [ ] `PRODAMUS_URL`, `PRODAMUS_SECRET_KEY`, `PRODAMUS_SHOP_ID` заданы.
- [ ] Checkout требует регистрацию/вход до оплаты; `SMTP_*` нужны только если включён guest checkout с отправкой credentials.

Frontend:

- [ ] `NEXT_PUBLIC_API_URL` указывает на `BACKEND_URL + /api`.
- [ ] `NEXT_PUBLIC_SITE_URL` указывает на публичный frontend URL.

## 3. Prodamus

- [ ] В личном кабинете Prodamus webhook указывает на `BACKEND_URL + /api/payments/webhook`.
- [ ] Подпись webhook соответствует `PRODAMUS_SECRET_KEY`.
- [ ] Тестовый платёж создаёт или обновляет одну покупку даже при повторной доставке webhook.
- [ ] Неверная сумма или подпись не выдаёт доступ.

## 4. Kinescope

- [ ] У всех production-уроков задан `kinescope_video_id`.
- [ ] В Kinescope включены нужные ограничения домена, watermark/DRM согласно тарифу сервиса.
- [ ] Ученик с активной покупкой получает embed URL.
- [ ] Ученик без покупки не получает доступ к закрытому уроку.

## 5. Manual Smoke Test

- [ ] Гость видит лендинг, страницу курса, тарифы и юридические страницы.
- [ ] Без опубликованного курса кнопки оплаты не ведут на `default`.
- [ ] Пользователь регистрируется, входит, попадает в кабинет.
- [ ] Авторизованный пользователь стартует оплату, Prodamus получает email аккаунта и course/tariff order id.
- [ ] После webhook покупка появляется в `/admin/purchases`.
- [ ] В кабинете отображается курс, срок доступа и прогресс.
- [ ] Страница урока открывает видео и сохраняет прогресс.
- [ ] Истёкшая покупка не даёт доступ.
- [ ] Админ может выдать доступ вручную и увидеть покупку.
- [ ] Автоматический smoke `.\scripts\smoke-production.ps1 -FrontendUrl <url> -BackendUrl <url>` пройден.

## 6. Production Go/No-Go

Go только если:

- [ ] Нет известных P0/P1 security blockers.
- [ ] Staging smoke-test пройден.
- [ ] Prodamus webhook проверен на реальном staging/prod URL.
- [ ] Есть план отката: предыдущий Railway deploy и DB backup/snapshot.

Post-MVP не блокирует релиз:

- Telegram-бот и уведомления.
- Сертификаты.
- PWA.
- Расширенная аналитика.
- Полноценные E2E/component tests.
