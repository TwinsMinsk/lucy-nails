# Launch readiness implementation — 2026-10-08

## Goal and release contract

Implement the approved launch plan for 1,000 visitors/day, 50 purchases/day and 50 concurrent learners. Only the self-paced tariff is sold. UTM and consented Yandex Metrika are required. A full refund revokes access and the certificate; normal access expiry does not invalidate an earned certificate.

Baseline: `a055e2d`, isolated branch `oleg/launch-readiness`. Production checkout stays disabled until independent review, migrations, controlled payment/refund, delivery, device and recovery acceptance succeed. Local verification does not establish production acceptance. The user authorized branch push and preparation for integration into master; draft PR #12 exists. Production deployment, real financial transactions and enabling sales remain distinct steps.

## Work checklist

- [x] A. Verify email ownership, safely recover existing unverified accounts, invalidate old sessions, atomic activation/reset, expired-access logout, safe redirects and malformed token handling.
- [x] B. Full-refund entitlement/certificate consistency; manual certificate eligibility; immutable refund dates; rejected webhook retries; durable second-payment incident handling.
- [x] C. Financial classification of legacy manual grants, consistent payment-date reports, ordered repeat-visit funnel, acquisition from course pages, campaign/ad breakdown, safe CSV, actual learning activity and Metrika goal code. Live counter configuration is an external gate.
- [x] D. Permission-aware admin loading/actions, paginated searchable orders/notifications/users/access, unified UTC formatting, preview progress and honest dashboard error state.
- [x] E. API-defined landing modules/gallery and single course identity for content, prices and checkout; tests distinguish API failure from empty publication.
- [x] F. Runtime dependency updates, bounded verified image upload and documented secret-scan triage complete. All four historical Prodamus findings were independently traced to an official public demo example and narrowly suppressed; current and historical scans and detection canaries pass.
- [ ] G. PostgreSQL 17 complete backup/restore, secure staging configuration, health/worker monitoring and load tools complete locally; remote resources and acceptance remain open.
- [x] H. Independent local implementation review, automated tests/lint/build/E2E, new-migration round-trip and synthetic load/recovery evidence complete. Full external CI/security and production acceptance are not declared complete.

## Required regressions

1. Attacker registers buyer email; guest payment persists money but old attacker session cannot read paid content. Mailbox confirmation invalidates prior sessions and grants only the owner access. Legacy accounts are not silently marked verified.
2. Full refund after active, suspended or expired access prevents restoring/extending that right and revokes certificates. Manual access can earn certificates. Repeated processed refund keeps the original time and rejects blank provider reference.
3. Duplicate or rejected signed provider events never falsely imply a fulfilled purchase; a second actual payment for one order is durably recorded and raises an operator incident.
4. Historical `admin_grant_` rows contribute zero real revenue. Repeat visits, earlier orphan CTA, direct course acquisition, cross-month payments, opt-out and hostile CSV text produce consistent reports.
5. Every seeded team role can use its permitted sections, all lists work beyond 200 records, CMS publication controls actual rendered content, permitted preview works without paid access, API failure is visibly distinct from no purchase.

## Launch acceptance

- Staging uses separate DB, Redis, payment form, signing secrets, provider recipients/chats and domains; no production data is used by tests.
- Guest and authenticated checkout, actual signed callback, activation, email, lesson/progress and certificate work; invalid signature/amount and concurrent retries cannot grant unintended access.
- Owner-assisted production purchase/refund and receipt verification remain explicit release gates. Access target is <=60 seconds after callback and delivery <=2 minutes with a healthy provider.
- All 11 lessons are checked on desktop, physical iOS and Android, including playback after >5 minutes idle, expiry and revoked access.
- Load profile: 50 concurrent users for 15 minutes, burst to 100 for 5 minutes, parallel checkout and callback retries; unexpected failures <1%, internal API p95 <500ms, no lost money/notifications.
- A fresh encrypted/versioned external backup restores to a separate database and includes upload files; measured RPO <=24 hours and RTO <=4 hours.
- First 72 hours: limited advertising, daily Prodamus reconciliation and delivery review, named operator and checkout kill switch.

## Operator-owned inputs

Metrika counter identity/access, isolated demo payment form, backup bucket/credentials and legal/accounting sign-off must be verified, never invented. Credentials belong in provider/environment secret stores. Any unavailable external gate stays explicitly open in the final report.

## Verified local candidate

Independent verifier verdict: **APPROVE local implementation; production launch INCOMPLETE**. Fresh follow-up backend run: **335 passed, zero skipped**, 141.69s. Independent follow-up review is recorded separately before its commit. No production resources were changed. An empty isolated Railway staging environment now has independent PostgreSQL 17 and Redis; application deployment and external acceptance are still pending.

