# Прокси для доступа из России (сейчас не используется)

**Статус на 09.11.2026: выключен.** DNS всех трёх доменов снова указывает на Railway (CNAME, «DNS only»). Railway сменил адреса на `153.52.255.x` (раньше `69.46.46.x`), и новые адреса из России открываются напрямую: Globalping `RU+eyeball-network` — сайт 15/15, `/health` 10/10; российские дата-центры — `/health` 9/10. Этот каталог — готовый план на случай, если Railway снова заблокируют.

## Зачем был нужен

03.11.2026 сеть Railway (`69.46.46.x`) в России не отвечала по TLS не только из дата-центров, но и у домашних и мобильных провайдеров: Globalping показал 0 из 20 напрямую и 20 из 20 через прокси. С 03.11 по 04.11.2026 `lucysmirnova.ru`, `www` и `api` указывали на VPS в Минске, а он пересылал запросы в Railway:

```
посетитель ──► VPS, Caddy ──► Railway (Frontend / Backend)
```

## Инцидент 04–09.11.2026

VPS на hoster.by брали на тестовый день и не продлили. Провайдер остановил сервер 04.11.2026 (между 07:55 и 16:26 UTC), DNS указывал на него, и сайт около пяти дней не открывался ни у кого. Ежечасная проверка падала 17 раз подряд, но уведомления GitHub о неудачных workflow и внешний монитор не были настроены, поэтому сбой никто не увидел. 09.11.2026 DNS откатили на Railway.

Выводы:

