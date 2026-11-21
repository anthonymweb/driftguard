# Backend completion (Phase 4)

The engine, sync, evaluation and redaction layers are done (Tasks 15–19). This plan
finishes the **backend service** itself so it can be considered a complete deliverable
before the dashboard is wired up.

Safety and scope rules from the project brief are unchanged: three audit areas, frozen
classification rules, redaction before any AI call, lab-only evaluation, and an
attributable authorisation record for every assessment.

## Task 20 — Alembic migrations target the application database

**Defect found:** `alembic/env.py` only set `sqlalchemy.url` when
`DRIFTGUARD_DATABASE_URL` was exported, so `alembic upgrade head` fell back to
`alembic.ini`'s `driver://` placeholder (or a relative path resolved against the
current working directory). The migration wrote tables into `backend/driftguard.db`
while the application opened `driftguard.db` at the repository root — two databases,
one of them empty.

- Extract URL resolution into `driftguard/migrations.py` (`resolve_database_url()`),
  used by `alembic/env.py`.
- Tests:
  1. the resolved URL is the application's `DATABASE_URL` when no override is set,
     and the override when one is;
  2. `alembic upgrade head` against a temporary database builds **exactly** the
     schema the models declare (tables and columns) — this is the regression that
     caught the empty migration.

## Task 21 — Readiness endpoint

`/health` reports liveness only. Add `/ready`, which verifies the database answers
and returns 503 when it does not, so an orchestrator can tell the difference between
"a process is up" and "the service can serve traffic".

## Task 22 — Scan request rate limiting (politeness)

The plan's safety paragraph requires polite, bounded scanning. Expose a configurable
per-client limit on `POST /api/targets/{id}/scans` (`DRIFTGUARD_SCAN_RATE_LIMIT`,
default `10/minute`); over-limit requests receive 429 with `Retry-After`.

## Task 23 — Structured and audit logging

- `configure_logging()` emits structured JSON application logs.
- `driftguard/audit.py` records attribution events (target authorisation, scan
  requests, evidence exports) as JSON lines on the `driftguard.audit` logger, so
  who/when/basis is traceable outside the database.

## Task 24 — Authentication and role-based authorisation

- `users` table (bcrypt-hashed passwords), `POST /api/auth/token` issuing signed
  JWTs, `POST /api/users` for administration with a one-time bootstrap when no user
  exists yet.
- Roles: `viewer` (read), `operator` (read + queue assessments), `admin` (everything,
  including user and target management).
- Enforced whenever `DRIFTGUARD_AUTH_SECRET` is set; with no secret the API runs in
  local-research mode and logs a startup warning. `DRIFTGUARD_AUTH_REQUIRED=1`
  turns a missing secret into a startup failure rather than an open service.
- CORS gains the `Authorization` header.

## Verification

`cd backend && .venv/bin/python -m unittest discover -s tests` must stay green
(104 existing tests plus the new ones), then a live run: `alembic upgrade head` on a
fresh database, `/health` and `/ready` checks, and a rate-limited scan burst.
