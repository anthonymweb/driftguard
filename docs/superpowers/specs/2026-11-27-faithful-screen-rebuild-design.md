# Faithful screen rebuild — design

**Date:** 2026-11-27
**Status:** approved 2026-11-27

## Intent and why

The owner supplied eight Stitch screens (four surfaces, desktop and mobile) and said the
integrated console "looks understandable, vague and confused". The current console is a
simplified reinterpretation of those screens; no side-by-side comparison was ever done.
The owner chose **approach 1: a faithful rebuild** of the four supplied screens in React,
with real database values substituted for the fictional mock content.

Success for the demo tomorrow: at `#/drift/1`, `#/targets`, `#/evaluation` and
`#/settings`, at 1440×900 and 390×844, the console reads as the supplied screens —
same section order, density, hierarchy, typography, palette, icon language and mobile
composition — while every number, name, label and claim comes from a completed scan or
an authorisation record in `demo-driftguard.db`.

## Goals

- Rebuild Drift, Targets, Evaluation and Settings to mirror the supplied screens.
- Preserve the section order and visual weight of each screen, on desktop and mobile.
- Substitute every fictional value with a real value from `/api/targets`,
  `/api/targets/{id}/history`, `/api/stats` or `/api/evaluation`.
- Keep all six frozen classifications intact and use no others in user-facing copy.
- Keep the React 19 + Vite + plain-CSS dependency set; no Tailwind, UI kit or new runtime
  CDN dependency.
- Update the frontend tests to the rebuilt markup and keep both suites green.

## Non-goals

- Copying the mock identities, mandates, hashes, keys, percentages or provenance claims.
- Adding Tailwind, shadcn, Framer Motion or any new UI library to the product.
- Changing the backend, the classifier, the API contract, a database, or the lab fixture.
- Adding endpoints or new scan capabilities.
- Building dead UI workflows that have no backend counterpart.

## Anti-goals

- A screen that looks polished but asserts something the database does not contain.
- Treating an empty observation window as "all clear".
- Reintroducing "comparator" into user-facing copy (it is an internal metaphor only).
- A mobile view that is just the desktop grid narrowed.

## Constraints

