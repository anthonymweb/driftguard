# Project state — 2026-11-24

This is the authoritative handoff for a fresh agent. Read it after `AGENTS.md`.
Update it at the end of every work session.

## Working copy and backup status

- The authoritative copy is **GitHub `origin/main`** (`anthonymweb/driftguard`).
- The original working volume `/mnt/data` (sda6) was mounted **read-only** with
  `norecovery` on 2026-11-24 because the disk is degraded. It remains readable and is
  not being written to.
- Work continues in `/home/anthonyl/driftguard`, a fresh clone of `origin/main`.
- Local-only research state was copied into that clone before work resumed:
  `backend/driftguard.db`, `.driftguard_redaction_secret`, lab state files,
  `ground_truth.csv`, `scans.json`, rendered nginx configs, and `lab/certs/`.
- The damaged-disk folder `lab/democommerce.corrupt-pre-reboot/` was deliberately not
  copied into version control; it is ignored.

## What the system is

DriftGuard is a **drift detector** whose core operation is comparison: it observes an
authorised target over time and classifies the change with frozen labels: `BASELINE`,
`NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, `NO DRIFT`. The lab is the controlled fixture
that supplies ground truth; the product is the backend plus the dashboard.

"Comparator" is an internal design metaphor only. Never use it in user-facing copy or the
product pitch; say **drift detection** and **what changed between scans**.

## Completed

### Lab / test domain

- Five targets (`eservices-lab`, `democommerce`, `civic-services-portal`, `juice-shop`,
  `vampi`), seventeen reversible drift scenarios, authoritative ground-truth log.
- 179 lab tests passing. Live verification reproduces the nine-scan matrix
  (17 scenarios, 0 mismatches) after the portal redesign.
- The eServices portal was deliberately restyled for presentation while its assessment
  contract stays pinned by tests.

### Backend (Phase 3 and Phase 4)

- Tasks 15–19: tool adapters, check catalogue, scan engine + authorisation/scope
  enforcement, registry sync + evaluation harness, redaction layer.
- Tasks 20–24: Alembic migrations target the application database; `/ready`; scan rate
  limiting; structured + audit logging; JWT authentication and `viewer`/`operator`/
  `admin` roles.
- **127 backend tests passing** (verified 2026-11-24 in the writable clone).
- API surfaces that exist: `/health`, `/ready`, `/api/auth/token`, `/api/users`,
  `/api/targets` (create/list/get), `/api/targets/{id}/scans` (create/list),
  `/api/scans/{id}/evidence`, `/api/scans/{id}/evidence/redacted`.

## Current focus — Drift console redesign

The owner chose **approach 1: a comparison-first console**, now called the **Drift
console** in product language. The interface is organised around one question: *what
changed since the previous authorised observation?* It is not a generic SOC dashboard.

- Design document: `docs/superpowers/specs/2026-11-24-drift-console-design.md`
  (revised after builder check; awaiting owner approval).
- The implementation plan has not been written yet. Until it is, the frontend is still
  the old dashboard.

## Paused / not current work

- The guided-demo design and plan exist in `docs/superpowers/specs/` and
  `docs/superpowers/plans/`. The owner explicitly said to ignore the demo for now.

## Known limitations and open items

- Evaluation joins engine findings to ground truth by scan **label**, so re-running the
  lab sequence without clearing scan history produces duplicate labels and an ambiguous
  join.
- `Remediation` and `User` models exist; remediation has no endpoint or workflow yet.
- The old frontend does not use the auth endpoints and fetches evidence with an N+1
  request pattern (one call per target, then one per scan).
- `.driftguard_redaction_secret` was tracked in earlier commits. It is now untracked and
  ignored. If the repository was shared, rotate the secret (delete it and let the backend
  regenerate it); this changes redaction tokens for old evidence.
- The dashboard's displayed metrics must distinguish *stored evidence* from *absence of
  a scan*. An empty state is not "all clear".

## Decisions the next agent must not reopen

1. DriftGuard is a drift detector; comparison is its core operation. The lab is a
   fixture, not a demo.
2. Evidence only; no fabricated findings.
3. Classification rules are frozen.
4. Every scan is gated by an attributable authorisation record and approved scope.
5. Redaction happens before any export or AI call.
6. The comparison-first Drift console (approach 1) is the chosen frontend direction.

## Verify before claiming completion

```bash
cd backend && .venv/bin/python -m unittest discover -s tests
cd frontend && npm run build
```

Then a live pass: run the API, register/sync the lab targets, run a scan, and confirm the
UI reads real `DriftEvent` classifications rather than deriving its own.
