---
name: prodamus
description: Use when integrating with Prodamus (Продамус) — Russian payment gateway by ООО «Продамус». Covers payment-page (`*.payform.ru`) link generation, HMAC-SHA256 signature for the `Sign` header, webhook (`urlNotification`) handling, recurrent/subscription payments (клубная система), REST API (`setActivity`, `setSubscriptionDiscount`, `setSubscriptionPaymentDate`), demo mode (`demo_mode=1`, secret + `demo` suffix), payment-method codes (Tinkoff/Sber/OTP/«Долями»/«ВсегдаДа»/«Prodamus Частями»), and CMS / chat-bot / online-school integrations.
---

# Prodamus Skill

Prodamus (ООО «Продамус», `prodamus.ru`) is a Russian payment aggregator focused on self-employed, sole proprietors and Russian legal entities. It provides a hosted payment page (`<merchant>.payform.ru`), a webhook-based notification flow, an embeddable widget, and a REST API for managing subscriptions.

This skill consolidates the official help documentation from `help.prodamus.ru` so an agent can implement and debug integrations without crawling the web each time.

## When to Use This Skill

Use this skill when you need to:

- **Generate a payment link** to `https://<merchant>.payform.ru/` from a backend (course/product checkout, subscription start, donation, etc.).
- **Verify or implement a webhook** (`urlNotification`) and the `Sign` header — including the awkward Prodamus signature algorithm (sorted JSON, `/` escaping, HMAC-SHA256).
- **Wire up subscriptions / recurrent billing** through Prodamus's клубная система or the REST API (`setActivity`, `setSubscriptionDiscount`, `setSubscriptionPaymentDate`).
- **Pick or filter payment-method codes** (Tinkoff, Sber, OTP, «Долями», «ВсегдаДа», «Prodamus Частями v3.0», foreign cards, СБП, T-Pay, Yandex Pay, Yandex Split, …) when configuring CMS modules or building UI.
- **Test payments locally** with demo mode (`demo_mode=1`) and the published Visa/MasterCard/МИР test cards.
- **Integrate with a CMS or chat-bot platform** (Bitrix, WordPress, Opencart, Tilda, Taplink, Linkrr, Creatium, EdproBiz, Skillspace, BotHelp, Senler, ActiveUsers, …) by re-using the canonical `URL уведомлений` + `Секретный ключ` pattern.
- **Configure fiscal / cashier behavior** (Atol ФФД 1.05 hookup, «Мой налог» integration for self-employed, offer placement, full-settlement receipt control).
- **Onboard a new merchant** (заявка → анкета → оплата подключения → кабинет) or change requisites/accounts.

> Trigger words: `prodamus`, `продамус`, `payform.ru`, `urlNotification`, `signature`, `Sign header`, `demo_mode`, `setActivity`, `setSubscriptionDiscount`, `setSubscriptionPaymentDate`, «клубная система», «рекуррент», «Prodamus Частями», `do=pay`, `products[0][price]`.

## Source Inventory & Confidence

This skill is built from **one** source type (official help documentation at `help.prodamus.ru`), with cross-checks against the live Prodamus integration in this repository.

| Reference file | Pages | Confidence | What's inside |
| --- | --- | --- | --- |
| `references/help_documentations_pf1.md` | 183 | medium (official help, partially summarized) | The bulk of articles: onboarding, payment-method catalog, integrations with 30+ services, REST API method list, recurrent payments, partner program, FAQ, case studies. Large file (~1 MB) — read targeted sections, do not load wholesale. |
| `references/payform.md` | 5 | medium (official help) | Atol cashier hookup (ФФД 1.05), offer/договор placement, «Мой налог» self-employed integration, E-AutoPay integration, support contacts. |
| `references/other.md` | 1 | medium (marketing) | Background on the company, supported methods, fees, country coverage, promo-code basics. Useful for *concept* questions, not for technical wiring. |
| `references/index.md` | – | low (auto-generated index) | Skip; use the per-source files above. |

**No GitHub-issue dataset and no PDF dataset** were supplied — there is nothing to cross-check against real-world bug reports beyond the local codebase.

## Key Concepts

