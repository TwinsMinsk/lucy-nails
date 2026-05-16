---
name: kinescope
description: Use when working with the Kinescope video platform — uploading and managing videos via REST API, embedding the player, configuring DRM and authorization backends, watermarks, subtitles, posters, analytics, and live streaming. Covers `api.kinescope.io` (REST), `kinescope.io/embed/...` (player), and the JWT-signed `drmauthtoken` flow for access control.
---

# Kinescope Skill

Kinescope is a video hosting and streaming platform. This skill consolidates official Kinescope documentation (10 categorized reference files) into a single navigable surface so you can quickly answer "how do I…" questions for the REST API, the embeddable player, content protection (DRM, watermarks, access restrictions), and integrations.

## When to Use This Skill

Trigger this skill whenever the task touches Kinescope. Concrete signals:

- The request mentions **Kinescope**, `kinescope.io`, `api.kinescope.io`, or a Kinescope **video ID** / **project ID**.
- You need to **embed a video** with `<iframe src="https://kinescope.io/embed/...">` and decide between plain embed, DRM-protected embed, or watermarked embed.
- You are wiring a backend to the **Kinescope authorization callback** (the request Kinescope sends to your URL when a viewer opens a DRM-protected video) and need to know the request shape and the `200`/`403` contract.
- You are signing a **`drmauthtoken`** (recommended: JWT) on your server to be passed in the embed URL.
- You are calling the **REST API** (`https://api.kinescope.io/v1/...`) to manage projects, folders, videos, posters, subtitles, annotations, analytics, or live events.
- You are uploading media — drag-and-drop in dashboard, **upload by link**, **CSV bulk import**, or **API uploader** (`https://uploader.kinescope.io/v2/init`).
- You are integrating with a static-site generator (e.g., **Hugo shortcode**) or a CMS.
- You are debugging player issues (DRM playback failure, encrypted-media not allowed, CORS / domain restriction blocks).
- You need to look up an **error response shape** (`error.code` whose first three digits mirror the HTTP status).

If the task is *only* about an unrelated video provider (Mux, Bunny, Vimeo, YouTube), skip this skill.

## Multi-Source Synthesis Note

This skill is built from **one source type** (official Kinescope documentation, `docs.kinescope.com`) split into 10 reference files by category. Confidence on individual pages is **medium** (docs were scraped, not handwritten by the user). All sources agree on the items below — there are **no detected discrepancies** between source files at this time. Where docs are silent (e.g., exact JWT claim names beyond the recommended `exp`/`aud`/`iss`), this is called out explicitly rather than guessed.

## Key Concepts

### API base & authentication
- Base URL: `https://api.kinescope.io`
- Header: `Authorization: Bearer <ACCESS_TOKEN>`
- Tokens are issued in the dashboard (**Settings → API tokens**) and are **scoped to a single workspace**. Use one token per integration so any of them can be rotated/revoked independently.
- The token must be in **UUID format** for the DRM-auth endpoints.
- **Never expose** the token in client-side code.

### Errors
- The first three digits of `error.code` always equal the HTTP status (e.g., HTTP 400 → `error.code` starts with `400…`).
- Standard error body shape: `{ "error": { "code": <number>, "message": <string>, "detail": <string> } }`.

### Pagination & ordering
- List endpoints return a `meta.pagination` block (`page`, `per_page`, `total`) and a `meta.order` block (e.g., `{ "created_at": "desc" }`).

### DRM / authorization backend (the most-asked-about piece)
- Kinescope can call **your** HTTP endpoint to decide whether a given user can play a given video.
- The viewer's identity arrives at the player via the `drmauthtoken` query param on the embed URL.
- **Recommended:** sign `drmauthtoken` as a **JWT** server-side; validate signature on your auth callback and check standard claims `exp`, `aud`, `iss`.
- Your callback returns **HTTP 200** to allow playback and **HTTP 403** to deny. 5xx responses break access checks — monitor them.
- DRM auth URL can be configured at **workspace** scope or **project** scope (project-level overrides workspace-level).

### Watermarks
- **Static**: a fixed string, passed via `?watermark=Your_text`.
- **Dynamic**: per-viewer data baked into the playback, passed via `?watermark=${user_data}`.

### Embed URL parameters (combine as needed)
- `?drmauthtoken=...` — token forwarded to your auth backend.
- `?watermark=...` — overlay text or per-viewer data.
- The `<iframe>` `allow` attribute must include `encrypted-media` for DRM playback.

### Video upload — three methods
1. **Dashboard / drag-and-drop / link** (no code).
2. **CSV bulk import** with columns `url,title`.
3. **API uploader** — `POST https://uploader.kinescope.io/v2/init` returns `{ id, endpoint }`; PUT the file bytes to `endpoint`.

## Quick Reference

