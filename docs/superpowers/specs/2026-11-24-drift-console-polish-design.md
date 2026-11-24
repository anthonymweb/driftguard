# Drift console polish — design

**Date:** 2026-11-24  
**Status:** Proposed for approval  
**Owner decision:** Approach 1, paper-first Drift polish, selected by the owner on 2026-11-24.

## Intent

DriftGuard already has a working, evidence-only console. This work is not a new product concept and not a new application. It is a focused polish of the surfaces that already exist so the Drift page reads unmistakably as a **time-based classification console**.

The guiding sentence stays:

> Show change over time against a baseline — never a pile of one-off findings.

Every polished screen must answer: *what changed, compared to what, and is the fix verified?*

## Goals

1. Make the Drift hero screen read as an observation record: subject, authorisation, difference summary, classification timeline, evidence rail.
2. Make the frozen classification vocabulary visually unmistakable and consistent everywhere it appears.
3. Fix the four code-level Important findings from the independent review before visual polish:
   - stale history can overwrite the newly selected target;
   - the UI derives `PERSISTENT` when a stored drift row is absent;
   - the mode chip can claim `LOCAL RESEARCH` under JWT auth with no session;
   - dialogs do not contain, restore, or release keyboard focus correctly.
4. Polish Targets as a register, not a CRM: authorisation stamp, scope, ports, last scan, scannable vs refused, and direct scan/open actions.
5. Keep Evaluation as an honest research report: plain numbers and tables, with unmeasured scans called out.
6. Preserve all existing API integration, authorisation behaviour, redaction boundary, and responsive `ThreadGrid`/`ThreadCards` behaviour.

## Non-goals

- No backend changes, no new endpoints, no schema changes.
- No change to the frozen classification rules in `backend/driftguard/drift.py`.
- No dark navy reskin, no left sidebar, no Overview, Scans, or Reports pages.
- No global risk score, threat map, decorative charts, attack animation, remediation ticketing, or AI chat panel.
- No guided-demo strip in this pass. It may be revisited only if a real `demo.py` is shipped.
- No lab-driven viva in this implementation pass. It remains a separate verification step that needs lab state and operator approval.

## Anti-goals

- Do not invent, seed, or simulate findings.
- Do not derive a classification in the UI when the backend did not store one.
- Do not hide authorisation refusal reasons.
- Do not expose raw evidence as a shareable surface; redacted export remains the only shareable path.
- Do not silently remove a working control or test.

## Constraints

- Existing stack: React 19, Vite 8, plain CSS, Vitest + Testing Library. No new component framework or UI library.
- Existing design tokens remain authoritative: paper `#ECEAE3`, sheet `#F5F3ED`, ink `#15181A`, rule `#C7C3B7`, signal blue `#1E45C8`, risk red `#A93627`, verified green `#2C6A4F`, Chivo + Chivo Mono.
- Existing four-page IA remains: `Drift`, `Targets`, `Evaluation`, `Settings`.
- Hash routing and deep links remain.
- API contract remains: `GET /api/targets`, `GET /api/targets/{id}/history`, `GET /api/stats`, `GET /api/evaluation`, `GET /api/targets/{id}/scans`, `POST /api/targets/{id}/scans`, `GET /api/scans/{id}/evidence/redacted`, and auth endpoints in `frontend/src/api/client.js`.
- There is no global scans endpoint and no report-generation endpoint. Do not pretend otherwise.
- Frozen labels: `BASELINE`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, `NO DRIFT`.
- Product language stays “drift detection” and “what changed between scans.” The internal design metaphor name must not appear in user-facing copy.

## Approaches considered

### 1. Paper-first Drift polish — chosen

Keep the approved paper design, top navigation, and four surfaces. Fix the review issues first, then sharpen the Drift hero, shared classification badges, evidence rail, Targets register, and Evaluation tables. This is the smallest change that directly improves what an examiner sees and preserves the research thesis. It does not invent unsupported pages.

