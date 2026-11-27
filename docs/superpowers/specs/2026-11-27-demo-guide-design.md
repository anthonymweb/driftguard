# Demo guide and real-data preload — design (2026-11-27)

## Intent

The owner needs one document he can use while demonstrating the DriftGuard prototype, plus
a console that is already loaded with real scan data so he can explain each panel quickly
without waiting for scans during the presentation.

## Goals

- A single `docs/DEMO_GUIDE.md` that explains the architecture, tech stack, and every way
  to load different targets.
- A rehearsal script: start services, preload data, walk the four panels, and know what to
  say at each step.
- The running Drift console shows real completed scans with `BASELINE`, `NEW`,
  `PERSISTENT`, `FIXED`, `RECURRING`, and `NO DRIFT` states.
- Targets panel shows the five lab targets; Evaluation shows measured KPIs if the
  ground-truth join is clean.

## Non-goals / anti-goals

- No synthetic, seeded, or imported fake findings. Evidence only.
- No changes to the frozen classification rules, API contract, or UI dependencies.
- No tablet rail, new endpoints, or backend code changes.
- Do not delete or overwrite the existing local research database as part of the demo.

## Constraints

- Lab targets bind to `127.0.0.1` only.
- Scans require an attributable authorisation record, approved scope/ports, and an
  operator-or-higher role.
- `lab/domain.py` controls lab drift state; it does not register targets with the backend.
- The lab's `scans.json` history must have unique labels or `/api/evaluation` reports
  `available: false` with duplicate-label reasons.
- Tools required for real scans: `nmap`, `httpx`, and `testssl` (installed here at
  `/usr/local/bin/testssl`).

## Approaches considered

### Document shape

1. **Single demo guide** — architecture, stack, target loading, and rehearsal in one file.
2. Two documents — permanent architecture reference plus a demo runbook.
3. Short cheat sheet only.

**Chosen: 1.** It matches the request for one document and is organised around the live
demo.

### Data loading

1. **Run real lab scans now** — bring the lab up, sync targets, run a short labelled scan
   sequence through the API.
2. Restore an existing completed-scan database snapshot — none found on this machine.
3. Seed synthetic demo findings — rejected; it violates the evidence-only rule.

**Chosen: 1.** Real scans are the only honest way to populate the panel.

## Decisions

- Deliverable: `docs/DEMO_GUIDE.md`, committed to the repository.
- Database: use a dedicated demo database `demo-driftguard.db` at the repo root. The API
  is restarted with `DRIFTGUARD_DATABASE_URL=sqlite:///demo-driftguard.db`, so the existing
  `driftguard.db` research data is preserved.
- Lab: start with `cd lab && ./bootstrap.sh --up` (idempotent; safe before a demo).
- Targets: load all five lab targets with
  `cd backend && .venv/bin/python -m driftguard.sync --authorized-by ... --authorization-basis ...`.
- Lab history: archive `lab/eservices-lab/scans.json` before marking demo labels so
  evaluation is not blocked by duplicate `S0`/`S1`/`S2` labels.
- Scan sequence: the documented five-scan quick path, labelled `DEMO-0` … `DEMO-4`:
  1. clean baseline
  2. `tls-legacy` + `cert-mismatch` on
  3. `http-plain` on
  4. `tls-legacy` off, `port-open` on
  5. `tls-legacy` on
  This produces `NO DRIFT`, `NEW`, `PERSISTENT`, `FIXED`, and `RECURRING` on the TLS area
  and `NEW`/`PERSISTENT` on Network/Service.
- Run one real API scan per label per target (`POST /api/targets/{id}/scans?label=DEMO-n`),
  waiting for each to reach `completed`. If a target cannot be brought up, record the
  failure honestly and exclude it; do not invent evidence.
- Verification before handoff: `/api/stats` shows five targets and completed scans;
  `/api/targets/{id}/history` shows drift events; `/api/evaluation` is available with
  measured KPIs; the UI renders without fatal errors.

## Demo guide contents

1. What DriftGuard is, in plain language.
2. Text architecture diagram and data flow: lab → tools → engine → evidence/drift → API →
   Drift console.
3. Tech stack table: FastAPI, SQLAlchemy, SQLite/Alembic, Pydantic, SlowAPI, React 19,
   Vite, plain CSS, nmap/testssl/httpx/gobuster, Docker lab.
4. Target-loading paths: UI/API registration, lab bulk sync, lab drift scenarios.
5. Panel-by-panel talking points: Drift, Targets, Evaluation, Settings.
6. Rehearsal checklist and troubleshooting (ports, lab down, testssl failure, duplicate
   labels, failed scans).

## What is left to the builder

- Start the lab, restart the API against the demo database, sync targets, run and verify
  the labelled scans, then write and commit `docs/DEMO_GUIDE.md`.
- No product code changes are required.

## Amendments (2026-11-27, after approval)

Two facts found while writing the implementation plan
([`docs/superpowers/plans/2026-11-27-demo-guide-preload.md`](../plans/2026-11-27-demo-guide-preload.md))
correct this design without changing its intent:

1. **Archive path.** `lab/eservices-lab/scans.json` does not exist. The file with the
   duplicate `S0/S1/S2` labels that blocks `/api/evaluation` is **`lab/scans.json`**.
2. **Labelled scans.** "One real API scan per label per target" would put five completed
   scans under each `DEMO-n` label, and `evaluation_service._duplicate_completed_labels`
   groups by label without target — evaluation would stay `available:false`. The labelled
   sequence therefore runs on **`eservices-lab` only**; the other four targets are scanned
   unlabelled so their panels still fill with real evidence.

Consequences for the demo: scenario toggles are also applied to `eservices-lab` only (so
the four untouched targets stay clean and honestly show `NO DRIFT`), and the API area of
the Evaluation panel will report no present findings.
