# Project state — 2026-11-25

This is the authoritative handoff for a fresh agent. Read it after `AGENTS.md`.
Update it at the end of every work session.

## Working copy and backup status

- The authoritative copy is **GitHub `origin/main`** (`anthonymweb/driftguard`).
- The Drift console work was merged to `main` and pushed to `origin/main` on
  2026-11-24 after the merged tree passed the full backend and frontend suites.
- The original working volume `/mnt/data` (sda6) was mounted **read-only** with
  `norecovery` on 2026-11-24 because the disk is degraded. It remains readable and is
  not being written to.
- Work continues in `/home/anthonyl/driftguard`, a fresh clone of `origin/main`.
- The 2026-11-25 Clarity restyle commits were made on local `main` and pushed to
  `origin/main` after the verification gates below passed.
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

### Clarity SecOps UI restyle — 2026-11-25 (implemented, awaiting visual approval)

- Owner approved the Stitch/Clarity SecOps direction for all four surfaces after
  reviewing the research design. Plan:
  `docs/superpowers/plans/2026-11-25-stitch-clarity-ui.md` (approved, review-corrected).
- Design authority: `stitch_driftguard_research_security_console/clarity_secops/DESIGN.md`
  YAML frontmatter (`#faf8ff`, `#004ac6`, `#006e2d`, `#ac0031`, `#ba1a1a`), plus the
  design prose amber `#b45309`. The other Stitch examples remain local-only research.
- Tasks 1–8 complete on `main`: Clarity tokens + CDN fonts/icons; fixed 240px desktop
  sidebar with a mobile header and bottom tab bar at <768px (no tablet rail); Drift
  metric cards from `latestComparable.summary.counts`; Targets stat tiles, search,
  filter tabs and right-anchored register slide-over; Evaluation KPI cards with real
  counts and mobile `data-label` table cells; Settings cards and four footprint tiles;
  unified state blocks and a responsive rewrite.
- No backend changes, no new endpoints, no new UI dependencies. React 19 + Vite +
  plain CSS only. Material Symbols and Google Fonts load from CDN with system fallbacks.
- Drift metric cards are omitted when the latest comparable scan has no counts; missing
  data is never rendered as zero. Evaluation shows only measured KPIs and otherwise shows
  the backend's own unavailable reason.

## Verification evidence — 2026-11-25 (Clarity restyle)

- Frontend: `cd frontend && npm test` → 24 files, 93 tests passed; `npm run build` →
  production build succeeded.
- Backend: `cd backend && .venv/bin/python -m unittest discover -s tests` →
  `Ran 143 tests ... OK` (untouched).
- Runtime registration: `eservices-lab` was registered through the real Targets form
  (authorised, scope `tls`/`network`, port 8443, basis `written approval`), and the API
  confirmed one target with zero scans. No seeded or invented findings.
- CDP runtime pass at 1440×900 and 390×844 on all four routes: correct page titles and
  selectors; desktop sidebar measured 240px with no tab bar; mobile header and tab bar
  present with no sidebar; no fatal console state. The only console error was a
  pre-existing `/favicon.ico` 404.
- Screenshots: `/tmp/opencode/driftguard-ui-shots/` — `targets`, `drift`, `evaluation`,
  `settings`, each in `-desktop.png` and `-mobile.png` variants. All eight PNGs are
  non-blank and carry the Clarity `#faf8ff`/white surfaces. Owner visual approval is
  still pending; these are the evidence for approve/reject per surface.
- Live API remained honest: `available: false` on `/api/evaluation` due to duplicate
  ground-truth labels, so the Evaluation screenshot shows the real unavailable reason
  rather than invented metrics. Drift has a subject and authorisation stamp but no
  observations yet, so it correctly shows no metric cards or drift rows.

