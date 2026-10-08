# Триаж секретов перед запуском

**Дата:** 08.10.2026
**Статус:** происхождение четырёх исторических образцов Prodamus подтверждено официальной публичной документацией; текущие файлы и история проходят Gitleaks, 4/4 контрольных секретов обнаружены.

Проверка читала только публичную документацию провайдера и не проверяла пригодность найденных значений через платёжный или подписочный API. Значения, JWT и подписи не включены в отчёт. Удаление литерала из текущего файла не отзывает ключ и не удаляет Git-историю.

## Источники и область проверки

- Исходные 27 находок: `.superpowers/sdd/launch-2026-10-08/secret-triage-metadata.json` (14 curl-auth-header, 9 generic-api-key, 4 jwt). Метаданные CI-артефакта; значения не печатались.
- Выполненное координатором сравнение с доступными текущими backend-секретами: 0 совпадений из 27. Это не доказательство отсутствия исторической компрометации и не доказательство отзыва.
- Дополнительное текущее сканирование обнаружило 30 находок: исходные 27 плюс три ложные находки шаблона env/тестовой конфигурации/имени localStorage.
- Инструмент: официальный Gitleaks v8.24.3, Docker image `ghcr.io/gitleaks/gitleaks@sha256:e1b35e12a8c6fa8901f060459cfb6b2fc4c484d3afbe3b029733a3bbfab07055`. Host executable не устанавливался.
- Вход dir-сканирования: отдельный снимок 997 файлов до триажа и свежий снимок 999 текущих tracked и nonignored файлов после изменений через `git ls-files --cached --others --exclude-standard`. Игнорируемые `.env`, локальные артефакты и зависимости не копировались. История проверяется отдельной командой; dir не является заменой history gate.

## Все исходные находки

