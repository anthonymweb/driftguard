# Drift console — design

**Date:** 2026-11-24 · **Status:** approved 2026-11-24 by the owner; implementation
pending. **Plans:**
`docs/superpowers/plans/2026-11-24-drift-read-api.md` (backend, first) and
`docs/superpowers/plans/2026-11-24-drift-console-ui.md` (frontend, second).
**Supersedes:** the dashboard direction implicitly assumed by the old `frontend/`
**Owner decisions already made:** redesign the frontend (not restyle); make comparison
the organising principle; ignore the guided-demo work for now; visual direction
delegated to the designer.

## Language: product, mechanism, metaphor

These are three different things and must not be conflated:

| Layer | Language | Example |
|---|---|---|
| **Product / category** | security drift detection | "DriftGuard detects security drift on authorised targets." |
| **Core mechanism** | comparison between observations | "It compares each scan with the previous one." |
| **Internal design metaphor** | optical comparator / measurement sheet | Used in this document only. Never shown to users. |

"Comparator" is **not** user-facing copy. It is accurate about the mechanism but
reductive as a product name: it omits authorisation, evidence, redaction, and measured
accuracy, and it is overloaded (Java `Comparator`, the optical instrument, generic diff
tools). A panelist or executive should hear **drift detection** and **what changed**,
not "comparator".

UI vocabulary:

- Main destination: **Drift** — subtitle "What changed between scans."
- Other destinations: **Targets**, **Evaluation**, **Settings**.
- Classification tokens verbatim: `BASELINE`, `NO DRIFT`, `NEW`, `PERSISTENT`, `FIXED`,
  `RECURRING`.

## Intent and why

DriftGuard's job is to answer one question: **what changed since the previous authorised
observation?** The current dashboard answers a different, weaker question — "what is in
the database?" — with metric cards, severity bars, and three pages that read "Awaiting
assessment engine". It makes the system look like a SOC console with missing features,
when the actual system is a precise drift detector that already classifies change with
frozen rules.

The console must make the comparison itself the primary object. A reviewer should be
able to open one target and read, without explanation, which findings appeared,
persisted, were fixed, or returned — and see the authorisation record that made the
observation legitimate.

## Goals

- Make the **comparison** the first thing on screen: a target's scan history as a
  calibrated thread grid, one row per evidence fingerprint, one column per scan.
- Make the **authorisation record** permanently visible on the subject target, not a
  table cell: who authorised it, when, on what basis, and the approved scope/ports.
- Show only **stored evidence and stored drift events**. Never derive a finding, never
  seed a sample, never imply "all clear" from the absence of a scan.
- Surface **instrument accuracy** (detection accuracy, false-positive rate, unmeasured
  scans) as a first-class part of the system, not a script output.
- Make every empty, loading, error, pending, and incomplete state explicit and useful.
- Be usable in a live viva: deep-linkable target state, one-click redacted export,
  readable at projector distance, keyboard-navigable.

## Non-goals / anti-goals

- No fake or illustrative findings, including in empty states.
- No changes to the frozen classification rules or the authorisation contract.
- No dark "cyber" dashboard; the category default is not the brief.
- No icon-heavy navigation, metric-card grid, sparkline, severity bar chart, or gradient
  hero.
- No remediation workflow in this release. The model exists but there is no endpoint or
  business rule; showing a placeholder would be the same mistake as the old UI.
- No cloud hosting, analytics, or external AI in this release.
- No mobile-first rebuild at the expense of the viva surface; mobile is supported, not
  the design centre.

## Constraints

- Backend contract changes must be **additive**; existing tests are the contract.
- The comparator data exists but is unreachable over HTTP: `DriftEvent` and
  `Remediation` have no read endpoints, and evaluation is a CLI script.
- `NO DRIFT` is defined by `drift.py` but never persisted: a scan with an empty change
  set writes zero `DriftEvent` rows. The console derives the scan-level `NO DRIFT` state
  from that emptiness; it does not invent a per-fingerprint event.
- A `FIXED` fingerprint's evidence lives in an earlier scan, not the current one; the
  history response must carry fingerprint metadata for every referenced fingerprint.
- The API supports JWT auth when `DRIFTGUARD_AUTH_SECRET` is set and local-research mode
  when it is not. The console must work in both and say which mode it is in.
- Fonts must be self-hosted or degrade cleanly; the console may run without internet.

## Approaches considered

