# Нагрузочная приёмка

`LOAD_PROFILE=acceptance`: 50 учеников 15 минут, переход к 100 на 5 минут; параллельно 10 checkout и 50 повторов одного signed webhook (5/с, 10 секунд). `smoke`: 5 учеников 60 секунд с той же денежной пробой. Кабинет и уроки запрашиваются с реальными session-bound Bearer-токенами. Видео CDN этим тестом не измеряется; пауза 90–120 секунд имитирует обучение.

## Подготовка

1. Использовать отдельные DB/Redis/API, demo form и почтовый sink. Требуются `ALLOW_STAGING_LOAD=true` и localhost либо staging hostname; проверка URL не доказывает изоляцию ресурсов.
2. Применить миграции к пустой БД с `load_staging` в имени. `seed_staging.py` требует `ENVIRONMENT=test/staging` и точного подтверждения имени. Создаёт 11 синтетических уроков, 100 подтверждённых учеников, ручные права и обычные AuthSession; финансовую выручку не создаёт.
3. Подготовить свежие токены перед тестом: штатный access token действует 30 минут. JSON исключён из Git; не публиковать токены или сырой HTTP trace. Повтор подготовки отзывает старые токены через token_version.

```powershell
$env:DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/lucy_load_staging'
$env:ENVIRONMENT = 'test'
$env:DEBUG = 'false'
python scripts/load/seed_staging.py --confirm-database lucy_load_staging
```

Подготовка сообщает course_id, цену и путь файла без токенов. Приёмка требует 100 разных session-bound токенов. Вход, bcrypt и его rate limit проверяются отдельно: 100 входов с одного k6 IP не являются 100 независимыми клиентскими IP.

## Запуск

```powershell
$env:ALLOW_STAGING_LOAD = 'true'
$env:LOAD_PROFILE = 'acceptance' # сначала smoke
$env:API_BASE_URL = 'https://api.staging.example.ru/api'
$env:COURSE_ID = '<course_id из подготовки>'
$env:COURSE_PRICE = '5900'
$env:LEARNERS_FILE = '<абсолютный путь learners.local.json>'
# PRODAMUS_SECRET_KEY — отдельный staging secret из защищённого окружения
k6 run --summary-export load-summary.local.json scripts/load/launch-readiness.js
```

На remote staging готовить сессии средствами отдельной staging БД/секретов. Не переносить локальный JWT secret или production токены. Адреса `@example.com` проходят EmailStr; почтовый sink staging должен перехватывать сообщения, не отправлять их наружу.

## Доказательства

Gate: `http_req_failed <1%`, внутренний HTTP p95 `<500 ms`, `checks >99%`. Сохранить версию кода, профиль, длительность, summary и метрики CPU/RAM/DB/Redis. Проверить дельты: 11 новых заказов (setup+10 checkout), одна purchase, одно связанное право, 50 повторов без второй покупки, outbox без дублей. Скрипт создаёт тестовые данные и не удаляет их.

Localhost не подтверждает capacity Railway, доставку письма, Kinescope на устройствах или RPO/RTO. На remote staging отдельно подтвердить доступ <=60 секунд и письмо <=2 минут.