- Прокси — единственная точка входа. Включать его можно только с оплаченным вперёд сервером, автоплатежом и работающими уведомлениями (см. «Мониторинг»).
- **hoster.by для этого не подходит.** Пункт 4.2.2 [публичного договора облачного хостинга](https://hoster.by/clients/public/cloud/) относит «размещение Proxy-серверов» к нарушениям, по которым провайдер вправе ограничить трафик. Поддержка hoster.by указала на этот запрет.

## Где поднимать при новой блокировке

Проверено 09.11.2026 по публичным условиям:

| Провайдер | Прокси в условиях |
| --- | --- |
| hoster.by (Беларусь) | запрещено, п. 4.2.2 договора облачного хостинга |
| activecloud.by (Беларусь) | запрещено, п. 2.3.7 дополнения «Cloud Server»: в том числе «установка… программного обеспечения, связанного с прокси-серверами» |
| ps.kz (Казахстан) | запрещено, п. 3.12.12 оферты: «организации Proxy-серверов» |
| hoster.kz (Казахстан) | запрещено, п. 6.2.3 договора облачного сервера: «скрипты, которые эмулируют работу прокси-сервера» и «входящий зарубежный трафик» |
| reg.am (Армения) | в общих условиях запрета нет |

Перед заказом письменно спросить у поддержки, разрешён ли reverse proxy (nginx/Caddy) только для своих доменов на свой backend, и проверить доступность адреса сервера из России через Globalping. Долгосрочная альтернатива — перенести само приложение на хостинг, доступный из России, тогда прокси не нужен.

## Как устроен

- **Caddy** из официального репозитория (`dl.cloudsmith.io/public/caddy/stable`), конфиг — [`Caddyfile`](Caddyfile) (последняя рабочая версия), на сервере `/etc/caddy/Caddyfile`. Журнал запросов выключен: адреса и ссылки учениц на сервере не хранятся. Сервер: 1 vCPU / 1 ГБ, Ubuntu, вход по SSH только по ключу, `ufw` пропускает 22, 80 и 443, `unattended-upgrades`.
- **Upstream.** Caddy подключается к `*.up.railway.app` с этим же SNI (сертификат Railway) и передаёт исходный `Host`. Railway маршрутизирует по `Host` и обслуживает наши домены, хотя в его панели DNS у них помечен «requires update». `Host: *.up.railway.app` Backend отвергает (400, `TRUSTED_HOSTS`), поэтому `header_up Host {host}` обязателен.
- **Сертификаты** Let's Encrypt Caddy получает и продлевает сам (TLS-ALPN-01 на 443). Пока DNS не переключён, проверять можно с временными сертификатами (`tls internal` в блоке сайта) и `curl --resolve`.
- **IP посетителя.** Caddy ставит `X-Forwarded-For` с адресом клиента и не доверяет входящему. Railway дописывает адрес прокси, поэтому IP прокси нужно добавить в `FORWARDED_ALLOW_IPS` у Backend: Uvicorn пропускает доверенные адреса справа и берёт адрес посетителя для лимитов и журнала сессий. Проверено 03.11.2026 через `GET /api/auth/sessions`. Старый адрес `87.232.67.155` в переменной остался, он безвреден.
- **HTTP/3 выключен** (`protocols h1 h2`): QUIC в российских сетях работает нестабильно.
- **DNS** в Cloudflare: A-записи на IP прокси, режим «DNS only», TTL 60 с. Проксирование Cloudflare не включать: его в России тоже замедляют. Переключать по одной записи, начиная с `www`.
- **Вебхуки** Prodamus и Kinescope идут через [`../webhook-relay`](../webhook-relay/) на `https://api.lucysmirnova.ru`, то есть через прокси, когда он включён.

## Мониторинг

- **Из России, раз в час:** workflow [`reachability.yml`](../../.github/workflows/reachability.yml) запускает [`scripts/ops/check_russia_reachability.py`](../../scripts/ops/check_russia_reachability.py): 10 проб Globalping в российских домашних и мобильных сетях открывают `/` и `/health`, плюс срок сертификатов всех трёх доменов. Работает и с прокси, и без него. Падение (меньше 70% успешных проб или сертификату меньше 14 дней) — письмо GitHub о неудачном workflow, **если у владельца репозитория включены уведомления Actions** (Settings → Notifications → Actions → Email, «Only notify for failed workflows»). Сбой самого Globalping — предупреждение без падения. Запустить вручную: Actions → «Reachability from Russia» → Run workflow. Секрет `GLOBALPING_TOKEN` необязателен, он поднимает лимит запросов.
- **Доступность сайта:** внешний монитор раз в 1–5 минут на `https://lucysmirnova.ru/` и `https://api.lucysmirnova.ru/health` (UptimeRobot или аналог). Он видит падение сервера или кончившийся баланс, но не блокировку в России.

GitHub отключает расписание в репозитории без активности 60 дней: тогда включить workflow заново во вкладке Actions.

## Проверка вручную

Без людей в России — Globalping, домашние и мобильные сети:

```powershell
$body = @{ type='http'; target='lucysmirnova.ru'; locations=@(@{ magic='RU+eyeball-network'; limit=15 }); measurementOptions=@{ protocol='HTTPS'; request=@{ method='GET'; path='/' } } } | ConvertTo-Json -Depth 6
$id = (Invoke-RestMethod -Method Post -ContentType 'application/json' -Body $body https://api.globalping.io/v1/measurements).id
Start-Sleep 30; (Invoke-RestMethod "https://api.globalping.io/v1/measurements/$id").results | ForEach-Object { "{0} {1} {2}" -f $_.probe.network, $_.result.statusCode, $_.result.timings.total }
```

Проверить новый сервер до переключения DNS: в `target` указать его IP, в `request` добавить `host='lucysmirnova.ru'`.

## Изменение конфига

```powershell
scp -i $HOME\.ssh\lucy_proxy_ed25519 ops\proxy\Caddyfile root@<IP>:/tmp/Caddyfile.new
ssh -i $HOME\.ssh\lucy_proxy_ed25519 root@<IP> 'caddy validate --config /tmp/Caddyfile.new --adapter caddyfile && install -m 0644 /tmp/Caddyfile.new /etc/caddy/Caddyfile && systemctl reload caddy'
```

## Откат на Railway

Вернуть в Cloudflare записи (все три — CNAME, «DNS only»):

| Имя | Значение |
| --- | --- |
| `lucysmirnova.ru` | `frontend-production-7b2e.up.railway.app` |
| `www` | `frontend-production-7b2e.up.railway.app` |
| `api` | `backend-production-f8f0f.up.railway.app` |

Сертификаты Railway для доменов после отката 09.11.2026 действовали, сайт открылся сразу.

## Риски прокси

- Сервер — единственная точка входа: если он упадёт или кончится баланс, сайт не откроется ни у кого.
- Если заблокируют и адрес прокси, поднять такой же сервер у другого провайдера и сменить три A-записи.
- Railway может перестать обслуживать домен, DNS которого на него не указывает. Признак — 404 или ошибка сертификата upstream в журнале Caddy (`journalctl -u caddy`).