- **Evidence only.** No seeded, simulated or inferred findings anywhere in the UI.
- **Frozen classification.** `BASELINE`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`,
  `NO DRIFT`. No `Skipped`, `Regressed` or other invented state.
- **Authorisation gate and scope** stay server-owned; the UI only displays what the API
  returns, including `scannable` and `refusal_reasons`.
- **Redaction** stays before export; the token map never leaves the process.
- **Local only:** API and UI bind to `127.0.0.1`. Research DB and lab state are untouched.
- The supplied HTML is a Tailwind CDN artifact and cannot be imported as-is; it is a
  visual specification to translate into plain CSS.
- The supplied desktop and mobile screens differ structurally, not just by breakpoint.
- Existing contracts: 93 frontend tests and 145 backend tests. The backend suite must
  remain untouched and green.
- Product dependency decision 8 in `docs/PROJECT-STATE.md` is binding: React 19, Vite,
  plain CSS, CDN fonts/icons with system fallbacks.

## Approaches considered

1. **Plain-CSS structural port (chosen).** Rebuild each page's JSX to the supplied
   hierarchy and translate the visuals into a new plain-CSS layer built on the existing
   tokens. Switch to the distinct mobile composition with the existing `useMediaQuery`
   hook where the supplied mobile screens genuinely differ. Trade-off: the most work,
   but no new dependency, offline-safe, and it keeps the data layer and frozen rules
   untouched. The owner picked this approach.
2. **Tailwind CDN port.** Paste the supplied markup into React with Tailwind classes.
   Closest pixels and fastest, but adds the runtime CDN dependency the project explicitly
   locked out, breaks offline use, and still needs the same fictional content stripped.
   Rejected; would require the owner to override the locked dependency decision.
3. **Incremental restyle of current components.** Already attempted in the Clarity
   restyle and rejected by the owner as vague and confused. Dropped.

## How it will be built

### Substitution map

| Supplied mock | Real source / treatment |
|---|---|
| `eservices-lab`, `127.0.0.1:8443`, "Citizen Public Portal", "Online" | `target.name`, `target.address`, `target.target_type`, `target.status`; no invented description or liveness claim |
| "5 observation runs since baseline" | count of comparable scans in `history.scans` |
| `Mandate #AUTH-2026-089-UG`, Dr. J. Mukasa, "166 days remaining" | `authorized_by`, `authorized_at`, `authorization_basis`, `approved_scope`, `approved_ports`; no expiry claim (the API has none) |
| New 1 / Persistent 3 / Resolved 2 / Regressions 1 | `latestComparable.summary.counts` for `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`; "Regressions" is not a frozen label, so the card reads "Recurring findings" |
| Timeline Run 1–5, `Skipped`, `Regressed` | real scans labelled `DEMO-n` or `#id` with their timestamps; cells render only frozen labels, with "not observed" for absent evidence and "unmeasured" for incomparable scans |
| CVE / CWE identifiers and handshake strings | `evidence.title`, `category`, `severity`, `resource` and real `details` rendered as key/value lines |
| Merkle root, chain height, Ed25519 signature, attestation timestamp | dropped; the accordion becomes "Evidence provenance" showing scan id, label and `observed_at` from the selected thread |
| "Create Patch Mandate", "Export Report", "Run Benchmark Calibration", "Export Node Config", "Rotate Signing Key", "Prune Buffers" | dropped; keep only Run Scan, Refresh and the existing redacted-evidence export |
| Footer "Daemon Active · Sync 100%", "Latency 18ms" | dropped; no fabricated telemetry |
| Targets: 5 endpoints / 60% ratified / 42m sweep | `targets.length`, authorised count, and the newest real `last_scan` timestamp; no invented cadence |
| Target filter counts All/Active/Pending/Halted | existing All/Authorised/Pending/Refused filters with real counts |
| Per-target mandate, days left, descriptive subtitles, statutory callout | real authorisation fields, `formatScope`, `formatPorts`, `refusal_reasons` |
| Evaluation: `DG-7740`, 98.3%, Cohen's κ, `n=120`, F1, Merkle seal, CLI harness | `generated_at`, `overall.detection_accuracy` (7/12), `false_positive_rate`, `unmeasured_scans`, `down_observations`, and real `per_area` rows; no κ or F1 because the backend does not compute them |
| Evaluation lower two-column module: per-classification fidelity bars and reproducible-CLI/provenance card | **keep the two-column shape for resemblance.** Left column uses real `per_area` accuracy counts; right column shows measurement scope — `generated_at`, `unmeasured` labels, and the honest caveat. The fabricated bars, CLI snippet and seal are dropped. |
| Methodology notice naming `ground_truth_v2.json` | existing honest caveat: scored against the lab ground truth; console scans are not scored |
| Target pills: "Active", "Baseline Verified (No Drift)", "1 Regression Detected", "Academic Exemption", "Scan Refused" | **server fields first**, then one read of `/api/targets/{id}/history` per target to show the most recent *stored* drift state as the pill. The page displays the backend's classification verbatim; it never derives one. `refusal_reasons` still drives the refused state. |
| Settings: PID 18492, Sys-Tick, v1.5.0-clarity, GPG key, audit sink path, root digest | real `apiBase`, `/api/stats` reachability, `auth_mode`, `redaction`, footprint counts, `APP_VERSION`, and a generated-at timestamp |
| Redaction diff with fake bearer/cookie/API-key values | drop the fake values; show the real enabled state and a neutral field-name legend (`Authorization`, `Cookie`, `X-Api-Key` → tokenised) |

### Structure

- `App.jsx` and `AppShell.jsx` keep routing, session and navigation; the shell is tuned to
  the supplied desktop sidebar and mobile header/tab-bar proportions but stays the same
  component.