## Verification evidence — 2026-11-24 (historical)

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
- Browser-level passive capture was completed with REA against
  `http://127.0.0.1:5173` at 1280px and 500px. All rendered routes produced no console
  or page errors. `#/drift` resolves to `#/targets` while the register is empty; the
  narrow viewport collapses the primary nav into a `MENU` button. Local-only screenshots:
  `/tmp/opencode/driftguard-{targets,evaluation,settings,narrow}.png`.
- A lab-driven viva (register/sync, baseline, drift scan, redacted export, real keyboard
  focus pass) remains unrun. Static browser capture does not replace it.
- Independent read-only code review of `8af20c0..55dce04` completed on 2026-11-24. No
  Critical issues. Important: stale-history target-switch race, UI-derived `PERSISTENT`
  fallback, misleading `LOCAL RESEARCH` chip under JWT/no-session state, dialog focus
  management, and the missing live viva. Minor: polling scope, evaluation error/remediation
  copy, CSV URL revocation and formula hardening. The reviewer did not rerun the suites;
  the test/build evidence above is the implementer's recorded verification.

## Paused / not current work

- The guided-demo design and plan exist in `docs/superpowers/specs/` and
  `docs/superpowers/plans/`. The owner explicitly said to ignore the demo for now.

## Known limitations and open items

- Evaluation joins engine findings to ground truth by scan **label**, so re-running the
  lab sequence without clearing scan history produces duplicate labels and an ambiguous
  join.
- `Remediation` and `User` models exist; remediation has no endpoint or workflow yet.
- Static browser capture passed at wide and narrow viewports, but a lab-driven viva with
  real `DriftEvent` rows, redacted export, and keyboard focus operation has not been run.
- Independent review found four code-level Important issues to fix before the console is
  treated as done: the `useHistory` target-switch race, the UI `PERSISTENT` fallback, the
  unconditional `LOCAL RESEARCH` mode chip, and dialog focus management. The first two
  touch evidence integrity and the frozen classification contract. These predate the
  Clarity restyle and were not in its scope.
- The Clarity restyle screenshots have been captured and runtime-checked but not yet
  visually approved per surface by the owner.
- Only one real target is registered locally and it has no completed scans, so metric
  cards and thread rows cannot yet be shown from runtime evidence. A lab-driven scan is
  still required for a full viva.
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
8. The Clarity SecOps direction is approved. Keep the product dependency set to React 19,
   Vite and plain CSS; use CDN fonts/icons with system fallbacks, not new UI libraries.
9. The design YAML palette in `clarity_secops/DESIGN.md` is authoritative over that file's
   prose palette; amber `#b45309` is the only adopted prose colour.

## Next steps

1. Obtain the owner's approve/reject decision for each of the four Clarity surfaces from
   `/tmp/opencode/driftguard-ui-shots/` (desktop and mobile), and apply any requested
   corrections before treating the restyle as accepted.
2. Fix the four code-level Important review findings on a feature branch off `main`,
   with focused regression tests: request-generation guard in `useHistory`, removal of
   the UI-side `PERSISTENT` fallback, explicit auth/mode state instead of "no session means
   local research", and focus containment/restore/Escape for dialogs.
3. Run the live viva rehearsal with the lab: register/sync targets, establish a baseline,
   switch `tls-legacy` on, scan, and confirm the Drift sheet shows stored `DriftEvent`
   rows with `NEW`/`PERSISTENT` classifications and a redacted CSV export.
4. Repeat the browser pass at 900px/600px and with real keyboard focus after the fixes;
   unit tests cover behavioural branches but not rendered focus visibility.
5. Address the Minor review findings: polling scope, evaluation error/remediation copy,
   and CSV download/formula hardening.
6. Optionally rotate `.driftguard_redaction_secret` if the earlier tracked copy could
   have been shared; doing so changes redaction tokens for existing evidence.

## Verify before claiming completion

```bash
cd backend && .venv/bin/python -m unittest discover -s tests
cd frontend && npm test
cd frontend && npm run build
```

Then a live pass: run the API, register/sync the lab targets, run a scan, and confirm the
UI reads real `DriftEvent` classifications rather than deriving its own.