- **Платёжная страница (payment page)** — a per-merchant URL of the form `https://<id>.payform.ru/`, where `<id>` is the merchant identifier (e.g. `https://edu2.payform.ru/`). All checkout links target this domain.
- **Секретный ключ (secret key)** — generated in the merchant cabinet under «Настройки». Used both for **signing** outbound payment links and for **verifying** inbound webhooks. The same key is what every CMS integration screen asks for.
- **`urlNotification`** — the webhook URL Prodamus will POST to after a payment event. Settable globally in «Настройки» or per-link via the `urlNotification` parameter. Prodamus signs the body with HMAC-SHA256 and sends the digest in the **`Sign`** header.
- **`callbackType=json`** — send `callbackType=json` on link generation so the webhook arrives as JSON instead of form-encoded; this is the recommended mode for modern backends.
- **`demo_mode=1`** — turns a single link into a test transaction. Test cards (Visa 4006 8009 0096 2514, MC 5469 9801 0004 8525, МИР 2202 2050 0001 2424, GazpromBank 4242 4242 4242 4242) only work in demo mode. **Important quirk:** in demo mode, the webhook signature is computed using `secret_key + "demo"` (suffix), not the plain secret. Verifiers must try both.
- **Клубная система / Recurrent** — Prodamus's native subscription system. Subscriptions are configured in the cabinet; the REST API exposes `setActivity` (activate/deactivate), `setSubscriptionDiscount` (apply discount to upcoming charges), and `setSubscriptionPaymentDate` (move the next charge date).
- **Виджет (widget)** — JS embed (`https://widget.prodamus.ru/src/init.js`) for Tilda/Taplink/Linkrr/Creatium and similar site builders; lets the checkout open in an overlay without leaving the site.
- **Льготный период** — onboarding gives a 3-month / 100 000 ₽ no-commission window on RUB-card / СБП / SberOnline / requisites payments. Worth knowing when estimating fees in tooling.

## Quick Reference

> Most examples are taken from official docs. Where a concrete signing example was missing in docs, the snippet is marked **"From codebase"** and reflects the working integration in `backend/app/services/prodamus_service.py` of this repo.

### 1. Embed the Prodamus widget on a Tilda/Taplink/Creatium-style site (official docs)

```html
<script>
  window.prodamusDomain         = "name.payform.ru";   // your merchant page
  window.prodamusCurrency       = "rub";               // rub|kzt|usd|eur
  window.prodamusConfirmationText = "Перейти к оплате";
  window.prodamusSys            = "taplink_eoo";       // platform tag
  window.successPaymentAddress  = "https://success-url";
  window.errorPaymentAddress    = "https://error-url";
</script>
<script src="https://widget.prodamus.ru/src/init.js" defer></script>
<link rel="stylesheet" href="https://widget.prodamus.ru/src/init.css" />
<script defer src="https://integration.prodamus.ru/taplink/script"></script>
<script src="https://integration.prodamus.ru/common/custom"></script>
```

### 2. Open the widget from a custom button (official docs)

```html
<a href="javascript:prodamusRedirectPay(123, 'rub',
        'https://success-url', 'https://error-url');">
  Pay now
</a>
```

`123` is the price; currency can be `'rub'`, `'kzt'`, `'usd'`, `'eur'`. Remove `success-url` / `error-url` if no post-payment redirect is needed.

### 3. HMAC-SHA256 signature algorithm — the canonical 5-step recipe (From codebase, derived from official docs)

```python
import hashlib, hmac, json

def _to_str(value):
    # 1) recursively stringify, 2) sort keys
    if isinstance(value, dict):
        return {k: _to_str(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_to_str(v) for v in value]
    return str(value)

def prodamus_sign(data: dict, secret: str) -> str:
    sorted_data = _to_str(data)
    # 3) compact JSON, 4) escape forward slash
    payload = json.dumps(sorted_data, ensure_ascii=False, separators=(",", ":")) \
                  .replace("/", "\\/")
    # 5) HMAC-SHA256
    return hmac.new(secret.encode("utf-8"),
                    payload.encode("utf-8"),
                    hashlib.sha256).hexdigest()
```

This exact algorithm is what produces the `signature` query param on outbound links **and** what Prodamus puts into the `Sign` header on the webhook.

### 4. Generate a payment link (From codebase — pattern used in production)

```python
params = {
    "do": "pay",
    "products[0][name]":     course_name,
    "products[0][price]":    str(price),
    "products[0][quantity]": "1",
    "products[0][type]":     "course",
    "urlSuccess":      f"{frontend}/payment-success",
    "urlReturn":       f"{frontend}/#pricing",
    "urlNotification": f"{backend}/api/payments/webhook",
    "callbackType":    "json",
    "order_id":        order_id,
    "customer_email":  email.lower(),
}
if environment != "production":
    params["demo_mode"] = "1"

params["signature"] = prodamus_sign(params, PRODAMUS_SECRET_KEY)
link = f"https://{merchant}.payform.ru/?{urlencode(params, quote_via=quote)}"
```

### 5. Verify a webhook (From codebase) — handle the demo-suffix quirk

```python
def verify_signature(payload: dict, signature: str, secret: str) -> bool:
    if hmac.compare_digest(prodamus_sign(payload, secret), signature):
        return True
    # Demo payments sign with secret + "demo"
    if hmac.compare_digest(prodamus_sign(payload, secret + "demo"), signature):
        return True
    return False
```