| Путь | Строка исходного скана | Правило | Классификация и доказательство | Решение |
|---|---:|---|---|---|
| `.claude/skills/kinescope/SKILL.md` | 241 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `.claude/skills/kinescope/references/developer-guides.md` | 1012 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/PRODAMUS_API.md` | 895 | `generic-api-key` | Одинаковый 64-символьный публичный образец ключа demo.payform.ru; точное совпадение с официальной документацией подтверждено 08.10.2026 | Только точный исторический fingerprint исключён; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/PRODAMUS_API.md` | 1753 | `generic-api-key` | Одинаковый 64-символьный публичный образец ключа demo.payform.ru; точное совпадение с официальной документацией подтверждено 08.10.2026 | Только точный исторический fingerprint исключён; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/PRODAMUS_API.md` | 2576 | `generic-api-key` | Одинаковый 64-символьный публичный образец ключа demo.payform.ru; точное совпадение с официальной документацией подтверждено 08.10.2026 | Только точный исторический fingerprint исключён; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/PRODAMUS_API.md` | 2799 | `generic-api-key` | Одинаковый 64-символьный публичный образец ключа demo.payform.ru; точное совпадение с официальной документацией подтверждено 08.10.2026 | Только точный исторический fingerprint исключён; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/KINESCOPE_API.md` | 663 | `generic-api-key` | Явно усечённый пример URL/ответа с конечным многоточием; неприменим как полный credential | Текущий пример заменён на placeholder; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 839 | `generic-api-key` | Явно усечённый пример URL/ответа с конечным многоточием; неприменим как полный credential | Текущий пример заменён на placeholder; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 5596 | `generic-api-key` | Явно усечённый пример URL/ответа с конечным многоточием; неприменим как полный credential | Текущий пример заменён на placeholder; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 6053 | `generic-api-key` | Явно усечённый пример URL/ответа с конечным многоточием; неприменим как полный credential | Текущий пример заменён на placeholder; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 6219 | `generic-api-key` | Явно усечённый пример URL/ответа с конечным многоточием; неприменим как полный credential | Текущий пример заменён на placeholder; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 655 | `jwt` | Иллюстративный JWT, exp=2023-12-25 11:40:00 UTC; значение декодировано локально, подпись не проверялась | Текущий пример заменён на `<EXAMPLE_JWT>`; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 669 | `jwt` | Иллюстративный JWT, exp=2023-12-25 11:40:00 UTC; значение декодировано локально, подпись не проверялась | Текущий пример заменён на `<EXAMPLE_JWT>`; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 6045 | `jwt` | Иллюстративный JWT, exp=2023-12-25 11:40:00 UTC; значение декодировано локально, подпись не проверялась | Текущий пример заменён на `<EXAMPLE_JWT>`; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 6058 | `jwt` | Иллюстративный JWT, exp=2023-12-25 11:40:00 UTC; значение декодировано локально, подпись не проверялась | Текущий пример заменён на `<EXAMPLE_JWT>`; только перепроверенный исторический fingerprint исключён |
| `Docs/integrations/KINESCOPE_API.md` | 357 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 475 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 507 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 515 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 523 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 695 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 1845 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 1865 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 1869 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 1889 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 1961 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |
| `Docs/integrations/KINESCOPE_API.md` | 1965 | `curl-auth-header` | Явный placeholder в Authorization; StartLine относится к началу curl, заголовок ниже | Только этот точный curl-текст и этот путь исключены из curl-auth-header |

## Дополнительные три находки текущего скана

| Путь | Строки | Доказательство | Точное исключение |
|---|---:|---|---|
| `.env.example` | 35–36 | PRIVATE_KEY_PATH и PRIVATE_KEY_PEM пусты; regexp ошибочно захватывает следующее имя переменной с `=` как значение | Только это имя с необязательным `=`, только generic-api-key, только .env.example |
| `backend/tests/test_production_hardening.py` | 17 | Синтетическое MFA-значение в тесте проверки production-конфигурации | Только точное значение fixture, только generic-api-key, только этот файл |
| `frontend/src/lib/attribution.ts` | 1 | Публичное имя ключа localStorage consent, не credential | Только это имя, только generic-api-key, только этот файл |

## Изменения и границы исключений

- `Docs/integrations/PRODAMUS_API.md`: ровно четыре литерала в исходных строках 895/1753/2576/2799 заменены на получение значения из environment; строки и остальной текст сохранены.
- `Docs/integrations/KINESCOPE_API.md`: ровно четыре истёкших JWT и пять усечённых примеров заменены на явно невалидные placeholders. Строки не добавлялись и не удалялись.
- `.gitleaks.toml`: сохраняет все правила через `extend.useDefault=true`. Для curl применяется AND: точный путь плюс полный точный текст конкретного curl-примера с placeholder (CRLF/LF эквивалентны). Для трёх дополнительных находок применяется AND: точный путь плюс точное не-секретное значение. Нет исключения каталога Docs, расширения md, всех JWT или всех demo-ключей.
- `.gitleaksignore`: добавлены девять fingerprint вида commit:path:rule:line для исторических Kinescope-примеров и четыре для проверенных публичных demo-примеров Prodamus. Kinescope перепроверен локально через git show (JWT exp либо конечное многоточие); Prodamus — точным приватным сравнением с официальными публичными страницами. Исключения ограничены конкретным коммитом, путём, правилом и строкой; широкого исключения demo-ключей нет.
- Четыре искусственных canary на тех же путях обнаружены новым сканом: curl с другим токеном, реальное value-shaped значение PRIVATE_KEY_PEM, другое значение MFA fixture и новый синтетический ключ Prodamus. Canary находятся только в игнорируемом локальном тестовом снимке; не внесены в runtime/документы.

## Проверки

| Проверка | Результат | Локальный артефакт |
|---|---|---|
| Current dir, стандартные правила, до исправлений | exit 1, 30 находок | `secret-scan-current-redacted.json` |
| Current dir, итоговая конфигурация, после исправлений | exit 0, 999 файлов, 0 находок | `secret-scan-current-public-redacted.json` |
| Canary на точных исключённых путях, итоговая конфигурация | ожидаемый exit 1, 4/4 искусственных значения обнаружены | `secret-scan-canary-public-redacted.json` |
| Git history до HEAD, итоговая конфигурация и fingerprints | **exit 0, 0 находок; 149 достижимых коммитов, Gitleaks обработал 141 коммит** | `secret-scan-history-public-redacted.json` |

Команды сканирования: `gitleaks dir /scan --config /config/.gitleaks.toml --gitleaks-ignore-path /config/.gitleaksignore --redact=100 --report-format json` и `gitleaks git /history --config /config/.gitleaks.toml --gitleaks-ignore-path /config/.gitleaksignore --log-opts=FETCH_HEAD --redact=100 --report-format json`. Исторический снимок обновлён локальным fetch из текущего checkout до `8d1f946bdbe40fe9514e1655b37dd6fb0b526dda`; источник истории не изменялся. Полные отчёты сохраняются локально с redact=100; в чат передавались только пути, правила, количества и статусы.

Конфигурация проверена по [официальной документации Gitleaks v8.24.3](https://github.com/gitleaks/gitleaks/blob/v8.24.3/README.md): extend.useDefault и rule allowlists с condition=AND. TOML разобран, 17 точных исключений проверены, глобального allowlist нет.

## Подтверждённое публичное происхождение Prodamus

08.10.2026 четыре значения из коммита `b63204b9d986ed53b2ade85509c8c0eab07fac0e` извлечены локально через `git show` и сравнены внутри Python с содержимым официальных публичных страниц. Все четыре литерала идентичны, длина каждого — 64 символа. Все четыре страницы вернули HTTP 200, содержат точное значение в видимом примере и адрес `demo.payform.ru`. Литерал не передавался в URL, поисковый запрос, логи или отчёт.

| Историческая строка | Официальный источник | Результат и контекст |
|---|---|---|
| 895 | [Документация для самостоятельной интеграции сервисов](https://help.prodamus.ru/payform/integracii/rest-api/instrukcii-dlya-samostoyatelnaya-integracii-servisov) | HTTP 200, exact match; раздел «Пример программного кода формирования ссылки для демо-формы», явное обозначение «Секретный ключ демо-формы» |
| 1753 | [Управление статусами подписки](https://help.prodamus.ru/payform/integracii/rest-api-1/setactivity) | HTTP 200, exact match; пример запроса к `https://demo.payform.ru/rest/setActivity/` |
| 2576 | [Управление скидкой по подписке](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptiondiscount) | HTTP 200, exact match; пример запроса к `https://demo.payform.ru/rest/setSubscriptionDiscount/` |
| 2799 | [Установка даты следующего платежа по подписке](https://help.prodamus.ru/payform/integracii/rest-api-1/setsubscriptionpaymentdate) | HTTP 200, exact match; пример запроса к `https://demo.payform.ru/rest/setSubscriptionPaymentDate/` |

Это доказательство публичного иллюстративного происхождения конкретных исторических находок. Сравнение с доступными текущими backend-секретами остаётся 0/27; оно не является доказательством отзыва или отсутствия прошлой компрометации. Отзыв, ротация, проверка пригодности ключа и переписывание Git-истории не выполнялись. Исторические исключения закрывают только эти четыре подтверждённых образца.

Проверка `.github/workflows/security.yml` подтверждает: Gitleaks action получает полную историю через fetch-depth=0. Поэтому dir-скан и history-скан проверяются отдельно.
