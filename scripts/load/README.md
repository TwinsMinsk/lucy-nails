# Нагрузочный gate запуска

Сценарий `launch-readiness.js` проверяет одновременно 100 чтений, 20 созданий checkout и 10 повторных webhook в секунду. Он намеренно запускается только против URL с `staging`/`localhost` и требует явного `ALLOW_STAGING_LOAD=true`.

```powershell
$env:ALLOW_STAGING_LOAD = "true"
$env:API_BASE_URL = "https://api-staging.example.ru/api"
$env:COURSE_ID = "<staging course UUID>"
$env:COURSE_PRICE = "5000"
$env:PRODAMUS_SECRET_KEY = "<staging secret>"
k6 run scripts/load/launch-readiness.js
```

Gate: `http_req_failed < 1%`, общий внутренний HTTP `p95 < 500 ms`. Результат k6 и снимок метрик БД/Redis прикладываются к release checklist. Скрипт создаёт тестовые заказы и доступ для адресов `@example.test`; после прогона их очищают только в staging.
