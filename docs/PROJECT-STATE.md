# Project state — 2026-11-27

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

## Current focus — faithful screen rebuild (2026-11-28)

- Owner chose a faithful rebuild of the four supplied screens over a faster clarity pass;
  resemblance is the tie-breaker wherever an evidence-only substitution leaves a choice.
  Design: `docs/superpowers/specs/2026-11-27-faithful-screen-rebuild-design.md` (approved).
  Plan: `docs/superpowers/plans/2026-11-27-faithful-screen-rebuild.md`.
- Work is on branch `faithful-screen-rebuild` off `22057e5`; commits `2d906a7` → `5209681`.
  Seven tasks are implemented. Task-scoped reviews: all Approved after fix loops for
  Task 3 (`9d33dc6` → `9e19044`) and Task 4 (`ab6dc13` → `5209681`).
- Frontend: **30 files / 158 tests passing**; production build succeeds. Backend untouched:
  **145 tests passing**. React 19 + Vite + plain CSS only; no new dependency. The extra 14
  tests close the whole-branch review's evidence-fidelity, target-state, and mobile-table
  findings before merge.
- Four screens rebuilt around the reference section order: Drift (subject → authorisation →
  difference line → four stored-count cards → timeline → detail rail), Targets (register head
  → three stat tiles → filter/search toolbar → roster cards with one stored-history read per
  target and a stored-state pill), Evaluation (header → methodology → four KPI cards → area
  table → 7/5 lower module), Settings (title → four-cell telemetry ribbon → panels A–D →
  evidence-only banner).
- Every displayed value comes from the demo API. No seeded, simulated, invented, or
  UI-derived finding; no `Skipped`/`Regressed`; frozen labels only. No fabricated telemetry,
  CLI snippet, seal, κ, F1, PID, key, digest, sync percentage, latency, or checksum action was
  added to close a visual gap. Evaluation keeps its honest unavailable branch.
- Live CDP pass against `demo-driftguard.db` at `1440×900` and `390×844`: Drift shows
  `eservices-lab` with stored `PERSISTENT`/`RECURRING` and no API step; Targets shows five
  targets with four `NO DRIFT`; Evaluation shows `7/12`, `0/56`, 17 unmeasured, TLS `7/7`,
  Network `0/5`; Settings shows `local_research`, redaction enabled, footprint `5/25/7/8`.
  Research DB remains `1 / 3 / 0 / 0`. Only console error is the pre-existing favicon 404.
- Screenshots: `/tmp/opencode/driftguard-rebuild-shots/` (`{drift,targets,evaluation,settings}-
  {desktop,mobile}.png`, plus `dom-audit.json`). They are non-blank at the exact requested
  dimensions. The mobile Evaluation table now scrolls inside its card (`overflow-x: auto`,
  `min-width: 720px`, `scrollWidth 720 / clientWidth 356`) without page-level overflow.
  Automated structural/DOM fidelity is verified; **per-surface pixel resemblance still needs
  the owner's eyes** before the rebuild is called visually accepted.
- Scoped forbidden-copy check (product source excluding tests + demo guide): clean.
  The plan's unscoped grep hits legitimate negative assertions and guide instructions, so
  the check is recorded with that scope.

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
- **145 backend tests passing** (verified 2026-11-27 after the scan-engine flush fix; 143 before the two new regression tests).
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

## Verification evidence — 2026-11-27 (demo preload)

- Backend: `.venv/bin/python -m unittest discover -s tests` → `Ran 145 tests ... OK` after
  the flush fix and two new RED→GREEN regression tests (`test_new_finding_is_classified_with_no_autoflush`,
  `test_persistent_finding_is_not_reported_as_fixed_with_no_autoflush`). Before the fix those
  tests produced `[] != NEW` and `FIXED != PERSISTENT` respectively.
- Frontend: `npm test` → 24 files / 93 tests passed; `npm run build` → production build OK.
- 25/25 preload scans reached `completed` (log: `/tmp/opencode/driftguard-demo-preload/sequence-final.log`).
  `/api/stats` → `targets 5, scans 25, evidence 7, drift_events 8`, `local_research`, redaction on.
