# Прокси для доступа из России

С ноября 2026 года сеть Railway в России недоступна не только из дата-центров, но и у домашних и мобильных провайдеров: TCP открывается, TLS виснет. 03.11.2026 Globalping (`magic: RU+eyeball-network`) показал 0 из 20 напрямую и 20 из 20 через этот прокси (Билайн, МТС, Ростелеком, ER-Telecom, МГТС и др.).

Поэтому `lucysmirnova.ru`, `www.lucysmirnova.ru` и `api.lucysmirnova.ru` указывают на VPS в Минске, а он пересылает запросы в Railway. Приложения и настройки Railway не менялись, кроме `FORWARDED_ALLOW_IPS` у Backend.

```
посетитель ──► VPS hoster.by, Caddy ──► Railway (Frontend / Backend)
```

## Как устроено

- **Сервер:** hoster.by, облачный VPS 1 vCPU / 1 ГБ / SSD 10 ГБ, Ubuntu 26.04, IPv4 `87.232.67.155`. Вход по SSH только по ключу, файрвол `ufw` пропускает 22, 80 и 443, включены `unattended-upgrades`.
- **Caddy** из официального репозитория (`dl.cloudsmith.io/public/caddy/stable`), конфиг — [`Caddyfile`](Caddyfile), на сервере `/etc/caddy/Caddyfile`. Журнал запросов выключен: адреса и ссылки учениц на сервере не хранятся.
- **Upstream.** Caddy подключается к `*.up.railway.app` с этим же SNI (сертификат Railway) и передаёт исходный `Host`. Railway маршрутизирует по `Host` и обслуживает наши домены, хотя в его панели DNS у них помечен «requires update». `Host: *.up.railway.app` Backend отвергает (400, `TRUSTED_HOSTS`), поэтому `header_up Host {host}` обязателен.
- **Сертификаты** Let's Encrypt Caddy получает и продлевает сам (TLS-ALPN-01 на 443).
- **IP посетителя.** Caddy ставит `X-Forwarded-For` с адресом клиента и не доверяет входящему. Railway дописывает адрес прокси, поэтому `87.232.67.155` добавлен в `FORWARDED_ALLOW_IPS` у Backend: Uvicorn пропускает доверенные адреса справа и берёт адрес посетителя для лимитов и журнала сессий. Проверено 03.11.2026: в новой сессии `GET /api/auth/sessions` показал адрес клиента, а не прокси.
- **HTTP/3 выключен** (`protocols h1 h2`): QUIC в российских сетях работает нестабильно.
- **DNS** в Cloudflare: три записи `A 87.232.67.155`, режим «DNS only». Проксирование Cloudflare не включать: его в России тоже замедляют.
- **Вебхуки** Prodamus и Kinescope по-прежнему идут через [`../webhook-relay`](../webhook-relay/) на `https://api.lucysmirnova.ru`, теперь через этот прокси.

## Мониторинг

- **Из России, раз в час:** workflow [`reachability.yml`](../../.github/workflows/reachability.yml) запускает [`scripts/ops/check_russia_reachability.py`](../../scripts/ops/check_russia_reachability.py): 10 проб Globalping в российских домашних и мобильных сетях открывают `/` и `/health`, плюс срок сертификатов всех трёх доменов. Падение (меньше 70% успешных проб или сертификат дольше 14 дней не продлевается) — письмо GitHub о неудачном workflow. Сбой самого Globalping — предупреждение без падения. Запустить вручную: Actions → «Reachability from Russia» → Run workflow. Секрет `GLOBALPING_TOKEN` необязателен, он поднимает лимит запросов.
- **Доступность сервера:** внешний монитор раз в 1–5 минут на `https://lucysmirnova.ru/` и `https://api.lucysmirnova.ru/health` (UptimeRobot или аналог). Он видит падение сервера или кончившийся баланс, но не блокировку в России.

GitHub отключает расписание в репозитории без активности 60 дней: тогда включить workflow заново во вкладке Actions.

## Проверка вручную

Без людей в России — Globalping, домашние и мобильные сети:

```powershell
$body = @{ type='http'; target='lucysmirnova.ru'; locations=@(@{ magic='RU+eyeball-network'; limit=15 }); measurementOptions=@{ protocol='HTTPS'; request=@{ method='GET'; path='/' } } } | ConvertTo-Json -Depth 6
$id = (Invoke-RestMethod -Method Post -ContentType 'application/json' -Body $body https://api.globalping.io/v1/measurements).id
Start-Sleep 30; (Invoke-RestMethod "https://api.globalping.io/v1/measurements/$id").results | ForEach-Object { "{0} {1} {2}" -f $_.probe.network, $_.result.statusCode, $_.result.timings.total }
```

Отдельные сбои вне России бывают у сетей, которым недоступен сам hoster.by (03.11.2026 — один хостинг в Варшаве).

## Изменение конфига

```powershell
scp -i $HOME\.ssh\lucy_proxy_ed25519 ops\proxy\Caddyfile root@87.232.67.155:/tmp/Caddyfile.new
ssh -i $HOME\.ssh\lucy_proxy_ed25519 root@87.232.67.155 'caddy validate --config /tmp/Caddyfile.new --adapter caddyfile && install -m 0644 /tmp/Caddyfile.new /etc/caddy/Caddyfile && systemctl reload caddy'
```

## Откат

Вернуть в Cloudflare прежние записи (все три — CNAME, «DNS only»):

| Имя | Значение |
| --- | --- |
| `lucysmirnova.ru` | `frontend-production-7b2e.up.railway.app` |
| `www` | `frontend-production-7b2e.up.railway.app` |
| `api` | `backend-production-f8f0f.up.railway.app` |

TTL записей прокси — 60 с. Railway выпускает сертификат для домена заново, когда DNS снова указывает на него. Адрес прокси в `FORWARDED_ALLOW_IPS` откату не мешает.

## Риски

- Сервер — единственная точка входа: если он упадёт или кончится баланс у провайдера, сайт не откроется ни у кого. Нужен внешний мониторинг `/` и `/health` по [`LAUNCH_OPERATIONS.md`](../../Docs/04_Setup_Ops/LAUNCH_OPERATIONS.md#monitoring).
- Если заблокируют и этот адрес, поднять такой же сервер у другого провайдера (сначала проверить его доступность из России через Globalping) и сменить три A-записи.
- Railway может перестать обслуживать домен, DNS которого на него не указывает. Признак — 404 или ошибка сертификата upstream в журнале Caddy (`journalctl -u caddy`).
