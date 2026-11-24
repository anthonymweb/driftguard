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
- **143 backend tests passing** (verified 2026-11-24 in the writable clone).
- API surfaces that exist: `/health`, `/ready`, `/api/auth/token`, `/api/users`,
  `/api/targets` (create/list/get), `/api/targets/{id}/scans` (create/list),
  `/api/scans/{id}/evidence`, `/api/scans/{id}/evidence/redacted`.

## Current focus — Drift console redesign (implemented)

The owner chose **approach 1: a comparison-first console**, now called the **Drift
console** in product language. The interface is organised around one question: *what
changed since the previous authorised observation?* It is not a generic SOC dashboard.

- Design document: `docs/superpowers/specs/2026-11-24-drift-console-design.md`
  (**approved 2026-11-24 — implemented**).
- Backend read API plan implemented (tasks 1–5): scannable fields on `TargetRead`,
  completed-scan-only comparison, `GET /api/targets/{id}/history`, `GET /api/stats`,
  `GET /api/evaluation`.
- Drift console UI plan implemented (tasks 1–17): test harness, API client, hash
  routing, frozen thread model and copy, shell, authorisation-first registration,
  target register, scan axis, thread grid and cards, redacted CSV/detail rail, single
  history loading with abort and polling, Drift page, Evaluation, Settings, responsive
  and reduced-motion behaviour, and final app wiring.
- The old dashboard is gone. Navigation is `Drift`, `Targets`, `Evaluation`, `Settings`;
  a deep link to `#/drift/{id}` restores the same subject sheet.
- Every row on the console comes from stored history. There are no seeded, simulated, or
  inferred findings, and an empty register or empty observation window says so plainly.

## Verification evidence — 2026-11-24

- Backend: `cd backend && .venv/bin/python -m unittest discover -s tests` → `Ran 143
  tests ... OK`.
- Frontend: `cd frontend && npm test` → 24 files, 86 tests passed; `npm run build` →
  production build succeeded.
- Copy audit: no `comparator` in `frontend/src` or `README.md`; the only hit in
  `AGENTS.md` is the internal instruction forbidding it in user-facing copy. No
  `awaiting assessment`, `sparkline`, `glow`, or gradient strings in `frontend/src`.
- Live API smoke against `127.0.0.1:8000`: `/health` ok; `/api/targets` returned an
  empty register; `/api/stats` returned zero counts, `local_research` mode, redaction
  enabled with a local-only token map; `/api/evaluation` returned `available: false`
  with the duplicate-label reason. `/api/targets/1/history` returned 404, as expected
  with an empty register.
- Browser-level checks (breakpoints, focus rings, lab-driven drift) were **not** run in
  this harness. A live viva rehearsal with the lab remains the next verification step.
- Backend final review was self-review by the implementing agent; no fresh reviewer
  subagent was available. Surface this limitation before presenting the work as
  independently reviewed.

## Paused / not current work

- The guided-demo design and plan exist in `docs/superpowers/specs/` and
  `docs/superpowers/plans/`. The owner explicitly said to ignore the demo for now.

## Known limitations and open items

- Evaluation joins engine findings to ground truth by scan **label**, so re-running the
  lab sequence without clearing scan history produces duplicate labels and an ambiguous
  join.
- `Remediation` and `User` models exist; remediation has no endpoint or workflow yet.
- A browser-level viva rehearsal against the lab has not been run; the API and unit-level
  contracts are green, but visual breakpoints and focus rings still need a human pass.
- `.driftguard_redaction_secret` was tracked in earlier commits. It is now untracked and
  ignored. If the repository was shared, rotate the secret (delete it and let the backend
  regenerate it); this changes redaction tokens for old evidence.
- The console's displayed metrics must distinguish *stored evidence* from *absence of
  a scan*. An empty state is not "all clear".

## Decisions the next agent must not reopen

1. DriftGuard is a drift detector; comparison is its core operation. The lab is a
   fixture, not a demo.
2. Evidence only; no fabricated findings.
3. Classification rules are frozen.
4. Every scan is gated by an attributable authorisation record and approved scope.
5. Redaction happens before any export or AI call.
6. The comparison-first Drift console (approach 1) is the chosen frontend direction.
7. The read API and console are implemented; do not reintroduce per-scan evidence fetches
   or derive classifications in the UI. The backend owns the frozen rules.

## Next steps

1. Run the live viva rehearsal with the lab: register/sync targets, establish a baseline,
   switch `tls-legacy` on, scan, and confirm the Drift sheet shows stored `DriftEvent`
   rows with `NEW`/`PERSISTENT` classifications and a redacted CSV export.
2. Do the browser-level 900px/600px and keyboard-focus pass; unit tests cover the
   behavioural branches but not rendered focus visibility.
3. Optionally rotate `.driftguard_redaction_secret` if the earlier tracked copy could
   have been shared; doing so changes redaction tokens for existing evidence.
4. Treat the backend sign-off as self-review only until a fresh reviewer is available.

## Verify before claiming completion

```bash
cd backend && .venv/bin/python -m unittest discover -s tests
cd frontend && npm test
cd frontend && npm run build
```

Then a live pass: run the API, register/sync the lab targets, run a scan, and confirm the
UI reads real `DriftEvent` classifications rather than deriving its own.