- Drift history for `eservices-lab`, oldest → newest: `DEMO-0 BASELINE`; `DEMO-1 CHANGED NEW=2`;
  `DEMO-2 CHANGED PERSISTENT=2`; `DEMO-3 CHANGED PERSISTENT=1 FIXED=1`;
  `DEMO-4 CHANGED PERSISTENT=1 RECURRING=1`. A clean target (`juice-shop`) reads
  `BASELINE` then four `NO DRIFT`.
- `/api/evaluation` → `available: true`, `duplicates: []`, overall `detections 7 / present_total 12`,
  `misses 5`, `false_positives 0`; TLS `7/7` accuracy `1.0`; Network `0/5` (honest misses from
  the 8443-only scope); API has no present findings by design.
- Research DB re-checked: `targets 1 / scans 3 / scan_evidence 0 / drift_events 0` — unchanged.
- UI DOM pass on all four hash routes from a real Chrome CDP session: Drift renders the two
  stored TLS threads with `PERSISTENT` / `RECURRING` and the scan-by-scan difference line;
  Targets shows five authorised targets with last scans; Evaluation shows the measured KPIs;
  Settings shows `targets 5 / scans 25 / evidence 7 / drift events 8`. Screenshots kept in
  `/tmp/opencode/driftguard-ui-shots/` (not committed).

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

## Current focus — demo guide and preloaded lab evidence (2026-11-27)

- The owner asked for **one** demo document and a console already loaded with real lab
  scans. Deliverable: `docs/DEMO_GUIDE.md`. Design:
  `docs/superpowers/specs/2026-11-27-demo-guide-design.md`; plan:
  `docs/superpowers/plans/2026-11-27-demo-guide-preload.md` (both approved, inline execution).
- Demo data lives in the untracked `demo-driftguard.db` at the repo root; the research DB
  `driftguard.db` (1 target, 3 scans) is preserved. The API must be started with
  `DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db` and
  `DRIFTGUARD_SCAN_RATE_LIMIT=60/minute`; without the env var it serves research data.
- The console is preloaded with 25 completed real scans across five lab targets.
  `eservices-lab` alone carries labels `DEMO-0` … `DEMO-4` and the scenario toggles; the
  other four targets are scanned unlabelled and stay clean (`BASELINE` / `NO DRIFT`).
  The API area (`api-debug`) is deliberately not demonstrated — it honestly shows no
  present findings.
- `lab/scans.json` (ground-truth marks) and `demo-driftguard.db` are untracked. Prior mark
  histories are archived outside the repo in `/tmp/opencode/driftguard-demo-backup/`:
  `scans.json.pre-demo` (original duplicate `S0,S1,S2`) and `scans.json.bad-preload`
  (discarded first preload with wrong drift events). `lab/ground_truth.csv` was never touched.
- **One product-code change was made**: `backend/driftguard/scanner/engine.py` now calls
  `db.flush()` after persisting evidence and before `_record_drift`. `SessionLocal` uses
  `autoflush=False`, so without the flush the current scan's evidence was invisible to the
  drift comparison: NEW events vanished and PERSISTENT was reported as FIXED. Two regression
  tests were added in `backend/tests/test_scanner_engine.py` (RED→GREEN verified). The frozen
  rules in `drift.py` were not changed; the plan's "no product code changes" constraint was
  explicitly voided for this one line by the owner.
- The demo DB's `eservices-lab.approved_ports` is `[8443]`, not `[8080, 8443]`: port 8080
  answers with a `301` and the `httpx` CLI exits 1 on a redirect, which makes a labelled
  scan `completed_with_errors` (no drift events). **Reapply after every `driftguard.sync`.**
- Verification: backend suite 145 tests OK; frontend 24 files / 93 tests and production
  build OK. See §Verification evidence — 2026-11-27 below for the live API state.

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
10. Demo labels and scenario toggles belong to `eservices-lab` only. `_duplicate_completed_labels`
    groups by label without target, so labelling all five targets makes `/api/evaluation`
    unavailable. Do not add `DEMO-*` labels to the other four targets and do not toggle
    scenarios on them.
