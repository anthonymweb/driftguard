# Guided demonstration of DriftGuard — design

**Date:** 2026-11-21 · **Status:** revised after builder check + owner decisions,
awaiting approval
**Context:** the project brief requires a demonstration of how the system works.
The chosen approach (Option A) is a guided demo script that drives the *real*
system through its full story, with narration, rather than a fake-data
simulation.

## Intent and why

An examiner (or any reviewer) must be able to see, in one sitting, how
DriftGuard works end to end: an authorised target is registered, assessed,
drift is classified across consecutive assessments with the frozen labels, and
evidence is exported in redacted form. The demonstration must be repeatable
(a viva can be re-run after a hiccup) and must never present fabricated
findings as real — the dashboard itself promises findings are evidence-backed
only.

## Goals

- One command walks the system through the canonical story:
  register → baseline → NO DRIFT → NEW → PERSISTENT → FIXED → RECURRING →
  redacted export (the full set the approved 2026-11-07 spec §6.5 quick path
  promises, plus BASELINE as the first scan's silence).
- Every scan, finding, and classification shown is **real** — produced by the
  engine against a lab target bound to 127.0.0.1.
- The UI shows a step-by-step narration panel alongside the live data so the
  viewer always knows what is happening and why it matters.
- The demo is idempotent: safe to run twice; a failed run can be reset and
  re-run.
- **Deliverable:** a screen recording of one clean run, alongside the live
  capability (owner decision, 2026-11-21). The design still optimises for a
  live, repeatable viva first — the recording is captured from that same run.

## Non-goals / anti-goals

- No seeded or simulated findings in the live app (violates the project's own
  evidence rule and the brief's real-scanning requirement).
- No changes to the classification rules — BASELINE, NEW, PERSISTENT, FIXED,
  RECURRING, NO DRIFT stay frozen exactly as specified. Persisting the
  already-specified NO DRIFT event is implementation of those rules (its
  definition and semantics are unchanged), not a rule change.
- No changes to the redaction rule: tokenise before any AI call; the token map
  never leaves the local environment. The demo only *shows* already-redacted
  output.
- No scanning outside the lab's authorised 127.0.0.1 targets.
- The recording deliverable does not change the architecture: it is captured
  from the same repeatable run used live (tooling and clean-take procedure in
  part 5).

## Constraints

- Lab targets must be up (Docker) and bind to 127.0.0.1 only.
- The API runs with auth in local-research mode (no `DRIFTGUARD_AUTH_SECRET`),
  so the demo needs no login; role gating is exercised separately, not in this
  demo.
- Backend test suite (127 tests) must stay green; new endpoints are covered by
  strict TDD like the rest of Phase 4.
- The working disk (sda6) is degraded: all work is committed and pushed; the
  demo must not depend on files only present in damaged directories.

## Approaches considered

1. **Guided demo script over the real API (chosen).** `demo.py` drives the
   seven steps through the running FastAPI service while the UI narrates.
   Real scans, real classification, repeatable. Cost: needs the lab's Docker
   targets and one missing read endpoint.
2. **Manual demonstration.** No new build; click through the UI while running
   the lab sequence by hand. Rejected: nine manual scans mid-viva is where
   fumbling happens, and the reviewer never sees the story arc.
3. **Fake-data simulation mode.** Rejected outright: contradicts the brief
   ("must actually scan") and the UI's own promise that findings are never
   sample data.

## What already exists (recon findings)

- The engine already classifies drift on every scan and persists
  `DriftEvent` rows (`_record_drift` in `driftguard/scanner/engine.py`);
  the first scan of a target intentionally emits no events (baseline).
- `driftguard/drift.py` implements the frozen classification rules; lab
  evaluation recorded detection accuracy 1.0 / false-positive rate 0.0.
- The lab's `lab/sequence.py` runs the canonical nine-scan sequence (S1–S9)
  that exercises every classification state; `lab/domain.py` CLI controls the
  scenarios (`on`/`off` tls-legacy, cert-mismatch, http-plain, port-open,
  api-debug).
- The frontend has a placeholder "Drift history" page waiting on a read
  endpoint; targets/scans/findings pages already call the real API.
- Docker is available; lab targets (eServices portal at 127.0.0.1:8443, plus
  demcommerce, civic portal, Juice Shop, VAmPI) are defined in
  `lab/domain/targets/`.

## The parts

### 1. Backend — drift read endpoint (TDD)

- `GET /api/targets/{target_id}/drift` → newest-first list of drift events for
  a target: `{id, scan_id, evidence_fingerprint, classification, recorded_at}`
  plus enough scan context (scan label/status, observed time) for a timeline.
- Role: `viewer` (read-only), consistent with the other GETs.
- 404 when the target does not exist.
- Tests: happy path ordering, empty result for a fresh target, 404, and
  auth-mode behaviour (401 without a token when auth is on).

### 1b. Backend — persist the NO DRIFT event (TDD)

**Owner decision (2026-11-21): the demo exhibits NO DRIFT for real.** The
classification rules already define NO DRIFT ("an empty change set produces a
single NO DRIFT event at the caller level" — `driftguard/drift.py` docstring),
but `_record_drift` never emits it. This implements the specified behaviour:

- When `classify()` returns an empty change set **and** a previous scan exists,
  the engine writes one `DriftEvent` with `classification="NO DRIFT"` and a
  fixed sentinel fingerprint (the column is `NOT NULL`; a documented constant
  such as `"—"` distinguishes it from any real finding fingerprint).
- First scan of a target still emits nothing (BASELINE remains the absence of
  events) — unchanged.
- The frozen rules themselves are untouched; the existing
  `test_no_drift_has_no_fingerprint_event` behaviour is reviewed and updated
  only where it asserted the old omission, with the reason recorded.
- Tests: no-change rescan emits exactly one NO DRIFT event; a rescan with
  changes emits none; first scan emits none; repeated no-change scans each
  record their own event.

### 2. Backend — demo orchestration script `demo.py` (repo root)

A CLI script (not an API endpoint — it is a presenter's tool, not part of the
service contract). **Builder check resolved: repeat runs get a genuinely fresh
baseline by running the demo against a dedicated demo database.** The script
owns a backend process started with
`DRIFTGUARD_DATABASE_URL=sqlite:///demo-driftguard.db`:

- The evaluation database (with its labelled S0–S9 scans that `evaluate.py`
  depends on) is never touched.
- Re-running = stop the demo backend, delete `demo-driftguard.db`, start
  again; the target then starts with no history, so the baseline is silent and
  step "NEW" classifies as NEW, not RECURRING. `--reset` performs exactly
  this; a plain run against a leftover demo DB fails loudly with instructions
  rather than narrating a wrong classification.
- The lab scenario state is converged to clean first (`domain.py off` for the
  demo scenarios) so no stale flaw is carried into the baseline.

Steps:

1. **Preflight** — starts the demo-backend (or attaches with `--no-server`),
   checks `/ready`, that the lab target answers, and that the target is
   registered (registers it via the API with the attributable authorisation
   record: who/when/basis).
2. **Baseline** — scenarios clean, queues the first scan, waits for
   completion; asserts no drift events were emitted (BASELINE = silence).
3. **NO DRIFT** — rescan with nothing changed; asserts exactly one
   `NO DRIFT` event (part 1b makes this possible).
4. **NEW** — `domain.py on tls-legacy`, rescan, waits; asserts the expected
   classification appeared (fails loudly rather than narrating a wrong claim).
5. **PERSISTENT** — rescan with the flaw still on.
6. **FIXED** — `domain.py off tls-legacy`, rescan.
7. **RECURRING** — `domain.py on tls-legacy`, rescan.
8. **Redacted export** — fetches `GET /api/scans/{id}/evidence/redacted`,
   prints a small sample showing `IP_…`/`URL_…` tokens, and states that the
   token map stays local.

Each step: prints a narration line to the console **and** advances the UI
narration state (see part 3). On assertion failure it stops with a clear
message and non-zero exit.

### 3. Frontend — narration panel + drift page

- **Demo narration strip** (top of the dashboard area): shows the current step
  number, title, and one-line explanation ("Flaw introduced → the next scan
  marks the finding NEW"), advancing as the script progresses. Driven by the
  script through a small, clearly-labelled demo channel (part 2's step
  posting; see decisions). When no demo is running the strip is absent —
  zero impact on normal use.
- **Live data during the run (builder check resolved):** while the narration
  strip is visible, each new step triggers a refetch of the dashboard,
  findings, and drift pages, so data never appears frozen behind an advancing
  narration. Outside a demo the pages keep today's fetch-once + manual
  Refresh behaviour — no polling is introduced into normal use.
- **Drift history page** (replaces the placeholder): a per-target timeline of
  real `DriftEvent` rows with the classification badges (including NO DRIFT),
  scan references, and the frozen-label legend. This is a real product page,
  not demo-only.
- Visual quality follows the frontend-design guidance already agreed:
  professional, practitioner-grade, no templated AI look.

### 4. Verification

- Backend: full suite green; new endpoint + NO DRIFT event tests included.
- Live: `demo.py` run end-to-end twice in a row (idempotency via the demo
  database), each step's asserted classification — including the NO DRIFT
  event — matches what the UI shows.
- The nine-scan lab sequence and evaluation remain reproducible (the demo's
  backend uses its own database; no changes to the lab).

### 5. Recording deliverable (owner decision: required)

- Procedure: one clean `demo.py` run with the screen recorder capturing the
  dashboard (narration strip + live data) and the console narration; a short
  clean-take checklist (containers up, `--reset` first, no terminal clutter).
- Tooling: an existing open-source recorder (e.g. OBS or the GNOME built-in
  recorder) — no new software is developed for this.
- Artefact: video stored on the sda4 backup drive (and not committed to git —
  it does not belong in the repository); the repair-kit README folder shows
  where it lives. Verification = the recording plays end-to-end and every
  asserted classification is visible on screen.

## What's left to the builder

- Wait/poll strategy for background scan completion and reasonable timeouts.
- Layout details of the narration strip and drift timeline within the
  existing design system (styles, iconography, spacing).
- The concrete shape of the demo channel (a `POST /api/demo/step` endpoint
  that the UI polls — the approach chosen in the decisions below).

## Decisions (owner, 2026-11-21)

1. **Narration channel:** `demo.py` posts step state to a tiny,
   clearly-labelled `POST /api/demo/step` endpoint the UI polls — works with
   the normal dev setup in any deployment, one source of truth.
   (Design call, confirmed implicitly: no objection was raised to the pick.)
2. **Repeat runs / fresh baseline:** the demo runs against a dedicated demo
   database owned by `demo.py`; the evaluation database and its labelled
   S0–S9 scans are never touched. (Design call resolving builder question 1.)
3. **NO DRIFT:** exhibited for real — one extra no-change scan step plus the
   TDD'd engine change to persist the already-specified NO DRIFT event
   (part 1b), matching approved spec §6.5. (Owner decision.)
4. **Live data during the run:** step-triggered refetch while the narration
   strip is visible; no polling in normal use. (Design call resolving
   builder question 3.)
5. **Recording:** required as a deliverable — captured from the same
   repeatable run used live (part 5). (Owner decision.)