### 2. Dark reskin, same information architecture

Replace the paper tokens with the navy/teal palette and a sidebar while keeping the same four pages. This changes the entire visual identity without adding product capability. It would require broad CSS rework and new responsive shell tests, and it fights the first brief’s explicit “paper UI, not dark SOC cosplay.”

### 3. Full second brief — dark sidebar plus Overview/Scans/Reports

Add a left sidebar and three new pages. Overview and Scans can be assembled only from existing target/history/stats data; Reports would be an honest empty state because no report endpoint exists. This is the largest scope and conflicts with the owner’s “do not add new pages” instruction, so it was not selected.

## Decided design

### Application shell

- Keep the horizontal top strip with `driftguard`, primary nav, mode chip, and sign-out.
- Make the mode chip truthful with an explicit state machine:
  - before service state resolves: `MODE PENDING`;
  - `/api/stats` succeeds with `auth_mode === "local_research"`: `LOCAL RESEARCH`;
  - `/api/stats` succeeds in JWT mode with a session: `OPERATOR · username` or role as already shown;
  - `/api/stats` returns 401 in JWT mode with no session: `SIGN IN REQUIRED`, never `LOCAL RESEARCH`; the existing unauthorized handler may open the sign-in sheet;
  - `/api/stats` returns 503 or the API is unreachable: `MODE UNAVAILABLE`, never `LOCAL RESEARCH`.
- This is the design author's call: a 401 is proof that auth is enabled, and an unreadable service must not be presented as local research.
- Keep desktop nav visible and the narrow-view `Menu` button. Improve its active state and focus visibility without changing the route set.

### Drift hero

Desktop hierarchy:

```
[target index] | SUBJECT · address · type        [Refresh] [Run scan]
               | AUTHORISATION STAMP · scope · ports
               | Difference summary
               | Classification timeline / thread grid
               | Evidence rail
```

- Keep `TargetIndex` at left on desktop and its narrow behaviour.
- Subject header keeps engraved `SUBJECT`, name, mono address/type, refresh, and scan action.
- Authorisation stamp stays immediately under the subject.
- Difference line stays directly above the thread grid and uses stored summary counts only.
- Scan control:
  - one primary header action only;
  - label is `Run baseline` when the record has no comparable scan and `Run scan` afterwards;
  - remove the duplicate baseline button from the empty sheet; the empty state explains the action and points to the header control;
  - while queued/running, show clear pending feedback and keep pending columns visible;
  - if not scannable, keep refusal reasons visible; never disable silently.
- Baseline empty state copy: `Baseline recorded. No prior scan to compare.` when the only comparable scan is a baseline with no drift events.
- Empty database copy remains honest: `No observations yet. Run a baseline to start the record. Nothing is inferred from an empty database.`

### Classification badge contract

Introduce one shared visual mapping used by the grid/current column, `ThreadCards`, and the difference summary. The mark shapes in the current grid may remain, but every visible classification label must use the same treatment:

| Label | Treatment |
|-------|-----------|
| `NEW` | Filled signal blue badge |
| `PERSISTENT` | Neutral ink outline badge |
| `FIXED` | Verified green badge |
| `RECURRING` | Risk red badge with slight emphasis |
| `NO DRIFT` | Quiet muted chip in the difference summary only, when a prior comparable scan exists |
| `BASELINE` | First scan state, not an event badge |

`NO DRIFT` is a scan-level summary from the backend, never a stored per-fingerprint drift event. It must not appear as a row/current-column classification. When evidence exists but no drift event was stored, show no classification label. Use a neutral `No stored classification` detail state. Do not fall back to `PERSISTENT`.

### Thread grid and cards

- Preserve the existing `buildThreadModel` shape, `ThreadGrid`, `ThreadRow`, and `ThreadCards` behaviour unless a tested equivalent is supplied.
- Rows are fingerprints; columns are scans over time; cells show the stored classification at that scan.
- Selecting a row opens `EvidenceDetail`.
- Narrow screens keep one finding per card with a mini history strip using the same badge mapping.
- Improve row/card selection affordance with visible focus and selected state.