| Check | Evidence | Practical limit |
| --- | --- | --- |
| Backend regression | 335 passed, 0 skipped | Disposable PostgreSQL 17, no live provider |
| Frontend regression | 77 tests, TypeScript and ESLint pass | Mocked API contracts |
| Full browser suite | 40 passed: 20 Chromium, 20 mobile WebKit, 45.8s | Isolated SSR fixture; physical devices still required |
| Production build | Next.js 16.4.0 build passed | Local build, no remote deployment |
| Runtime dependency audit | pip-audit and npm audit --omit=dev: zero known vulnerabilities | Full npm audit: 5 high dev-only advisories remain in the upstream braces dependency chain with no patched release. Two typography advisories were removed with a scoped selector-parser override; generated Tailwind CSS is byte-identical. No incompatible Next ESLint downgrade was applied |
| Migrations | Latest head 8c9d0e1f2a3b; downgrade to baseline 6a7b8c9d0e1f and upgrade pass | Model metadata now matches the existing migrated schema; alembic check reports no new upgrade operations |
| Upload protection | Forged/missing Content-Length bounded before multipart parsing | 12 MiB total body, 10 MiB image, 20M pixels |
| Backup recovery | Latest-head database and uploads restored to new isolated DB in 1.86s; hashes match | Synthetic local data, no production RPO/RTO proof |
| Load smoke | 72/72 checks, zero HTTP errors, p95 263.86ms | Local API |
| 20-minute load | Exit 0; 50 learners for 15 minutes, up to 100 for 5 minutes; 1,573 requests; 99.87% checks, 0.127% errors, p95 349.67ms | Two Docker-to-host dial timeouts included; no remote Railway capacity proof |
| Secret scan | Current files and history: 0 findings; independent canaries: 4/4 detected | Narrow historical fingerprints cover only verified official public demo examples |

The pre-existing baseline metadata drift is resolved without changing applied migrations: five model fields now declare JSONB, and analytics event ID / MFA user ID declarations match the existing unique constraints and ordinary indexes. A fresh PostgreSQL 17 upgrade and `alembic check` pass; CI now checks schema drift explicitly.

[Secret-scan triage](../04_Setup_Ops/SECRET_SCAN_TRIAGE.md) records all 27 original findings and the exact official provenance of the four historical Prodamus demo examples. Current files and refreshed history through candidate `8d1f946` have zero findings; four independent canaries are still detected. GitHub CI, scanner and individual CodeQL language jobs passed on that candidate; a separate CodeQL regex alert prompted a bounded hostname parser fix. The follow-up commit requires another complete GitHub run before merge.

Verification also found and closed concurrency defects: stale password changes could race mailbox activation/session revocation; a payment-event FK lock could deadlock concurrent callbacks and misclassify the same provider payment. Deterministic regressions now cover both. Bcrypt no longer blocks the API event loop: ten-login probe gap decreased from 1.864s to 15.7ms using a bounded thread pool.

Both load runs separately created 11 orders, one paid purchase, one paid entitlement, one processed financial event and one durable outbox message; 50 signed callback repeats per run created no duplicate records. Combined read-back: 22 orders, 2 purchases, 2 payment events, 2 outbox messages and 202 rights, of which 200 are preauthenticated synthetic manual fixtures. Checkout and paid-lesson checks all succeeded. Two course-read requests timed out while connecting from Docker to the Windows host; direct API health remained healthy and database sessions showed no lock waits. Their underlying transport cause was not established. The errors were retained in the thresholds; the result meets <1% errors and p95 <500ms locally. Repeat on remote isolated staging with worker/delivery/CPU/RAM evidence before capacity acceptance. This test does not measure video delivery or mail-provider latency.

## External release gates — not completed by local code checks

1. Create and verify isolated remote staging DB/Redis/domains/provider secrets, email sink and demo payment form; measure access <=60 seconds and healthy-provider delivery <=2 minutes, including failures/retries and operator alerts.
2. Supply the real Metrika counter ID and validate consented UTM -> checkout -> confirmed purchase -> refund reconciliation. The server financial ledger remains authoritative; external goal deduplication after consent removal/reconsent needs live reconciliation.
3. Configure externally scheduled encrypted/versioned backups with the actual backend uploads snapshot, freshness/failure alerts and a full-size restore proving RPO <=24h and RTO <=4h. Local configuration does not prove active Railway schedules or native backups.
4. Verify all 11 real lessons on desktop, physical iPhone and Android after >5 minutes idle. Iframe renewal is tested, but a reload may reset playback position; real Kinescope DRM remains a device gate.
5. Owner performs the controlled actual Prodamus purchase/refund, receipt and finance reconciliation, confirms offer/privacy/refund obligations and then enables checkout using the admin switch. Limit advertising for the first 72 hours and reconcile daily.

Do not enable advertising or sales solely on this local approval. The user authorized push and preparation for master integration. Master automatically deploys to Railway; merge requires green checks, independent review and a verified production backup/rollout plan. Checkout remains disabled through deployment and acceptance.