1. **Comparison-first console (chosen; previously called "comparator console").** One
   target is the subject. Its scan history is a thread grid; authorisation is a permanent
   stamp; evaluation is a separate accuracy report. Requires small additive read
   endpoints. Cost: backend work alongside the UI.
2. **Evidence workbench.** Keep a multi-target landing page and rebuild it around
   fingerprints, with a comparison drawer. Less backend work because transitions are
   derived client-side, but the UI's idea of drift can disagree with the authoritative
   `DriftEvent` rows. Rejected: two sources of truth for the core claim.
3. **Two-scan diff instrument.** One screen that compares any two scans side by side.
   Excellent for explanation, weak for authorisation and inventory work. Rejected as the
   whole product; its core idea survives inside the chosen design.

## The design

### Concept: the optical comparator sheet

The visual reference is a precision **optical comparator** and its measurement sheet:
a part is projected against a reference profile, deviations are read off a calibrated
axis, and a sign-off block records who approved the measurement. That is what DriftGuard
does with a target's security state.

This is a deliberate aesthetic risk: a **light, paper-like measurement sheet** in a
category saturated with near-black dashboards, neon accents, and glow. It is justified by
the subject, not by novelty. The interface should feel engraved, ruled, and quiet; the
data supplies the drama. The metaphor is internal; the UI never uses the word
"comparator".

### Palette

| Token | Value | Role |
|---|---|---|
| `--paper` | `#ECEAE3` | page ground, cool bone (not warm cream) |
| `--sheet` | `#F5F3ED` | raised sheet / selected row |
| `--ink` | `#15181A` | primary text, marks, rules of emphasis |
| `--ink-2` | `#565B5B` | secondary text, axis labels |
| `--rule` | `#C7C3B7` | hairlines, grid, column separators |
| `--signal` | `#1E45C8` | ultramarine: change, focus, links, newest scan |
| `--risk` | `#A93627` | oxide red: Critical/High severity only |
| `--verified` | `#2C6A4F` | FIXED / verified only |
| `--pending` | `#8A600F` | pending authorisation, warnings |

Ultramarine is the single interactive/change accent. Risk red and verified green are
**semantic**, never decorative. There are no gradients, glows, or translucent panels.

### Typography

- **Display / UI:** Chivo (700 headings, 400/500 text). A squared grotesque that reads as
  engineering rather than marketing.
- **Data:** Chivo Mono (400/500) for addresses, fingerprints, scan ids, dates, counts,
  axis labels, and classification tokens.
- Self-host WOFF2 files with their OFL licence. Fallback stacks:
  `ui-sans-serif, system-ui, sans-serif` and `ui-monospace, monospace`.
- Scale: 11px mono labels (uppercase, `0.08em` tracking) · 14px body · 16px row titles ·
  24–28px section headings · 40px only for the evaluation readouts. No 64px hero.
- Headings are sentence case. Classification tokens and engraved labels are uppercase
  mono.

### Layout

A ruled sheet, not a card dashboard:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ driftguard      drift   targets   evaluation   settings          [mode chip]  │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ TARGETS       │  eservices-lab                                               │
│               │  127.0.0.1:8443 · web                                        │
│ ● eservices   │  ┌ AUTHORISATION ─────────────────────────────────────────┐  │
│ ○ democommerce│  │ A. Owner · 12 Nov 2026 · written approval              │  │
│ ○ civic       │  │ scope TLS / NETWORK / API · ports 8443, 8080           │  │
│ ○ juice-shop  │  └────────────────────────────────────────────────────────┘  │
│ ○ vampi       │                                                              │
│               │  1 new · 2 persistent · 1 fixed since scan #12              │
│               │                                                              │
│               │        #10      #11      #12      #13      #14              │
│               │  TLS   ├────────┼────────┼────────┼────────┤ calibrated axis  │
│               │  tls-legacy   ■────────■────────■────────◇   PERSISTENT     │
│               │  cert-mismatch ○────────○────────–────────–   FIXED          │
│               │  NETWORK                                                     │
│               │  http-plain   ○────────■────────■────────■   NEW            │
│               │  API                                                         │
│               │  api-debug    ○────────○────────○────────●   PERSISTENT     │
│               │                                                              │
│               │  ┌ selected fingerprint ─────────────────────────────────┐  │
│               │  │ title · resource · severity · last observed            │  │
│               │  │ [local detail] [copy redacted record] [export scan]    │  │
│               │  └────────────────────────────────────────────────────────┘  │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

