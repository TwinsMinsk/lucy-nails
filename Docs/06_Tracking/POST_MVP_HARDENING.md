# Post-MVP Hardening Backlog

Эти пункты не блокируют первый production-релиз MVP, но должны быть запланированы после стабилизации продаж и первых пользователей.

- Перевести auth на полноценные httpOnly Secure cookie sessions с refresh-token rotation/revocation.
- Подключить Redis-backed rate limit для нескольких backend-инстансов.
- Добавить payment audit/outbox: raw webhook events, retry доставки писем, историю повторных покупок.
- Расширить тесты: expired access, admin/upload, real Prodamus fixtures, frontend smoke/e2e.
- Добавить Telegram-бота, сертификаты, PWA и расширенную аналитику.