- Each page component is rebuilt around the supplied section order. Page-local
  subcomponents (banner, metric card, timeline, panel) are introduced where they make
  the markup readable; `Icon`, `StateBlocks`, `RegisterTargetSheet`, `AuthorisationStamp`
  and `EvidenceDetail` are reused where their semantics still hold.
- A new plain-CSS visual layer carries the supplied density: card padding, 12–16px
  radii, label/display/mono type roles, pill badges, dividers, grid breakpoints and the
  mobile compositions. Existing token variables are the single source of colour and
  spacing. Legacy page CSS that no longer has a consumer is removed in the same change.
- Desktop/mobile switching: CSS media queries for layout that is the same content
  reflowed; the existing `useMediaQuery` hook only where the supplied screens use a
  different composition or ordering. Existing breakpoint behaviour (768px shell,
  900px thread grid) remains intact.
- Data flow stays server-owned: `useTargets`, `useHistory`, `client.stats()`,
  `client.evaluation()` and the frozen `buildThreadModel`. One additional read of
  `/api/targets/{id}/history` per target supplies the Targets pills; the page displays
  stored classifications verbatim and derives none.
- The known mode-chip finding is not reopened: the chip continues to reflect the real
  `auth_mode`/session state, and no new claim is added.
- Accessibility contracts from the current tests are preserved: labelled search,
  `aria-pressed` filters, `role="status"`/`role="alert"`, row headers, reachable actions,
  focus-visible styling and reduced-motion behaviour.

### Owner decisions and settled calls

The owner's tie-breaker: **resemblance to the supplied screens** wherever an evidence-only
substitution leaves a choice. That settled the two questions raised by the design review:

- **Evaluation lower half:** kept, populated with real per-area counts and measurement
  scope rather than fabricated fidelity bars and provenance.
- **Targets pills:** enriched with one stored-history read per target so the cards carry
  the reference's visual weight, without deriving a classification in the UI.

Calls made by the designer under the evidence-only rule, recorded so they can be checked
while reading:

- **Drift evidence diff:** render only the states actually stored for the selected thread
  (earliest observed, any recorded FIXED, latest). No "Verified Fix" card and no
  explanatory prose when the database has no such state.
- **Mobile Drift:** all stored threads remain reachable as stacked cards; the first is
  expanded by default so the deep link shows a finding detail immediately. Hiding real
  threads to copy the reference's single-card composition would be worse than the
  reference.
- **Evaluation unavailable:** keep the current single-panel state with the backend's real
  reason when `available: false`; do not render a four-section skeleton full of blanks.
- **Settings panels:** A = connection and mode, B = authorisation provenance from the real
  target/session fields, C = redaction, D = data footprint and version.
- **Footer/shell telemetry:** no invented daemon, latency, tick or sync values; keep the
  product name and real generated-at time only.

## Verification

- **Resemblance gate:** capture all four routes at 1440×900 and 390×844 next to the
  supplied `screen.png` files and compare section order, density, palette and typography.
  Any structural divergence needs a reason recorded here.
- `cd frontend && npm test` — tests updated to the new markup, all passing.
- `cd frontend && npm run build` — production build succeeds.
- `cd backend && .venv/bin/python -m unittest discover -s tests` — 145 passing, unchanged.
- Live CDP pass at 1440×900 and 390×844 on all four routes against the demo DB: capture
  screenshots next to the supplied `screen.png` files and confirm the DOM contains only
  real values. Screenshots stay in `/tmp/opencode/`, not in the repo.
- Update `docs/PROJECT-STATE.md` and `docs/development-log.md`; commit and push.

## Left to the builder

- Exact component split, class names and CSS file organisation.
- Per-test assertion updates while preserving the behavioural contracts listed above.
- The precise mapping of Settings' four panels onto the real `stats` fields.
- Any small visual adjustment needed to make a real value occupy the same visual slot as
  the mock value it replaces, without inventing content.