- **Top strip:** wordmark, four text destinations, and an auth/mode chip
  (`LOCAL RESEARCH` or `OPERATOR · name`). No icons in the primary nav.
- **Target index (left, 236px):** a specimen index, not a sidebar. Each row: name, mono
  address, last completed observation time, and a filled/hollow authorisation mark.
  Selected row gets a 2px signal rule on its left and `--sheet` ground.
- **Subject header:** target name, address/type, then the authorisation stamp. The stamp
  is a bordered block with `AUTHORISATION` as an engraved label. Pending targets read
  `PENDING — scanning refused` in `--pending`.
- **Difference line:** one sentence, exact counts, in body text with mono numerals:
  `1 new · 2 persistent · 1 fixed since scan #12`. If nothing changed: `No change since
  scan #12.` If baseline: `Baseline recorded 12 Nov 2026.` No metric cards.
- **Thread grid:** the signature element (below).
- **Detail rail:** anchored below the grid, not a floating drawer. Shows the selected
  fingerprint's metadata, the scan it was last observed in, and actions: reveal raw local
  detail (explicitly marked local-only), copy the redacted record for that fingerprint,
  and export the selected scan's redacted evidence.

### Signature: the thread grid

Each evidence fingerprint is a horizontal thread across the included scans.

| Mark | Meaning |
|---|---|
| filled ink tick `▮` | present in that scan |
| continuous ink rule | present in consecutive scans (PERSISTENT) |
| signal square `■` | NEW in that scan |
| signal diamond `◇` | returned after an absence (RECURRING) |
| open circle `○` | FIXED at the transition scan |
| short hairline dash `–` | known absent at a later scan (fixed and gone, not re-observed) |
| no mark | never observed before this point |
| hatched column | incomplete observation (failed / completed-with-errors) |
| shaded column | baseline scan |

- The axis is calibrated: scan column headers carry the id and date, with a tick for
  each scan. Columns are evenly spaced, newest at the right.
- Rows are grouped by the three audited areas in fixed order: TLS, NETWORK, API.
- A row's right-hand cell carries the current classification token and severity mark.
- **Incomplete observations do not advance the thread.** A `failed` or
  `completed_with_errors` scan is shown as a hatched column with the label
  `NOT COMPARED`; threads pass through with a dotted segment, and no absence/FIXED marks
  are produced. This is the rule that prevents a failed scan from falsely reporting that
  everything was fixed.
- Hovering or focusing a row lifts it 1px onto `--sheet` and fills the detail rail.
- The grid is a real table for assistive technology: `<table>` with a row header per
  fingerprint and a column header per scan; marks carry visually hidden text.
- Colour is never the only encoding: shape and token text carry the state.

### Page: Drift (default, requires a target)

Index, subject header, difference line, thread grid, detail rail. Empty target:
authorisation stamp plus `No observations yet. Run a baseline to start the record.` and a
primary scan action. Queued/running scans appear as a pending column with the scan's
status text; the console polls that scan until it settles, then refreshes. Settled means
`completed`, `completed_with_errors`, or `failed`; only `completed` enters the comparison.
New scan columns draw in once, left to right, 480ms, staggered 20ms per row, maximum 8
rows; `prefers-reduced-motion` disables the draw.

### Page: Targets

A register, not a table of cards. One row per target: name and mono address,
authorisation stamp or pending mark, approved scope as text chips, approved ports, last
observation, and actions (`Open`, `Run scan`). `Run scan` is disabled with the exact
refusal reason when the target is not scannable. **Register target** opens a right-hand
form sheet with three ruled sections: Identity, Authorisation, Scope. Choosing
`authorized` requires `authorized_by`, `authorized_at`, and `authorization_basis`;
validation is inline and specific. The form never silently substitutes defaults.

### Page: Evaluation

An accuracy report on paper. Two large readouts — `DETECTION ACCURACY` and
`FALSE-POSITIVE RATE` — each with its numerator/denominator underneath, then a ruled
per-area table (TLS, Network, API) with detections, misses, false positives, unmeasured
scans, and down observations. A caveat block states: `Scored against the lab's ground
truth. A label with no engine scan is unmeasured, not correct.` If the ground truth is
unavailable, the page says so and shows no numbers.

**Evaluation is decoupled from the console's `Run scan`.** Accuracy requires a
controlled, labelled lab sequence (`sequence.py`), so the report reads labelled scans
only. Console scans are exploratory and are not scored. The page states this; the console
does not offer a label field that an operator could misuse.

