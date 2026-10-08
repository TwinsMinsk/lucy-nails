# Launch operations — 8 October 2026

Status: local configuration and synthetic recovery prepared; isolated remote PostgreSQL 17 and Redis created. External staging, cron, alerts, counter, real payment and production deployment are not accepted by this document.

## Isolated Railway staging

Create an empty environment with PostgreSQL 17, dedicated Redis, backend, outbox worker and frontend. Do not duplicate production secrets/data. Separate domains, JWT/MFA/monitoring/payment/DRM keys, demo payment form, email destinations, owner chat, cookies and storage are required.

| Service | Root | Config file | Gate |
| --- | --- | --- | --- |
| Backend | `/backend` | `/backend/railway.toml` | `/health`, startup migrations |
| Worker | `/backend` | `/ops/railway/worker.toml` | Redis heartbeat |
| Frontend | `/frontend` | `/frontend/railway.toml` | `/`, build-time environment |
| Backup | `/` | `/ops/railway/backup.toml` | 01:00 UTC daily, external full backup |

These TOML files describe the intended legacy service settings; they do not prove effective Railway settings. On 8 October the API rejected assigning railwayConfigFile to new staging services because Config as Code is deprecated. Per-service root, Railpack builder, build/start command, restart policy and frontend/API healthchecks were applied directly and read back on staging. Existing legacy services still read TOML until the documented 1 December 2026 cutoff; migrate to Infrastructure as Code before that date. See [official migration guide](https://docs.railway.com/infrastructure-as-code#migrating-from-config-as-code). Production settings remain a separate controlled rollout step. Remote staging uses `ENVIRONMENT=staging`, `DEBUG=false`, `PRODAMUS_DEMO_MODE=true` with a separate form. It enforces the production security checks and requires an isolated cookie/domain namespace, e.g. frontend `staging.lucysmirnova.ru`, API `api.staging.lucysmirnova.ru`, `COOKIE_DOMAIN=staging.lucysmirnova.ru`. Production continues to reject demo payments. Keep checkout disabled until isolation and synthetic fixtures are reviewed.

Frontend build variables: API URL, site URL, operator-provided Metrika counter ID (see frontend env template). Verify configured checkout/purchase goals with consented UTM journeys. Missing counter remains an advertising gate.


### Current remote staging preparation

Environment `f19a31c5-d7fd-496a-a2e5-c13e9998ab5b` is isolated from production. PostgreSQL 17 (`Postgres17-staging`) and a dedicated Redis are running on separate volumes. Backend, frontend and worker shells exist; this is not a healthy application deployment yet. An earlier template provisioned PostgreSQL 18 on a different fresh volume; it is unused and must not be downgraded in place.

Custom domains are registered but DNS/certificates are pending: `staging.lucysmirnova.ru` and `api.staging.lucysmirnova.ru`. Missing isolated payment/video/Telegram configuration remains explicit; production secrets are not copied and placeholder keys do not establish provider readiness.

Mailpit v1.31.4 is deployed successfully only in staging, with a dedicated `/data` volume and private host `mailpit-staging.railway.internal`. Backend/worker SMTP settings were verified in memory; apps remain undeployed, so end-to-end email delivery is not yet accepted. Use a private authenticated Mailpit SMTP sink on port 1025 and an authenticated UI on 8025, with its own volume. Configure bcrypt htpasswd values for `MP_UI_AUTH` / `MP_SMTP_AUTH`, `MP_SMTP_AUTH_ALLOW_INSECURE=true`, `MP_DEMO_MODE=true`, and no relay/forward settings. Backend and worker use the matching SMTP credentials, empty `RESEND_API_KEY`, and `SMTP_START_TLS=false` only with the private `*.railway.internal` host. Production rejects disabling STARTTLS. Mail capture proves queue delivery to the sink, not receipt in a real customer's inbox.

A Railway Bucket does not currently provide the required server-side encryption, versioning, lifecycle and object-lock guarantees. Use an external S3 provider with verified encryption/versioning and separate writer/restore-reader permissions. No external bucket or schedule is accepted until actual credentials, uploads source and restore proof exist.

### Production pre-rollout findings

Read-only checks on 8 October found no fresh native snapshot: PostgreSQL had an expired August copy, backend uploads had no copies, and neither volume had a backup schedule. The actual uploads path is `/app/data/uploads` on the backend `/app/data` volume. Checkout is disabled both by environment and absence of a DB override.

Attempts to create native snapshots through the authenticated Railway API returned `Not Authorized` for both correct volume-instance IDs. No snapshot success is claimed. Obtain a fresh copy through an authorized Railway operator, or an existing authenticated read-only pg_dump/SFTP export, before production migration. Native snapshots are limited to the same project/environment and remain a pre-rollout fallback, not the required independent external backup.

## Monitoring

Configure an external uptime monitor every 30 seconds, alert after two consecutive failures, and test failure/recovery delivery:

1. Frontend `/` and API `/health`: HTTP 200.
2. API `/health/operations`: HTTP 200, header `X-Monitoring-Token` from a separate random `MONITORING_TOKEN` of at least 32 characters.
3. Operational probe exposes only counts. HTTP 503 means worker heartbeat missing (120s TTL), notification pending for >120s, dead letters, or DB/Redis unavailable. API and worker must share the environment's Redis; environments must not share Redis.
4. Monitor external backup freshness independently: a complete archive and checksum younger than 24 hours. Healthy API does not prove fresh backups. Alerting belongs outside the app's Railway failure domain.

Heartbeat proves loop liveness; queue age and delivery ledger prove notifications. A dead letter needs operator resolution, not falsely marking it sent.

## Complete backup and recovery

The image uses PostgreSQL 17. Configure `DATABASE_URL`, `BACKUP_REQUIRE_S3=true`, `BACKUP_S3_URI`, `BACKUP_S3_SSE=AES256` or `aws:kms`, restricted AWS credentials, `BACKUP_REQUIRE_UPLOADS=true`, `BACKUP_UPLOADS_DIR`, and a nonempty `BACKUP_UPLOADS_MARKER`. An operator must place a regular, non-symlink `.backup-source-marker` with that identity on the actual uploads volume or its verified snapshot. The backup job checks it before pg_dump and never creates the marker automatically. The manifest records source identity and upload file count; an empty real marked directory is accepted. Enable provider bucket versioning/retention and prohibit the writer from deleting previous versions. Local retention does not configure remote retention.

**Upload attachment is an open external gate:** supply a consistent read-only snapshot of the backend volume. A separate Railway service cannot be assumed to share that volume. Provide a real snapshot/export mechanism or execute the job where its snapshot is available. An empty unrelated upload directory does not satisfy full recovery.

The archive includes `database.dump`, uploaded files and SHA-256 manifest. Upload `.tar` and `.tar.sha256`. Compatible database-only `.dump` is insufficient for full acceptance.

```sh
python3 /app/restore_postgres.py s3://BUCKET/PREFIX/ARCHIVE.tar \
  --database-url "$RESTORE_DATABASE_URL" \
  --confirm-database lucy_restore_drill --uploads-dir /restore/uploads
```

Restore only to an empty separate DB and upload directory. The CLI verifies all hashes, rejects path traversal/links/duplicates and refuses non-empty uploads. A read-only PostgreSQL preflight runs before any download or unpacking and refuses existing user objects, including functions, types, custom schemas, extensions and other non-table objects. Unknown/error results fail closed. Restore does not use destructive `--clean` or `--if-exists`; never use `--allow-production` for a drill.

Local synthetic drill on 8 October: latest head `8c9d0e1f2a3b`, archive+upload restore in 1.86s to a newly created isolated database. Read-back: 102 synthetic users, 12 lessons, 22 orders, 2 paid purchases, 202 rights (200 fixture grants), 2 outbox messages and 2 payment events. Uploaded file SHA-256 matched the source. The database includes both smoke and acceptance setup; it contains no production records. This proves the mechanism, not production RPO/RTO. Restore a fresh external full-size backup before launch; record financial/row counts, hashes and elapsed time to prove RPO <=24h and RTO <=4h.

## Acceptance

Use [load profile](../../scripts/load/README.md), [implementation checklist](../06_Tracking/LAUNCH_READINESS_IMPLEMENTATION.md) and [release checklist](RELEASE_CHECKLIST.md). Physical devices, actual receipt/refund, provider reconciliation, legal signoff, external counter/alerts/backups remain separate evidence gates. Checkout stays disabled.

Development compose uses a new `lucy_postgres17_data` volume and preserves the old PG15 volume. Retained data requires dump/restore; do not mount a PG15 data directory into PG17.
