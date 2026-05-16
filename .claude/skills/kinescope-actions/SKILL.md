---
name: kinescope-actions
description: Use to debug & verify Kinescope DRM authorization-backend setup — sign test drmauthtokens (RS256), decode/verify a JWT, list registered JWKs on the workspace, inspect the DRM auth webhook config. Pairs with the `kinescope` knowledge skill (concepts + REST reference) and the Kinescope MCP server (which handles content management but not DRM setup). Wraps `scripts/kinescope/drm_actions.py` plus the existing `scripts/kinescope/setup_drm.py` / `put_drm_auth_from_env.py`.
---

# Kinescope DRM actions

Companion to the `kinescope` knowledge skill. The knowledge skill answers "how does Kinescope DRM auth work" — this skill **performs** the runtime/debug operations that the Kinescope MCP server does not expose: signing test JWTs locally, decoding incoming tokens, and reading the workspace-level JWK/webhook config.

For **media management** (videos, projects, analytics) use the `kinescope` MCP server directly instead.

## When to trigger

- Debugging a Kinescope DRM playback failure ("403 from auth backend", "Decrypt failure", "DRM widevine init failed").
- The user wants to **sign a one-off `drmauthtoken`** to test playback manually in a browser (skipping the backend `/api/integrations/kinescope/drm/authorize` route).
- The user asks **which JWKs are currently registered** on the workspace, or wants to plan a key rotation.
- Verifying that the configured DRM webhook URL on Kinescope's side still matches production.
- Sanity-checking an incoming JWT (e.g. one captured from a webhook log) — decoded claims, signature validity.

For one-shot setup or rotation (generate new keypair, upload JWK, set webhook), use the existing scripts in `scripts/kinescope/` directly — see "Related scripts" below.

## Prerequisites

The CLI auto-loads from repo `.env` when keys are missing:

- `KINESCOPE_API_KEY` — workspace token (for `list-jwks` / `get-drm-auth`).
- `KINESCOPE_PROJECT_ID` — project UUID (for `get-drm-auth`).
- `KINESCOPE_JWT_PRIVATE_KEY_PEM` (inline, `\n`-escaped) **or** `KINESCOPE_JWT_PRIVATE_KEY_PATH` — needed for `sign-token` and `decode-token --verify`.
- `KINESCOPE_JWK_KID` — `kid` header value (used when signing).
- `KINESCOPE_DRM_TOKEN_TTL_SECONDS` (optional, default 300).
- `BACKEND_URL` (optional, used as `iss` claim; defaults to `lucy-nails`).

Python deps: `python-jose[cryptography]`, `cryptography`, `requests` — all already in `backend/requirements.txt`. The CLI does **not** import any backend modules; runs on a bare Python.

## Commands

### `sign-token` — locally sign a test `drmauthtoken`

```
python scripts/kinescope/drm_actions.py sign-token \
    --user-id <whatever string represents the viewer> \
    [--lesson-id <optional lesson>] \
    [--email <optional>] \
    [--video-id <Kinescope video id>] \
    [--ttl-seconds 300] \
    [--kid <override kid>] \
    [--issuer https://api.lucysmirnova.ru] \
    [--pem-path backend/secrets/kinescope_drm_private.pem] \
    [--print-embed | --print-token]
```

By default prints full JSON with `token`, decoded `payload`, `kid`, optional `embed_url`. Use `--print-embed` (requires `--video-id`) for a paste-into-browser link, or `--print-token` to pipe into another tool.

When to use:
- **Smoke test the auth backend** end-to-end: sign with the same private key the prod backend uses, paste the embed URL into a fresh browser tab, watch the backend log for the `/drm/authorize` POST and confirm a 200.
- **Generate a one-off "magic link"** for a customer when the standard flow is broken.
- **Reproduce a customer's exact token** by passing the same `user_id` and `lesson_id` claims, then compare against what the backend produces.

### `decode-token` — inspect a JWT

