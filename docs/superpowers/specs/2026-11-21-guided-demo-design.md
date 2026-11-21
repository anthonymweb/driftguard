# Guided demonstration of DriftGuard — design

**Date:** 2026-11-21 · **Status:** awaiting approval
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
  register → baseline → NEW → PERSISTENT → FIXED → RECURRING → redacted export.
- Every scan, finding, and classification shown is **real** — produced by the
  engine against a lab target bound to 127.0.0.1.
- The UI shows a step-by-step narration panel alongside the live data so the
  viewer always knows what is happening and why it matters.
- The demo is idempotent: safe to run twice; a failed run can be reset and
  re-run.

## Non-goals / anti-goals

- No seeded or simulated findings in the live app (violates the project's own
  evidence rule and the brief's real-scanning requirement).
- No new classification rules — BASELINE, NEW, PERSISTENT, FIXED, RECURRING,
  NO DRIFT stay frozen exactly as specified.
- No changes to the redaction rule: tokenise before any AI call; the token map
  never leaves the local environment. The demo only *shows* already-redacted
  output.
- No scanning outside the lab's authorised 127.0.0.1 targets.
- Not a video-production task: built for a live viva first; its repeatability
  also makes it easy to screen-record if a recording is later required
  (open question, see below).

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

### 2. Backend — demo orchestration script `demo.py` (repo root)

A CLI script (not an API endpoint — it is a presenter's tool, not part of the
service contract) that assumes the API is already running and:

1. **Preflight** — checks `/ready`, that the lab target answers, and that the
   target is registered (registers it via the API with the attributable
   authorisation record: who/when/basis) — reusing it if already present.
2. **Baseline** — ensures the scenario is clean (`domain.py off` for the demo
   scenarios), queues the first scan, waits for completion.
3. **NEW** — `domain.py on tls-legacy`, rescan, waits; asserts the expected
   classification appeared (fails loudly rather than narrating a wrong claim).
4. **PERSISTENT** — rescan with the flaw still on.
5. **FIXED** — `domain.py off tls-legacy`, rescan.
6. **RECURRING** — `domain.py on tls-legacy`, rescan.
7. **Redacted export** — fetches `GET /api/scans/{id}/evidence/redacted`,
   prints a small sample showing `IP_…`/`URL_…` tokens, and states that the
   token map stays local.

Each step: prints a narration line to the console **and** advances the UI
narration state (see part 3). On assertion failure it stops with a clear
message and non-zero exit. `--reset` re-runs the lab's state cleanly first;
default run is safe to repeat (it re-uses the existing target and continues
the story from a fresh baseline).

### 3. Frontend — narration panel + drift page

- **Demo narration strip** (top of the dashboard area): shows the current step
  number, title, and one-line explanation ("Flaw introduced → the next scan
  marks the finding NEW"), advancing as the script progresses. Driven by the
  script through a small, clearly-labelled demo channel (see open question 1).
  When no demo is running the strip is absent — zero impact on normal use.
- **Drift history page** (replaces the placeholder): a per-target timeline of
  real `DriftEvent` rows with the classification badges, scan references, and
  the frozen-label legend. This is a real product page, not demo-only.
- Visual quality follows the frontend-design guidance already agreed:
  professional, practitioner-grade, no templated AI look.

### 4. Verification

- Backend: full suite green; new endpoint tests included.
- Live: `demo.py` run end-to-end twice in a row (idempotency), each step's
  asserted classification matches what the UI shows.
- The nine-scan lab sequence and evaluation remain reproducible (no changes to
  the lab).

## What's left to the builder

- Exact shape of the narration channel between `demo.py` and the UI
  (open question 1 — decided below once answered).
- Wait/poll strategy for background scan completion and reasonable timeouts.
- Layout details of the narration strip and drift timeline within the
  existing design system (styles, iconography, spacing).

## Open questions for the owner

1. **Narration channel:** (a) `demo.py` posts step state to a tiny,
   clearly-labelled `POST /api/demo/step` endpoint the UI polls — works with
   the normal dev setup, one extra endpoint; or (b) the script writes a
   `demo/state.json` the frontend dev server watches — no API surface, but
   only works when UI and script share a filesystem. **My pick: (a)** — it
   works in any deployment and keeps one source of truth.
2. **Recording:** you did not answer whether a recorded video is also
   required. The design optimises for a live, repeatable run; if a recording
   is required later we simply screen-record a run — no design change.