### Page: Settings

Connection (API base, reachable/unreachable), mode (`LOCAL RESEARCH` or JWT-authenticated
with user/role), redaction (exports are tokenised; the token map never leaves the
process), data footprint (targets, scans, evidence, drift events), version. No toggles
that do not do anything.

## Backend additions and corrections

These are **calls made during the builder check**. Veto any of them.

1. **Only `completed` scans are comparable.** `failed` and `completed_with_errors` scans
   are incomplete observations. They are returned by history but marked
   `comparable: false`, their drift rows are not rendered, and they do not become the
   "previous" scan for the difference line.
   - **Engine correction:** `_record_drift` currently writes drift before the final scan
     status is known, so a failed scan can store false `FIXED` rows. Move drift recording
     after the final status decision and record drift only for `completed` scans.
   - `_completed_scans_before` must use `completed` only, not `completed_with_errors`.
   - Classification rules are unchanged; this changes which observations are eligible.
2. **`TargetRead` gains `last_scan`, `scannable`, and `refusal_reasons`.** `last_scan` is
   `{id, status, started_at, completed_at}` or `null`; `scannable` and
   `refusal_reasons` come from `ensure_scannable`, so the UI's disabled action explains
   itself exactly. This is the "one response schema change" the earlier draft promised.
3. **A third read endpoint, `GET /api/stats`,** supplies the Settings footprint:
   `{targets, scans, evidence, drift_events, auth_mode, redaction: {enabled: true}}`.
   Without it, Settings would either fabricate counts or make per-target calls.
4. **`GET /api/targets/{target_id}/history?limit=20`** (default 20, max 100, newest
   first) returns the target, recent scans, each scan's evidence, drift events, computed
   summary, and a fingerprint metadata catalogue:

   ```json
   {
     "target": { "...": "TargetRead" },
     "scans": [
       {
         "scan": { "...": "ScanRead" },
         "comparable": true,
         "evidence": [ { "...": "EvidenceRead" } ],
         "drift": [
           { "id": 1, "scan_id": 14, "evidence_fingerprint": "eservices-lab/TLS/tls-legacy",
             "classification": "PERSISTENT", "recorded_at": "..." }
         ],
         "summary": { "state": "BASELINE | NO DRIFT | CHANGED | INCOMPLETE",
                      "counts": { "NEW": 0, "PERSISTENT": 0, "FIXED": 0, "RECURRING": 0 } }
       }
     ],
     "fingerprints": {
       "eservices-lab/TLS/tls-legacy": {
         "title": "...", "category": "TLS", "severity": "High", "resource": "..."
       }
     }
   }
   ```

   `summary.state` is `INCOMPLETE` when the scan is not comparable, `BASELINE` when it is
   the first completed scan, `NO DRIFT` when a comparable scan has zero drift events,
   otherwise `CHANGED`. Failures are surfaced, not hidden, and not compared.
5. **`GET /api/evaluation`** returns `200` with either
   `{"available": false, "reason": "..."}` or
   `{"available": true, "generated_at": "...", "overall": {...}, "per_area": {...},
   "per_target": {...}}`, computed read-only by the existing evaluator. It loads only
   `completed` labelled scans. **Duplicate scan labels make the join ambiguous:** if any
   label appears more than once, return `available: false` with the duplicated labels and
   a remediation hint. No silently wrong accuracy numbers.
6. **Export shape.** The scan-level export is the existing
   `GET /api/scans/{scan_id}/evidence/redacted`, downloaded as CSV from the detail rail.
   The fingerprint action copies that fingerprint's redacted JSON record to the
   clipboard. Whole-target export is out of scope for this release.
7. **Thread semantics for absence.** The mark table distinguishes FIXED (the transition),
   known-absent at later scans (short dash), and never-observed (blank), so a reviewer
   can tell "fixed and gone" from "never seen". The row's current token stays `FIXED`
   until a recurrence.

Both new read endpoints and the stats endpoint use the same auth as the rest of the API.
Tests cover: unknown target (404); baseline summary; NO DRIFT summary; CHANGED counts;
INCOMPLETE scan excluded from comparison; FIXED metadata present via the catalogue; limit
clamping; `TargetRead` refusal reasons; stats counts; evaluation unavailable path;
duplicate-label rejection; auth enforcement.

## Frontend architecture

