# Launch operations — 8 October 2026

Status: local configuration and synthetic recovery prepared. External staging, cron, alerts, counter, real payment and production deployment are not accepted by this document.

## Isolated Railway staging

Create an empty environment with PostgreSQL 17, dedicated Redis, backend, outbox worker and frontend. Do not duplicate production secrets/data. Separate domains, JWT/MFA/monitoring/payment/DRM keys, demo payment form, email destinations, owner chat, cookies and storage are required.

| Service | Root | Config file | Gate |
| --- | --- | --- | --- |
| Backend | `/backend` | `/backend/railway.toml` | `/health`, startup migrations |
| Worker | `/backend` | `/ops/railway/worker.toml` | Redis heartbeat |
| Frontend | `/frontend` | `/frontend/railway.toml` | `/`, build-time environment |
| Backup | `/` | `/ops/railway/backup.toml` | 01:00 UTC daily, external full backup |

Set these config paths in Railway and read back the effective start command/healthcheck. Older root TOML service sections do not prove applied per-service settings. Remote staging uses `ENVIRONMENT=staging`, `DEBUG=false`, `PRODAMUS_DEMO_MODE=true` with a separate form. It enforces the production security checks and requires an isolated cookie/domain namespace, e.g. frontend `staging.lucysmirnova.ru`, API `api.staging.lucysmirnova.ru`, `COOKIE_DOMAIN=staging.lucysmirnova.ru`. Production continues to reject demo payments. Keep checkout disabled until isolation and synthetic fixtures are reviewed.

Frontend build variables: API URL, site URL, operator-provided Metrika counter ID (see frontend env template). Verify configured checkout/purchase goals with consented UTM journeys. Missing counter remains an advertising gate.

## Monitoring

Configure an external uptime monitor every 30 seconds, alert after two consecutive failures, and test failure/recovery delivery:

1. Frontend `/` and API `/health`: HTTP 200.
2. API `/health/operations`: HTTP 200, header `X-Monitoring-Token` from a separate random `MONITORING_TOKEN` of at least 32 characters.
3. Operational probe exposes only counts. HTTP 503 means worker heartbeat missing (120s TTL), notification pending for >120s, dead letters, or DB/Redis unavailable. API and worker must share the environment's Redis; environments must not share Redis.
4. Monitor external backup freshness independently: a complete archive and checksum younger than 24 hours. Healthy API does not prove fresh backups. Alerting belongs outside the app's Railway failure domain.

Heartbeat proves loop liveness; queue age and delivery ledger prove notifications. A dead letter needs operator resolution, not falsely marking it sent.

## Complete backup and recovery

The image uses PostgreSQL 17. Configure `DATABASE_URL`, `BACKUP_REQUIRE_S3=true`, `BACKUP_S3_URI`, `BACKUP_S3_SSE=AES256` or `aws:kms`, restricted AWS credentials, `BACKUP_REQUIRE_UPLOADS=true`, `BACKUP_UPLOADS_DIR`. Enable provider bucket versioning/retention and prohibit the writer from deleting previous versions. Local retention does not configure remote retention.

**Upload attachment is an open external gate:** supply a consistent read-only snapshot of the backend volume. A separate Railway service cannot be assumed to share that volume. Provide a real snapshot/export mechanism or execute the job where its snapshot is available. An empty unrelated upload directory does not satisfy full recovery.

The archive includes `database.dump`, uploaded files and SHA-256 manifest. Upload `.tar` and `.tar.sha256`. Compatible database-only `.dump` is insufficient for full acceptance.

```sh
python3 /app/restore_postgres.py s3://BUCKET/PREFIX/ARCHIVE.tar \
  --database-url "$RESTORE_DATABASE_URL" \
  --confirm-database lucy_restore_drill --uploads-dir /restore/uploads
```

Restore only to an empty separate DB and upload directory. The CLI verifies all hashes, rejects path traversal/links/duplicates and refuses non-empty uploads. PostgreSQL restore replaces the target schema; never use `--allow-production` for a drill.

Local synthetic drill on 8 October: latest head `8c9d0e1f2a3b`, archive+upload restore in 1.86s to a newly created isolated database. Read-back: 102 synthetic users, 12 lessons, 22 orders, 2 paid purchases, 202 rights (200 fixture grants), 2 outbox messages and 2 payment events. Uploaded file SHA-256 matched the source. The database includes both smoke and acceptance setup; it contains no production records. This proves the mechanism, not production RPO/RTO. Restore a fresh external full-size backup before launch; record financial/row counts, hashes and elapsed time to prove RPO <=24h and RTO <=4h.

## Acceptance

Use [load profile](../../scripts/load/README.md), [implementation checklist](../06_Tracking/LAUNCH_READINESS_IMPLEMENTATION.md) and [release checklist](RELEASE_CHECKLIST.md). Physical devices, actual receipt/refund, provider reconciliation, legal signoff, external counter/alerts/backups remain separate evidence gates. Checkout stays disabled.

Development compose uses a new `lucy_postgres17_data` volume and preserves the old PG15 volume. Retained data requires dump/restore; do not mount a PG15 data directory into PG17.