The examples below are extracted verbatim from the official docs (medium confidence). They are ordered by how often they come up in real integration work.

### 1. Embed a DRM-protected video and pass a per-user token

From `developer-guides.md` and `content-protection.md` (both agree).

```html
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?drmauthtoken=${user_id}"
  width="640"
  height="360"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

Replace `${user_id}` server-side with a **signed JWT** before rendering. The `encrypted-media` permission is required for DRM playback.

### 2. Configure your authorization backend URL (workspace-wide)

From `developer-guides.md`. The `Authorization` header token must be in **UUID format**.

```bash
curl -X PUT "https://api.kinescope.io/v1/drm/auth" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/drm/authorize",
    "username": "drm_user",
    "password": "drm_password",
    "strict": false
}'
```

Project-scoped variant overrides workspace settings:

```bash
curl -X PUT "https://api.kinescope.io/v1/drm/auth/${PROJECT_ID}" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/drm/authorize",
    "username": "drm_user",
    "password": "drm_password",
    "strict": false
}'
```

Read current settings:

```bash
# Workspace
curl -X GET "https://api.kinescope.io/v1/drm/auth" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"

# Project
curl -X GET "https://api.kinescope.io/v1/drm/auth/${PROJECT_ID}" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"
```

### 3. List videos (and the standard error shape)

From `api.md`.

```bash
curl -H 'Authorization: Bearer <ACCESS_TOKEN>' \
  https://api.kinescope.io/v1/videos
```

Standard error response:

```json
{
  "error": {
    "code": 400301,
    "message": "invalid uuid format",
    "detail": "see https://en.wikipedia.org/wiki/Universally_unique_identifier"
  }
}
```

### 4. Initiate a resumable upload via the API

From `developer-guides.md`. POST returns an `endpoint` you upload bytes to.

```bash
curl --location --request POST 'https://uploader.kinescope.io/v2/init' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer ${KINESCOPE_API_TOKEN}' \
  --data-raw '{
    "filesize": 10485760,
    "type": "video",
    "title": "My Video",
    "parent_id": "e51e55a1-7615-493e-9055-10ac9cc44ccd",
    "filename": "video.mp4",
    "description": "Video description",
    "client_ip": "11.22.33.44"
}'
```

Sample response:

```json
{
  "data": {
    "id": "7127f2d7-0e96-40d0-9a03-2e987c096466",
    "endpoint": "https://eu-ams-uploader-1.kinescope.io/v2/upload/0966958f-638b-4aab-bf4a-7f9860a57a93"
  }
}
```

### 5. List projects and folders

From `developer-guides.md`.

```bash
curl --location 'https://api.kinescope.io/v1/projects' \
  --header 'Authorization: Bearer ${KINESCOPE_API_TOKEN}'

curl --location "https://api.kinescope.io/v1/projects/${PROJECT_ID}/folders" \
  --header 'Authorization: Bearer ${KINESCOPE_API_TOKEN}'
```

### 6. Bulk upload by CSV

From `catalog-and-video-management.md`. Columns are `url` and `title`.

```csv
url,title
https://example.com/video1.mp4,Video Title 1
https://example.com/video2.mp4,Video Title 2
```

### 7. Analytics: workspace overview and per-video grouping

From `catalog-and-video-management.md`.

```bash
# Overview for a date range
curl -X GET "https://api.kinescope.io/v1/analytics/overview?from=2024-01-01&to=2024-01-31" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"

# Top 10 videos by views in a date range
curl -X GET "https://api.kinescope.io/v1/analytics?from=2024-01-01&to=2024-01-31&group_by=video_id&order=views.desc&per_page=10" \
  -H "Authorization: Bearer ${KINESCOPE_API_TOKEN}"
```

### 8. Add a static or dynamic watermark to the embed

From `content-protection.md`.

```html
<!-- Static watermark: fixed text -->
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?watermark=Your_text"
  width="640" height="360" frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>

<!-- Dynamic watermark: server-rendered per-viewer data -->
<iframe
  src="https://kinescope.io/embed/pcFNnQGsD59CMKte2SQQaz?watermark=${user_data}"
  width="640" height="360" frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media;"