Header to read: `Sign`. If it is missing, reject the request — Prodamus always sends it.

### 6. REST API surface (official docs — `payform/integracii/rest-api-1`)

```
Endpoint format : https://{домен}/rest/{метод api}/
HTTP methods    : GET or POST

setActivity                — activate/deactivate a subscription
setSubscriptionDiscount    — set discount for upcoming subscription charges
setSubscriptionPaymentDate — set the next charge date for a subscription
```

The docs do **not** expand request/response schemas in the corpus; for full body shapes consult `help.prodamus.ru/help_documentations_pf1/payform/integracii/rest-api-1` and the «Техническая документация по автоплатежам» link in the cabinet.

### 7. Demo / test cards (official docs)

```
МИР          : 2202 2050 0001 2424   exp 05/35   CVV 669
MasterCard   : 5469 9801 0004 8525   exp 05/26   CVV 041   3DS 111111
Visa         : 4006 8009 0096 2514   exp 05/30   CVV 706   3DS 111111
Монета       : 2200 2400 0000 0006   exp 12/24   CVV 123
GazpromBank  : 4242 4242 4242 4242   exp 12/30   CVV 123
```

To force demo mode for a single link via the API include `demo_mode=1` in the params.

### 8. Common CMS integration shape (official docs — recurring pattern)

Every CMS/online-school integration page (Bitrix, WordPress, Opencart, Skillspace, School-Master, E-AutoPay, EdproBiz, …) follows the same three fields:

```
URL платёжной формы   : https://<id>.payform.ru/
URL уведомлений       : https://<your-cms>/path/prodamus/notification
Секретный ключ        : <copied from Prodamus → Настройки>
```

If you are wiring up a new platform that isn't covered explicitly, copy this triple — it is the integration contract.

### 9. Subscription / club integration (official docs)

```
Cabinet steps:
1. Подписки → создать подписку (цена + длительность в днях)
2. Скопировать ID подписки
3. URL-адрес для уведомлений о совершении оплат по подписке
   → точка приёма вебхуков о повторных списаниях
4. Передать ID подписки в стороннюю платформу (BotHelp / EdproBiz / Asay / …)
```

Length of subscription is **always measured in days** on the Prodamus side — match that unit in downstream systems.

### 10. Payment-method codes you'll actually need

Selected, high-signal codes from the Bitrix integration list (full catalog in `references/help_documentations_pf1.md`):

```
fresh_installment_0_0_{6|10|12|18|24|36}    — рассрочка «Фреш Кредит»
vsegdada_installment_0_0_{3|4|6|10|12|18|24|36}  — рассрочка «ВсегдаДа»
vsegdada_creditline_0_0_{3|4|6|10|12|24}    — кредит «ВсегдаДа»
proonline_installment_0_0_{6|12|18|24}      — рассрочка ProOnline (RU/KG)
proonline_installment_kz_0_0_{6|12|18|24}   — рассрочка ProOnline (KZ)
direct_installment_0_0_{3|6|10|12|18|24|36} — рассрочка от банков-партнёров
TINKOFF_API_SUBSIDIZED_HIGH_INSTALLMENT_0_0_{3|4|6|10|12|18|24|36}  — Т-Банк
otp_installment_0_0_{3|4|6|10|12|18|24}     — ОТП Банк
sbrf_installment_0_0_{6|10|12|18|24|36}     — Сбербанк
broker_installment_0_0_{6|10|12|24}         — брокерская рассрочка
installment_10_28:v3.0                      — Prodamus Частями v3.0
```

Separator for «Список доступных платёжных систем» in Bitrix is the pipe `|`.

## Reference Files

`references/` holds the full doc dump. Suggested reading order:

1. **`references/help_documentations_pf1.md`** (medium confidence, ~1 MB, 183 pages).
   Sectioned alphabetically by article title. Most-referenced anchors:
   - `## Rest API | Prodamus` — REST method list (`setActivity`, `setSubscriptionDiscount`, `setSubscriptionPaymentDate`).
   - `## 1С-Битрикс | Prodamus` — full payment-method code catalog.
   - `## Какие методы оплаты поддерживает Prodamus | Prodamus` — narrative description of all supported methods with limits and fees.
   - `## Как провести тестовую оплату | Prodamus` — demo mode + test cards.
   - `## Как принимать рекуррентные платежи через Prodamus | Prodamus` — клубная система vs. external auto-charge robots.
   - `## Как подключить Prodamus | Prodamus` — onboarding, fees, льготный период.
   - `## Как отправить клиенту обучающий материал после оплаты заказа | Prodamus` — common online-school post-payment flow.
   - Per-platform integration pages (Tilda, Taplink, Linkrr, Creatium, BotHelp, Senler, ActiveUsers, EdproBiz, Skillspace, Antitreningi, …).