```
python scripts/kinescope/drm_actions.py decode-token \
    --token "eyJhbG..."     # or @path/to/token.txt
    [--verify]              # verify signature using local private key → derived public key
    [--issuer ...] [--audience ...] [--pem-path ...]
```

Without `--verify`, prints decoded header + claims **without checking signature** (useful for "is this token even readable?"). With `--verify`, derives the public key from the configured private PEM and checks signature + standard claims (`exp`, `iat`, `aud`, `iss`).

When to use:
- A token from a Kinescope webhook log → want to see `user_id`/`lesson_id`/`exp` without setting up backend env.
- Suspect the prod private key rotated → verify whether a recent token still validates against the local PEM.

### `list-jwks` — what kids does Kinescope know about?

```
python scripts/kinescope/drm_actions.py list-jwks
```

Hits `GET /v1/jwk`. Returns each registered JWK with `kid`, `expires_at`, `created_at`, RSA modulus.

When to use:
- Before running `setup_drm.py` to rotate — confirm what's already there, pick a non-clashing kid.
- After rotation — confirm new kid is live alongside (or instead of) the old one.
- Check `expires_at` so you don't get a surprise outage when a key auto-expires.

### `get-drm-auth` — what webhook does Kinescope call?

```
python scripts/kinescope/drm_actions.py get-drm-auth [--project-id <override>]
```

Hits `GET /v1/drm/auth/<project_id>`. Returns the configured `url`, `username`, `password` (Basic Auth Kinescope sends), `strict` flag, timestamps.

When to use:
- Sanity-check after a backend domain change ("does Kinescope still know to hit `api.lucysmirnova.ru`?").
- Diagnose "playback works in dev, fails in prod" — webhook URL mismatch is the #1 cause.
- Verify the Basic Auth credentials match `KINESCOPE_DRM_BASIC_USER` / `KINESCOPE_DRM_BASIC_PASS` in production env.

⚠️ The response contains the Basic Auth password in plain text. Do not paste this output anywhere public.

## Related scripts (already in the repo — not part of this CLI)

| Script | What it does | When to use |
|---|---|---|
| [`scripts/kinescope/setup_drm.py`](../../scripts/kinescope/setup_drm.py) | Generate RSA-2048 keypair → save PEM → upload public JWK → PUT `/v1/drm/auth/<project>` (one-shot full setup) | First-time DRM setup, key rotation. **Mutates Kinescope state.** |
| [`scripts/kinescope/put_drm_auth_from_env.py`](../../scripts/kinescope/put_drm_auth_from_env.py) | Re-PUT the webhook URL + Basic Auth from current `.env` | After moving backend domain / changing Basic Auth password. |

`drm_actions.py` is purely read/sign-side; it does not write to Kinescope. For any mutation (new key, new webhook URL) defer to the two scripts above.

## Safety

- `sign-token` produces a real, valid JWT signed with the production private key. Treat the output as a credential — short-lived (default 5 min), but anyone with it can play protected videos as the named `user_id` for that window. Do not paste full tokens into chat tools or screenshots.
- `decode-token --verify` reads but never writes; `list-jwks` and `get-drm-auth` are read-only.
- All four commands hit production Kinescope API. There is no separate sandbox environment for DRM config.

## Troubleshooting

- `ERROR: private key not found` → `.env` lacks `KINESCOPE_JWT_PRIVATE_KEY_PEM`/`PATH`; pass `--pem-path backend/secrets/kinescope_drm_private.pem` explicitly.
- `decode-token --verify` raises `Signature verification failed` → the JWT was signed with a different private key than the one in env. Check `kid` in the token header vs `list-jwks` output to identify which key was used.
- `get-drm-auth` returns 404 → project id is wrong, or DRM auth was never registered for this project. Run `setup_drm.py` (or `put_drm_auth_from_env.py` if keys already exist).
- Playback works in browser when you paste the URL from `sign-token --print-embed` but fails through the normal app flow → the issue is upstream of DRM (probably how the app constructs `drmauthtoken`), not in DRM itself.