></iframe>
```

### 9. Enable JWT-required chat on a live event

From `developer-guides.md`.

```bash
curl --location --request PUT 'https://api.kinescope.io/v2/live/events/{{event_id}}' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer your_api_token_here' \
  --data '{
    "chat_jwt_required": true
}'
```

### 10. Hugo shortcode integration

From `integrations.md`. File path inside your theme:

```
themes/your-theme/layouts/shortcodes/kinescope.html
```

Usage in content:

```
{{< kinescope url="https://kinescope.io/pl/5ifZjJLLGYncrHYBdPNhKE" >}}
```

## Authorization Backend Flow (4 steps)

The most common Kinescope integration question. Distilled from `developer-guides.md → authorization-backend`.

1. **Embed sends the player to Kinescope** with `?drmauthtoken=<your_token>`.
2. **Kinescope POSTs JSON** to the authorization URL you registered via `PUT /v1/drm/auth` (or `…/${PROJECT_ID}`). The body carries the context (token, video, viewer info).
3. **Your backend validates the token** (signature + claims if JWT) and decides — does this user have access to this video?
4. **Your backend returns** `200` (allow) or `403` (deny). 5xx blocks access entirely; monitor and recover quickly.

Minimal access-check pseudocode:

```text
on_request(payload):
    user_id = verify_jwt(payload.drmauthtoken)         # raises on bad signature/exp
    if not user_id: return 403
    if not user_has_access(user_id, payload.video_id): return 403
    return 200
```

**Security notes (from the docs):**
- Use a **signed JWT** for `drmauthtoken` in production — raw `user_id` is replayable from the client.
- On the backend, validate `exp` (expiration), `aud` (audience), `iss` (issuer).
- DRM API token (in your `Authorization: Bearer` header to Kinescope) **must be UUID-formatted**.

## Reference Files

All references live in `references/` and were scraped from `docs.kinescope.com`. Source confidence: **medium** across the board. Page counts are from the source manifests.

| File | Coverage | When to open it |
| --- | --- | --- |
| `api.md` | REST API entry point: auth, errors, pagination, posters, subtitles, annotations, videos. | You need the canonical request/response shape for `/v1/videos/...` resources. |
| `catalog-and-video-management.md` | Projects, advanced upload (drag-drop, link, cloud, API, CSV), media file settings, analytics, built-in editor, search. | You are uploading or organizing media, or pulling analytics. |
| `content-protection.md` | DRM encryption, watermarks (static/dynamic), access restrictions (private link, password, codes, domain). | You need to lock down a video. |
| `developer-guides.md` | Authorization backend, file upload via API, live event JWT chat, general API guidelines. | Most backend integration work — start here for the auth-backend flow. |
| `getting-started.md` | Onboarding, account & workspace basics. | First-time setup. |
| `index.md.md` | Top-level docs index. | Quick navigation lookup. |
| `integrations.md` | Hugo (and other static-site / CMS) integration patterns. | You're embedding via a CMS or SSG. |
| `other.md` | Misc / uncategorized topics. | Last-resort search when nothing else matches. |
| `troubleshooting.md` | "Embedded video does not play" and similar player issues. | Player playback bugs, especially around DRM. |
| `video-player.md` | Player options, embed parameters, iframe attributes. | You're tweaking the embedded player. |

## Working with This Skill

### First-time / beginners
1. Skim **`getting-started.md`** for the dashboard model (workspace → project → video).
2. Read the **Key Concepts** section above for the API base URL, auth header, and error format.
3. Embed a video using example #1 (no DRM yet) and verify it plays.

### Backend integrators (most common path)
1. Open **`developer-guides.md`** and read the **Authorization Backend** section end-to-end.
2. Use example #2 to register your auth-callback URL.
3. Implement the callback per the **Authorization Backend Flow** section above (200/403 contract, JWT verification).
4. Use example #1 to embed with `?drmauthtoken=<signed_jwt>`.
5. Verify with `troubleshooting.md` if playback fails.

### Content / catalog operations
1. Use example #4 (resumable upload) or example #6 (CSV bulk) for ingestion.
2. Use the analytics queries in example #7 to report on consumption.
3. See `catalog-and-video-management.md` for posters, subtitles, chapters, annotations.

### Resolving conflicts
None detected across the current sources. If you find one in the future, follow this priority:
1. Codebase ground truth (if you have a working integration locally).
2. Official Kinescope docs (the source of `references/`).
3. Anything else.

## Known Discrepancies

None at this time. The 10 reference files are non-overlapping by category, and the few overlapping items (DRM iframe shape, API base URL, auth header format) match across files.

## Notes & Caveats

- Reference files were scraped; their per-page confidence is **medium**. Validate critical numbers (rate limits, exact JWT claim names beyond `exp`/`aud`/`iss`) against the live docs at `docs.kinescope.com` before shipping.
- The docs use `${VAR}` placeholders in many curl snippets. Substitute with real values; do **not** leave the literal `${...}` in production code.
- The DRM API token (`Authorization: Bearer ...` to Kinescope) must be UUID-formatted; this is distinct from the `drmauthtoken` query param (which is your viewer-scoped token, recommended JWT).
- Variable-frame-rate (VFR) source files are auto-converted to CFR on upload — set CFR in your editor in advance to avoid sync issues.

## Updating

To refresh this skill with updated documentation:
1. Re-run the docs scraper against `docs.kinescope.com` with the same configuration that produced `references/`.
2. The reference files and this skill will be rebuilt with the latest content.