### Evidence detail

- Keep `EvidenceDetail` sourced from `row.detail`, `row.observedAt`, and the stored scan history.
- Clear local/raw rail copy: it is local detail, not the shareable surface.
- Keep the redacted export action pointed at `/api/scans/{id}/evidence/redacted`.
- Add clear loading, success, and failure feedback for redacted fetch/export.
- Do not add prose explanations of a finding that are not derived from stored evidence.

### Targets register

Keep the existing register and registration sheet. Polish each row to show at a glance:

- name and mono address/type;
- compact authorisation stamp (who / when / basis);
- scope chips: `TLS` · `Network` · `API`;
- approved ports in mono;
- last scan id/status/time;
- scannable vs refused, with refusal reasons visible on refusal;
- `Open` and `Run scan` actions with current disabled/busy states.

The authorisation fields remain required when status is `authorized`. That strictness is intentional.

### Evaluation

- Keep the existing tables and readouts; no decorative charts.
- Preserve detection accuracy, false-positive rate, detections, misses, false positives, unmeasured scans, and down observations.
- Show per-area results for TLS, Network, and API, and per-target results when the API supplies them.
- Scored copy stays explicit: measurements are against laboratory ground truth; a scan with no engine counterpart is unmeasured, not correct.
- Fix the current unconditional remediation text: only recommend renaming duplicate labels when duplicates are actually present; otherwise state the real reason from `data.reason`.

### Settings

- Preserve connection state, auth mode, session information, redaction status, data footprint, and version.
- Improve status indicators and panel readability without exposing secrets or token values.
- Continue to derive auth mode from `/api/stats`, not from the absence of a session.

### Review fixes with tests

1. **History race:** replace the shared boolean liveness guard in `useHistory` with a request generation or active-target guard. A test must prove that a late response from target A cannot write into target B’s state after a switch.
2. **Frozen classification:** remove the `PERSISTENT` fallback in `buildThreadModel`. A test must prove that a comparable non-baseline scan with evidence but no stored drift row does not display `PERSISTENT`.
3. **Mode truth:** add a test for JWT mode with no session that rejects `LOCAL RESEARCH`.
4. **Dialog keyboard behaviour:** add focus containment, restore, and Escape handling for `RegisterTargetSheet` and `SignIn`, with rendered-focus tests.

### Minor findings included as polish

- Narrow polling in `useHistory` to a scan the current user just queued where the API response makes that distinguishable; otherwise keep polling but document why it cannot be narrowed.
- Keep evaluation remediation copy conditional on actual duplicate labels.
- Harden client-side CSV export: defer object-URL revocation and neutralise leading spreadsheet formula characters.
- Backend-side evaluation error hygiene remains out of scope because this pass makes no backend changes; the UI may avoid echoing raw exception-looking text.

## Verification expected from the builder

- `cd backend && .venv/bin/python -m unittest discover -s tests` stays green.
- `cd frontend && npm test` passes with new regression tests.
- `cd frontend && npm run build` passes.
- Browser capture of `Targets`, `Evaluation`, and `Settings`, plus empty-register `Drift`, at desktop and narrow widths shows no console or page errors. Populated Drift captures require a real lab target and scan and belong to the separate viva pass.
- No user-facing occurrence of the internal design-metaphor word.
- Review fixes are verified by tests before visual polish is called complete.

## What is left to the builder

The builder decides file-level structure, component extraction, CSS selector names, and test names. The builder may add a small shared classification badge/token helper if that removes duplication. The builder must not change backend behaviour or API contracts.

If a narrow-view or focus behaviour cannot be tested in the existing jsdom setup, the builder should say so explicitly and cover it with a browser capture instead of claiming a unit test exists.