- Keep React 19 + Vite. Replace the single 257-line `App.jsx` with:
  - `src/api/client.js` — fetch wrapper, JWT header, typed errors, abort support.
  - `src/state/useHashRoute.js` — `#/drift/:targetId`, `#/targets`, `#/evaluation`,
    `#/settings`; deep links work on refresh.
  - `src/components/` — `AppShell`, `TargetIndex`, `AuthorisationStamp`,
    `DifferenceLine`, `ScanAxis`, `ThreadGrid`, `ThreadRow`, `EvidenceDetail`,
    `RegisterTargetSheet`, `SignIn`.
  - `src/pages/` — `Drift`, `Targets`, `Evaluation`, `Settings`.
  - `src/styles/` — `tokens.css`, `base.css`, `drift.css`, `targets.css`,
    `evaluation.css`, `responsive.css`.
- No routing library, no state library, no chart library. `lucide-react` is retained only
  for universal actions (refresh, close, external link); navigation is typographic.
- Data flow: `/api/targets` for the index; one `/api/targets/{id}/history` call per
  selected target (removes the old N+1); `/api/stats` for Settings; `/api/evaluation`
  only when its page is open. Abort in-flight requests on target switch. No background
  polling except the scan the user just queued.
- Auth: on `401`, open a compact sign-in sheet; keep the token in memory plus
  `sessionStorage`; clear on expiry or `401`; show the role in the top strip. In
  local-research mode, no sign-in is shown and the mode chip says `LOCAL RESEARCH`.
- Fonts self-hosted under `src/assets/fonts/`; if missing, the fallback stack must not
  change layout materially.
- Frontend tests: `vitest` for pure logic (summary grouping, thread layout including
  FIXED/known-absent/incomplete, hash route, date formatting) plus a small number of
  component smoke tests. No snapshot-testing of the whole page.

## Copy rules

- Name things by what the person controls: `Run scan`, `Register target`, `Export
  redacted evidence`. Never `Submit`, `Execute`, or `Leverage`.
- State facts, not moods: `No observations yet.` not `Your journey starts here.`
- Errors say what happened and what to do: `API unreachable at 127.0.0.1:8000. Start the
  backend, then retry.` No apologies.
- Empty is an invitation to act, and it never implies safety.
- Never use "comparator" in user-facing copy. Say "comparison" or "what changed".

## Accessibility and quality floor

- Keyboard: target index, grid rows, detail rail, form sheets, and dialogs fully
  operable; visible 2px `--signal` focus ring with offset.
- Contrast meets WCAG AA on `--paper` and `--sheet`.
- Motion respects `prefers-reduced-motion`.
- Grid uses table semantics; marks have text alternatives; no state is colour-only.
- Responsive: at ≤900px the index becomes a target selector and the grid becomes stacked
  fingerprint cards with a compact timeline; the detail rail becomes a bottom sheet. At
  ≤600px the top nav collapses to a menu, actions stack, and the evaluation readouts
  remain legible at 28px.
- Loading uses ruled skeleton rows, not spinners in the middle of the sheet.

## What is left to the builder

- Exact SVG/CSS construction of the thread marks and the calibrated axis, including the
  incomplete-column and reduced-motion variants.
- Component boundaries within `src/components` and the internal shape of the history
  hook.
- The precise self-hosted font subsetting and fallback metrics.
- Vitest configuration and the list of pure-function tests.
- Whether to remove the unused Tailwind dependency now or after the redesign lands.
- Whether `GET /api/evaluation` should reuse `backend/evaluate.py` directly or extract a
  testable loader; either is acceptable if it stays read-only and covered by tests.
- Whether the engine correction in item 1 should also delete already-stored drift rows
  for historical incomplete scans, or simply exclude them at read time. The design
  requires the read behaviour; the historical cleanup is optional and may be a one-off
  migration script.

## Verification

- `cd backend && .venv/bin/python -m unittest discover -s tests` stays green, with new
  tests for the endpoints, the eligibility rule, the refusal reasons, and the
  duplicate-label rejection.
- `cd frontend && npm run build` succeeds; `npm test` (vitest) passes.
- Live: run the API, sync the lab, scan `eservices-lab` at baseline and with `tls-legacy`
  on, and confirm the console reads `PERSISTENT`/`NEW` from stored `DriftEvent` rows —
  not from client-side inference.
- Deliberately fail a scan and confirm it appears as `NOT COMPARED` without FIXED marks
  and without changing the difference line.
- Empty, offline, pending-authorisation, auth-required, evaluation-unavailable, and
  duplicate-label states are each exercised.
