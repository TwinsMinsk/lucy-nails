# Триаж секретов перед запуском

**Дата:** 08.10.2026
**Статус:** текущие tracked/nonignored файлы проходят Gitleaks; историческое происхождение четырёх образцов Prodamus остаётся открытым.

Проверка не обращалась к провайдерам и не проверяла пригодность найденных значений через API. Значения, JWT и подписи не включены в отчёт. Удаление литерала из текущего файла не отзывает ключ и не удаляет Git-историю.

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
| `Docs/integrations/PRODAMUS_API.md` | 895 | `generic-api-key` | Одинаковый 64-символьный образец ключа в четырёх PHP-примерах для demo.payform.ru; происхождение/отзыв не доказаны | OPEN исторически; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/PRODAMUS_API.md` | 1753 | `generic-api-key` | Одинаковый 64-символьный образец ключа в четырёх PHP-примерах для demo.payform.ru; происхождение/отзыв не доказаны | OPEN исторически; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/PRODAMUS_API.md` | 2576 | `generic-api-key` | Одинаковый 64-символьный образец ключа в четырёх PHP-примерах для demo.payform.ru; происхождение/отзыв не доказаны | OPEN исторически; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
| `Docs/integrations/PRODAMUS_API.md` | 2799 | `generic-api-key` | Одинаковый 64-символьный образец ключа в четырёх PHP-примерах для demo.payform.ru; происхождение/отзыв не доказаны | OPEN исторически; текущий литерал заменён на `getenv('PRODAMUS_SECRET_KEY')` |
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
- `.gitleaksignore`: добавлены ровно девять fingerprint вида commit:path:rule:line для исторических Kinescope-примеров; исторические значения перепроверены локально через git show (JWT exp либо конечное многоточие). Четыре исторические находки Prodamus намеренно не исключены. Новое значение/новый коммит не совпадёт с таким fingerprint.
- Три искусственных canary на тех же разрешённых путях были обнаружены новым сканом: curl с другим токеном, реальное value-shaped значение PRIVATE_KEY_PEM и другое значение MFA fixture. Canary находятся только в игнорируемом локальном тестовом снимке; не внесены в runtime/документы.

## Проверки

| Проверка | Результат | Локальный артефакт |
|---|---|---|
| Current dir, стандартные правила, до исправлений | exit 1, 30 находок | `secret-scan-current-redacted.json` |
| Current dir, новая конфигурация, после исправлений | exit 0, 0 находок | `secret-scan-current-final-redacted.json` |
| Canary на точных исключённых путях, та же конфигурация | ожидаемый exit 1, 3/3 искусственных значения обнаружены | `secret-scan-canary-redacted.json` |
| Git history до HEAD, итоговая конфигурация и fingerprints | **exit 1, 140 коммитов, четыре открытые исторические находки Prodamus** | `secret-scan-history-final-redacted.json` |

Команды сканирования: `gitleaks dir /scan --config /scan/.gitleaks.toml --redact=100 --report-format json` и `gitleaks git /history --config /config/.gitleaks.toml --gitleaks-ignore-path /config/.gitleaksignore --log-opts=HEAD --redact=100 --report-format json`. Полные отчёты сохраняются локально с redact=100; в чат передавались только пути, правила, количества и статусы.

Конфигурация проверена по [официальной документации Gitleaks v8.24.3](https://github.com/gitleaks/gitleaks/blob/v8.24.3/README.md): extend.useDefault и rule allowlists с condition=AND. TOML разобран, 17 точных исключений проверены, глобального allowlist нет.

## Открытая операторская проверка

Четыре исторические находки Prodamus не закрыты и не добавлены в allowlist. Владелец должен установить происхождение образца и статус отзыва у провайдера; если образец принадлежал рабочему магазину, согласовать ротацию/отзыв и проверку использования. Доказательства текущего отсутствия и 0/27 совпадений не заменяют эту проверку. Ни ротация, ни переписывание Git-истории, ни тест найденного ключа здесь не выполнялись.

Итоговый history-скан сохранил только четыре строки Prodamus в коммите `b63204b9d986ed53b2ade85509c8c0eab07fac0e`. Таким образом **history gate CI остаётся красным**; текущий checkout зелёный, историческая проверка требует решения владельца.

Проверка `.github/workflows/security.yml` подтверждает: Gitleaks action получает полную историю через fetch-depth=0. Поэтому зелёный dir-скан не позволяет объявить history job зелёным.
