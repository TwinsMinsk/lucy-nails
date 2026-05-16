---
name: prodamus-actions
description: Use to perform real Prodamus operations from Claude — generating signed checkout URLs, verifying webhook signatures, and calling the REST subscription endpoints (setActivity, setSubscriptionPaymentDate, setSubscriptionDiscount). Pairs with the `prodamus` knowledge skill which explains the protocol; this skill is the executor. Wraps `scripts/prodamus/actions.py` (standalone Python, no backend dependencies).
---

# Prodamus actions

Companion to the `prodamus` knowledge skill. The knowledge skill answers "how does Prodamus work" — this one **does** things, by shelling out to `scripts/prodamus/actions.py`.

## When to trigger

- User asks to **generate a payment link** ("дай ссылку на оплату курса X за 5900", "make a checkout URL for tariff support").
- User asks to **verify** a webhook payload (debugging a 403 from the backend, comparing the `Sign` header against the body).
- User asks to **manage a subscription**: pause/resume, push next-payment date, apply discount.
- User asks to **reproduce a demo payment** (`demo_mode=1`) end-to-end.

If the request is purely about *how* Prodamus signs requests or *which* payment-method code to pass, prefer the `prodamus` knowledge skill instead — no need to shell out.

## Prerequisites

The CLI reads credentials from environment variables (auto-loads from repo `.env` when missing). Required keys:

- `PRODAMUS_URL` — base payment-page, e.g. `https://lucysmirnova.payform.ru/`
- `PRODAMUS_SECRET_KEY` — merchant secret (Settings → API в кабинете)

Both are already in the repo `.env`. The CLI is standalone — no `backend/.venv` activation needed, just `requests` on the system Python.

## Commands

All commands print JSON or a URL to stdout. Non-zero exit on signature mismatch or non-2xx REST response.

### `link` — build a signed checkout URL

```
python scripts/prodamus/actions.py link \
    --course "<product name shown on payform>" \
    --price <amount_in_rub> \
    [--email <customer@example.com>] \
    [--phone <+79XXXXXXXXX>] \
    [--order-id <internal_order_id>] \
    [--success-url <return after success>] \
    [--return-url <return after cancel>] \
    [--notification-url <webhook URL>] \
    [--demo]
```

When to use:
- One-off test of a checkout URL ("дай тестовую ссылку на 1 руб").
- Reproducing a customer's exact link to debug a payment.
- Generating a manual link for a customer outside the normal flow.

Notes:
- Pass `--demo` for any non-production test. Demo links use Visa `4006 8009 0096 2514` (any future expiry, CVV `123`).
- The default `urlNotification` is **not** set by the CLI. If the user wants the webhook fired against our backend, pass `--notification-url https://api.lucysmirnova.ru/api/payments/webhook` (production) or the local equivalent.
- `--tariff self|support` is informational; Prodamus does not see this param. The course product on the Prodamus side is identified only by `products[0][name]`.

### `verify-sign` — check a webhook `Sign` header

```
python scripts/prodamus/actions.py verify-sign \
    --sign <hex from Sign header> \
    --body <JSON literal | @file.json>
```

Tries the production secret first, then `secret_key + "demo"` (Prodamus's documented demo quirk). Prints which one matched, or both expected hexes on mismatch.

When to use:
- Backend logs say "Prodamus signature mismatch" — feed the raw body + Sign header here to confirm whether the secret rotated, the body got mutated, or it was a demo call.
- Manually re-replaying a webhook from a saved curl dump.

### Subscription REST methods

All three accept one auth selector and a subscription id. Pick exactly one of `--profile <id>`, `--vk-user-id <id>`, `--phone +79...`.

```
# Activate / deactivate a club subscription
python scripts/prodamus/actions.py set-activity \
    --subscription <sub_id> --profile <profile_id> --active 1|0

# Move the next-charge date forward (date must be in the future)
python scripts/prodamus/actions.py set-payment-date \
    --subscription <sub_id> --profile <profile_id> --date YYYY-MM-DD

# Apply discount to the next N upcoming charges
python scripts/prodamus/actions.py set-discount \
    --subscription <sub_id> --profile <profile_id> \
    --discount 20 --discount-type percent --count 1
```

When to use:
- "Поставь подписку 1234 на паузу" → `set-activity --active 0`.
- "Сдвинь следующее списание клиента N на месяц вперёд как бонус" → `set-payment-date --date <new>`.
- "Дай 50% скидку на следующее списание" → `set-discount --discount 50 --discount-type percent --count 1`.

All three POST to the Prodamus `*.payform.ru/rest/<method>/` endpoint and dump the JSON response (including `status_code`). A non-2xx exit is treated as failure.

## Safety

- These are **production-acting** commands. Don't run subscription writes (`set-*`) in a test loop. Always confirm the subscription id with the user (or grep `purchases` in the DB) before mutating.
- The `link` command alone is harmless (it just signs a URL). Generating a link does **not** charge anything until the customer pays on Prodamus.
- The CLI does not read or write the local DB. Any state change is on Prodamus's side; the local backend only learns about it through the webhook.

## Troubleshooting

- `ERROR: --prodamus-url not given and PRODAMUS_URL not in env` → `.env` is missing the key or wasn't found; rerun from repo root.
- `MISMATCH` from `verify-sign` → check that the body file is byte-identical to what hit the backend (no re-pretty-printing) and that the secret in `.env` matches the production merchant cabinet.
- REST returns `error: signature` on `set-*` → the subscription / profile id might be wrong, or the secret has rotated. Re-derive the link signature with `link --demo` first to confirm the secret end-to-end.