2. **`references/payform.md`** (medium confidence, 5 pages).
   Lightweight overlay covering Atol cashier integration (ФФД 1.05), offer placement, «Мой налог» self-employed flow, and the E-AutoPay integration. Read in full when fiscalization or self-employed onboarding is in scope.
3. **`references/other.md`** (medium confidence, 1 page).
   Marketing-flavored overview — supported methods, country coverage, fees, integrations list. Useful for stakeholder-facing answers and high-level scoping, not for implementation details.
4. **`references/index.md`** (low confidence).
   Stub; skip.

Because `help_documentations_pf1.md` is large, prefer `Grep` on the references directory over reading whole files — the table of contents above lists the heading anchors you can pattern-match against.

## Working with This Skill

### Beginner — "I just need to take a payment"
1. Pick the right surface:
   - Site builder (Tilda/Taplink/Linkrr/Creatium) → use the widget (Quick Reference §1–§2).
   - Custom backend → generate a signed payment link (Quick Reference §3–§4).
2. Set `urlNotification` to a backend endpoint and verify the `Sign` header on every webhook (Quick Reference §5).
3. Turn on `demo_mode=1` in non-prod, use the published test cards (Quick Reference §7), and **remember the demo-suffix signature quirk**.

### Intermediate — CMS / online-school integration
1. Find the per-platform section in `references/help_documentations_pf1.md` (use `Grep` for the platform name).
2. Apply the canonical triple: payment-page URL, notification URL on the CMS side, secret key (Quick Reference §8).
3. For subscriptions, also paste the secret into «URL адреса для уведомлений о совершении оплат по подписке» and pass the subscription ID downstream (Quick Reference §9).

### Advanced — Recurrent billing / programmatic subscription control
1. Decide between клубная система Prodamus (managed in the cabinet) and an external auto-charge robot — see the «Как принимать рекуррентные платежи» article. If you don't need custom timing, prefer the клубная система.
2. Drive lifecycle via REST: `setActivity` to (de)activate, `setSubscriptionDiscount` for retention offers, `setSubscriptionPaymentDate` to shift the next charge.
3. For initial and recurrent payment webhooks, **both arrive at the same `urlNotification`** — distinguish by the subscription-id and `payment_type` fields in the payload.

### Navigating multi-section references
- Article headings always end with ` | Prodamus`. Grep for `^## .* | Prodamus` to enumerate the table of contents.
- Sections are auto-extracted excerpts, not complete pages — when wording feels truncated, follow the `**URL:**` link inside the section.

### Resolving conflicts
Within this skill there is only one source family (official help docs). When the docs and the real Prodamus integration in this repo disagree:

1. **Code in `backend/app/services/prodamus_service.py` wins** for *signing details* and *webhook header semantics* — it was validated against live demo and production traffic.
2. **Docs win** for *cabinet-side behavior*, *fee schedules*, and *list of supported methods/banks*, which the code cannot observe.

## Known Discrepancies / Gotchas

These come from real integration work and are not always explicit in the docs:

- **Demo signatures use `secret + "demo"`.** The docs only hint at this; the verifier must try both. (See Quick Reference §5.)
- **Signature is over a flat key/value dict, with `/` escaped.** The literal escaping step (`"/" → "\/"`) is easy to miss — without it, every signature mismatches.
- **`callbackType=json` is recommended.** Without it, the webhook arrives form-encoded, which then has to be reconstructed into a dict before signing, multiplying the chances of a sort/encoding bug.
- **`order_id` is your idempotency anchor.** The docs do not promise that Prodamus deduplicates retries — your webhook handler must.
- **Subscription length is in days everywhere on the Prodamus side**, even when the downstream UI says "month". Convert at the boundary.
- **«Prodamus Частями» uses a versioned method code** (`installment_10_28:v3.0`) — that colon-versioning is unusual and must be preserved verbatim.
- **Foreign-card fee is flat 10%** (min 100 ₽) per docs — significantly higher than the base RU rate of 3.8%. Surface this in cost estimates.

## Notes

- Source documentation language is **Russian**; UI labels, error messages and parameter names in the docs are quoted in Russian to match the merchant cabinet.
- This skill was generated from a docs scrape and supplemented with insights from the local Prodamus service implementation.
- Reference files are excerpts — if a section ends abruptly, follow the `**URL:**` link.

## Updating

To refresh this skill with the latest documentation:

1. Re-run the scraper against `help.prodamus.ru` with the same source-type configuration.
2. Re-generate `references/*.md` and review diffs — payment-method codes and REST endpoint lists change occasionally.
3. Re-check Quick Reference §5–§6 against `backend/app/services/prodamus_service.py` to keep the signing recipe in sync with the live integration.