11. The demo DB's `eservices-lab` is scoped to port 8443 only. Restoring 8080 with a fresh
    sync reintroduces the `httpx` redirect failure and empty drift history; reapply the fix.
12. `lab/ground_truth.csv` stays untouched — evaluation builds truth from `lab/scans.json`.
    Archive that file outside the repo before reusing demo labels.
13. The scan-engine flush is load-bearing infrastructure, not a classifier change. Do not
    remove it to satisfy the original "no product code changes" wording in the demo design.
14. The faithful rebuild is plain CSS on React 19/Vite; do not introduce Tailwind or a UI kit
    to improve resemblance.
15. Target-state pills read one stored history per target and never derive a label. A newest
    drift event with a non-frozen classification yields no state, not an older stored state.
16. Stored snapshot cards only render states already present in the selected thread; an
    unclassified older observation is omitted, not labelled with the latest state.
17. No telemetry, fake provenance, fabricated bar/CLI/seal, or invented toast may be added to
    close a visual gap with the supplied screens.
18. A finding observed without a stored drift event renders `NO STORED CLASSIFICATION`, never
    a stored-looking `PERSISTENT`. Snapshot cards use the detail stored on that same scan;
    missing per-scan detail is stated, never copied from the latest observation.

## Open carried-over findings (not changed by the faithful rebuild)

These predate this branch and remain open for a future scoped session. They are recorded here
so a handoff replacement does not imply they were resolved:

- `useHistory` request-generation/abort guard: open, Important, frontend state only.
- "No session means local research" auth/mode inference: open by design decision; do not
  silently change it in a visual task.
- Dialog focus containment, focus restore, and Escape handling: open, no dialog component was
  changed by this branch.
- CSV download/formula hardening: open, Minor, `frontend/src/lib/csv.js` untouched.
- Polling scope and Evaluation error/remediation copy: open, Minor, untouched.
- Duplicate per-area derivation in Evaluation's table and fidelity panel: open, Minor; both
  currently read the same backend data but can drift if edited separately.
- Malformed `recorded_at` on the newest target drift entry: open, Minor; it falls back to
  array ordering rather than an explicit no-state.
- Desktop Settings footprint grid is 2×2 at 1024px although the brief described 3-up tiles:
  open, cosmetic; deliberately not reopened in this fidelity pass.
- 900px/600px and real-keyboard-focus browser pass: open verification; the automated gate only
  covered 1440×900 and 390×844 DOM/screenshots.

## Next steps

0. Obtain the owner's approve/reject decision for each of the four rebuilt surfaces from
   `/tmp/opencode/driftguard-rebuild-shots/` (desktop and mobile). The automated gate verified
   structure, exact dimensions, real values and non-blank captures; it did not substitute for
   the owner's visual judgment.
1. Hand over `docs/DEMO_GUIDE.md` with the API running on `demo-driftguard.db` and the console
   hard-refreshed at `#/drift/1`. The four talking points are labelled
   `NEW → PERSISTENT → FIXED → RECURRING` on eservices-lab, `NO DRIFT` on a clean target,
   measured Evaluation KPIs with honest Network misses, and redaction in Settings.
2. Run the lab-driven viva: register/sync, baseline, `tls-legacy` on, scan, confirm stored
   `DriftEvent` rows and a redacted CSV export. A queued scan is never narrated as a finding.
3. Keep the research DB (`driftguard.db`) untouched and reapply `[8443]` to
   `eservices-lab.approved_ports` in the demo DB after any `driftguard.sync`.
4. Optionally rotate `.driftguard_redaction_secret` if the earlier tracked copy could
   have been shared; doing so changes redaction tokens for existing evidence.

## Verify before claiming completion

```bash
cd backend && .venv/bin/python -m unittest discover -s tests
cd frontend && npm test
cd frontend && npm run build
```

Then a live pass: run the API, register/sync the lab targets, run a scan, and confirm the
UI reads real `DriftEvent` classifications rather than deriving its own.
