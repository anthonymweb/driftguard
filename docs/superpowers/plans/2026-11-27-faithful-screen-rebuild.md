# Faithful Screen Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the four DriftGuard console screens so they visually mirror the eight supplied Stitch screens while displaying only values from completed scans and authorisation records.

**Architecture:** Keep React routing, state hooks, API client, and `buildThreadModel` intact; replace page markup and the plain-CSS layer with a reference-faithful visual system. Add small read-only helpers for stored target state and stored evidence snapshots; never classify in the UI or change the backend classifier.

**Tech Stack:** React 19.3.1, Vite 8.3.6, Vitest 5.1.1, Testing Library React 16.3.3, plain CSS, Material Symbols CDN with system fallbacks.

**Spec:** `docs/superpowers/specs/2026-11-27-faithful-screen-rebuild-design.md`

## Global Constraints

- Evidence only: every displayed finding, count, label, timestamp, and authorisation value must come from `demo-driftguard.db` via `/api/targets`, `/api/targets/{id}/history`, `/api/stats`, or `/api/evaluation`.
- No seeded, simulated, invented, or UI-derived findings.
- Frozen classifications: `BASELINE` · `NEW` · `PERSISTENT` · `FIXED` · `RECURRING` · `NO DRIFT`.
- Do not render `Skipped`, `Regressed`, or any other invented finding state.
- Do not use “comparator” in user-facing copy; say **drift detection** or **what changed between scans**.
- Backend `backend/driftguard/drift.py` is frozen; do not modify it.
- Authorisation gate stays server-owned: `authorization_status=authorized` plus `authorized_by`, `authorized_at`, `authorization_basis`, and approved scope/ports.
- Redaction stays before export; the token map never leaves the backend process.
- API binds to `127.0.0.1:8000`; Vite binds to `127.0.0.1:5173`; lab targets bind to `127.0.0.1` only.
- Do not modify `backend/driftguard.db`, `lab/scans.json`, or the lab fixture.
- Demo evidence lives in `demo-driftguard.db`; after any `driftguard.sync`, reapply `eservices-lab.approved_ports=[8443]`.
- React 19 + Vite + plain CSS only; no Tailwind, shadcn/ui, Framer Motion, UI kit, or new runtime dependency.
- Existing suites: 145 backend tests and 93 frontend tests. Backend suite stays untouched and green.
- Work from a feature branch off `origin/main`; use `using-git-worktrees` if isolation is needed.

## Review Focus

- Empty data window: an authorised target with no scans must show an explicit empty state, not zeros, “all clear”, or a fake finding. Pinned in Task 2 and Task 5.
- Incomplete or queued scan columns: must render as not compared/pending with no finding classification. Pinned in Task 2.
- Pending or refused target: must show stored refusal reasons, disabled scan action, and no invented authorisation record. Pinned in Task 2 and Task 4.
- Target pills: must show one stored backend state per target from one history read; no UI-invented label when no comparable scan exists. Pinned in Task 4.
- Narrow viewport: every stored thread must remain reachable; the first thread is expanded by default, and no real finding is hidden to copy the reference. Pinned in Task 3.
- Missing redacted record: copy/export must fail with the backend/API reason and never expose local raw detail. Pinned in Task 3.

## File Structure

### Create

- `frontend/src/lib/target-state.js` — pure lookup of the newest stored drift/summary state for one target history.
- `frontend/src/lib/target-state.test.js` — contract tests for that lookup.
- `frontend/src/state/useTargetStates.js` — one stored-history read per target for the Targets pills.
- `frontend/src/state/useTargetStates.test.js` — hook contract tests.
- `frontend/src/components/TargetStatePill.jsx` — renders a frozen stored state or an honest no-state mark.
- `frontend/src/components/TargetStatePill.test.jsx` — pill contract tests.
- `frontend/src/lib/snapshots.js` — selects only already-stored evidence states for the selected thread.
- `frontend/src/lib/snapshots.test.js` — snapshot selection tests.
- `frontend/src/components/EvidenceSnapshots.jsx` — renders stored snapshot cards.
- `frontend/src/components/EvidenceSnapshots.test.jsx` — snapshot rendering tests.

### Modify

- `frontend/src/styles/tokens.css` — add missing reference radius/type aliases only; keep all existing Clarity token values.
- `frontend/src/styles/base.css` — shared card, eyebrow, pill, chip, icon-tile, KPI, progress, and accordion primitives.
- `frontend/src/styles/shell.css` — desktop top header/footer and mobile header/tab bar proportions.
- `frontend/src/styles/drift.css` — Drift subject, authorisation band, metrics, timeline matrix, evidence detail.
- `frontend/src/styles/targets.css` — Targets header, stat tiles, toolbar, roster cards, register drawer.
- `frontend/src/styles/evaluation.css` — Evaluation header, notice, KPIs, area table, lower two-column module.
- `frontend/src/styles/settings.css` — Settings ribbon, 2×2 panels, mobile stacked panels, closing banner.
- `frontend/src/styles/responsive.css` — reflow rules at 900/767/600px and reduced-motion gate.
- `frontend/src/components/AppShell.jsx` — desktop top navigation variant, mobile header/tab bar unchanged in composition.
- `frontend/src/components/TargetIndex.jsx` — subject pills/select styled to the reference.
- `frontend/src/components/ScanAxis.jsx` — add Category and Severity column headers.
- `frontend/src/components/ThreadGrid.jsx` — wrap the dense reference table; preserve table semantics.
- `frontend/src/components/ThreadRow.jsx` — category chip, severity cell, frozen state pills.
- `frontend/src/components/ThreadCards.jsx` — expanded selected card for mobile.
- `frontend/src/components/AuthorisationStamp.jsx` — styling hooks only; preserve stored-field text nodes.
- `frontend/src/components/EvidenceDetail.jsx` — reference detail header, snapshots, provenance accordion.
- `frontend/src/pages/Drift.jsx` — reference section order and first-thread selection.
- `frontend/src/pages/Targets.jsx` — reference header, stat tiles, toolbar, roster cards.
- `frontend/src/pages/Evaluation.jsx` — reference KPI/table/lower module shape.
- `frontend/src/pages/Settings.jsx` — reference ribbon and A–D panels.
- `frontend/src/App.jsx` — pass `targets` into Settings.
- Existing `*.test.jsx` files named in each task; pure lib/state/API tests remain untouched except where a task names them.
- `docs/DEMO_GUIDE.md`, `docs/PROJECT-STATE.md`, `docs/development-log.md` — final runbook and handoff updates.

---

### Task 1: Visual foundation and reference shell

**Files:**
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/base.css`
- Modify: `frontend/src/styles/shell.css`
- Modify: `frontend/src/styles/responsive.css`
- Modify: `frontend/src/components/AppShell.jsx:1-64`
- Test: `frontend/src/components/AppShell.test.jsx`

**Interfaces:**
- Consumes: `route = { page, targetId }`, `mode = { kind: 'operator', username, role } | { kind: 'local' }`, `onSignOut`, `narrow`, `children`.
- Produces: desktop `.topbar` with one `<nav aria-label="Primary">`, `.console`, optional `.footer`; mobile `.mobile-bar`, `.tab-bar`, `.console`. No `.sidebar`.

- [ ] **Step 0: Prepare the feature branch**

Before changing files, create or switch to a feature branch off `origin/main` using `using-git-worktrees` if isolation is needed. Confirm `git status --short` shows only the approved design-doc edit and this plan, then proceed.

- [ ] **Step 1: Write the failing shell tests**

Replace the desktop sidebar test in `frontend/src/components/AppShell.test.jsx` with:

```jsx
it('renders a top navigation bar on desktop and marks the current page', () => {
  const { container } = render(
    <AppShell
      route={{ page: 'targets', targetId: null }}
      mode={{ kind: 'operator', username: 'alice', role: 'admin' }}
      onSignOut={vi.fn()}
    >
      <p>body</p>
    </AppShell>,
  );

  expect(container.querySelector('.topbar')).toBeTruthy();
  expect(container.querySelector('.sidebar')).toBeNull();
  expect(screen.getAllByRole('navigation')).toHaveLength(1);
  expect(screen.getByRole('link', { name: 'Targets' }).getAttribute('aria-current')).toBe('page');
  expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
  expect(screen.getByText(/^v\d+\.\d+\.\d+$/)).toBeTruthy();
  expect(screen.getByText('body')).toBeTruthy();
});
```

Keep the existing mobile tab-bar and sign-out tests unchanged except for renaming the first test.

- [ ] **Step 2: Run shell tests to verify they fail**

Run: `cd frontend && npm test -- src/components/AppShell.test.jsx`

Expected: FAIL because `.topbar` is not rendered and `.sidebar` still exists.

- [ ] **Step 3: Implement the reference shell and shared primitives**

In `AppShell.jsx`, render a fixed desktop `<header className="topbar">` containing the brand shield tile, version chip, `DriftGuard`, one four-link `<nav>`, mode chip, and optional sign-out. Use a segmented capsule class for `route.page === 'drift' || route.page === 'targets'` and plain nav-link styling for `evaluation`/`settings`; do not render a second `<nav>`. Add a minimal desktop footer with product name and version only; no daemon, latency, tick, or sync values. Keep the narrow branch and all link hrefs/`aria-current` behaviour unchanged.

In CSS, add only the shared primitives needed by later tasks: `.surface-card`, `.eyebrow`, `.mono-chip`, `.status-pill`, `.icon-tile`, `.kpi-card`, `.progress-track`, `.accordion-trigger`, and `.hairline`. Add `--radius-xs: 4px`; keep existing Clarity token values and all current focus-visible/reduced-motion behaviour.

- [ ] **Step 4: Run shell tests and full frontend suite**

Run: `cd frontend && npm test`

Expected: all AppShell tests PASS; all other 92 existing tests remain PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/tokens.css frontend/src/styles/base.css frontend/src/styles/shell.css frontend/src/styles/responsive.css frontend/src/components/AppShell.jsx frontend/src/components/AppShell.test.jsx
git commit -m "refactor(ui): build reference visual shell"
```

---

### Task 2: Drift subject, authorisation, metrics, and timeline

**Files:**
- Modify: `frontend/src/pages/Drift.jsx:99-215`
- Modify: `frontend/src/components/TargetIndex.jsx:1-52`
- Modify: `frontend/src/components/ScanAxis.jsx:16-38`
- Modify: `frontend/src/components/ThreadGrid.jsx:6-48`
- Modify: `frontend/src/components/ThreadRow.jsx:13-52`
- Modify: `frontend/src/styles/drift.css`
- Test: `frontend/src/pages/Drift.test.jsx`
- Test: `frontend/src/components/TargetIndex.test.jsx`
- Test: `frontend/src/components/ThreadGrid.test.jsx`

**Interfaces:**
- Consumes: `buildThreadModel(history) -> model`, `model.scans[]`, `model.groups[].rows[]`, `row.cells[]`, `row.current.classification`, `formatDate`, `formatScope`, `formatPorts`.
- Produces: desktop Drift section order `.subject` → `.stamp` → `.difference-line` → `.metric-cards` → `.thread-wrap`; table columns Finding / Category / Severity / scans / Current.

- [ ] **Step 1: Write failing Drift structure tests**

Add to `frontend/src/pages/Drift.test.jsx`:

```jsx
it('keeps the reference section order with real stored values', async () => {
  const { container } = await renderDrift();
  await screen.findByRole('heading', { name: 'eservices-lab' });

  const order = [
    '.subject',
    '.stamp',
    '.difference-line',
    '.metric-cards',
    '.thread-wrap',
  ].map((selector) => container.querySelector(selector));

  for (let index = 1; index < order.length; index += 1) {
    expect(order[index - 1].compareDocumentPosition(order[index])
      & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  }
  expect(screen.getByText('TLS / NETWORK · PORTS 8443, 8080')).toBeTruthy();
});
```

Update `frontend/src/components/ThreadGrid.test.jsx` so the table contract includes the reference columns:

```jsx
expect(screen.getByRole('columnheader', { name: /Category/ })).toBeTruthy();
expect(screen.getByRole('columnheader', { name: /Severity/ })).toBeTruthy();
expect(screen.getByRole('columnheader', { name: /#2/ })).toBeTruthy();
expect(screen.getByText('NOT COMPARED')).toBeTruthy();
expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
expect(screen.getByText('FIXED')).toBeTruthy();
expect(screen.getByText('baseline observation')).toBeTruthy();
```

Keep all existing Drift, TargetIndex, and ThreadGrid behavioural tests intact.

- [ ] **Step 2: Run the three test files to verify they fail**

Run: `cd frontend && npm test -- src/pages/Drift.test.jsx src/components/TargetIndex.test.jsx src/components/ThreadGrid.test.jsx`

Expected: FAIL for missing section order/Category/Severity assertions.

- [ ] **Step 3: Rebuild the Drift upper and timeline sections**

In `Drift.jsx`, keep all loading/error/empty/refusal branches. Replace the current top region with: subject header showing target name, `address · target_type`, stored `target.status`, and Refresh/Run scan actions; full-width `AuthorisationStamp` band; `DifferenceLine`; four fixed-height KPI cards from `latestComparable.summary.counts`; then `PendingScanPanel` and `ThreadGrid`. Omit metric cards entirely when `counts` is absent. Do not add an Export Report action.

In `TargetIndex.jsx`, render desktop target pills and the narrow `<select aria-label="Subject">` exactly as before, but add reference styling hooks (`.target-chip`, `.index-mark`, `.index-last`).

In `ScanAxis.jsx`, add `Category` and `Severity` column headers before scan columns and keep `columnState(scan)` unchanged.

In `ThreadGrid.jsx`, set group `colSpan` to `model.scans.length + 4`; keep the visually-hidden caption and all table roles.

In `ThreadRow.jsx`, add `<td className="thread-category">` with a `.mono-chip` containing `row.category`, `<td className="thread-severity">` with stored `row.severity`, and render each existing scan cell as a rounded `.state-pill` containing the existing visually-hidden `MARK_TEXT` and a visible frozen token only when `cell.classification` exists. Incomplete and pending cells keep their honest text alternatives and no classification.

Rewrite `drift.css` to the reference: tinted authorisation band, 12px card radius, 36px KPI numbers, 13px labels, 8px table head text, tinted table header, highlighted latest scan column, and horizontally scrollable matrix. Preserve `.visually-hidden`, focus-visible, and reduced-motion rules.

- [ ] **Step 4: Run the three test files and full frontend suite**

Run: `cd frontend && npm test -- src/pages/Drift.test.jsx src/components/TargetIndex.test.jsx src/components/ThreadGrid.test.jsx && npm test`

Expected: all PASS; frozen classification strings unchanged.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Drift.jsx frontend/src/components/TargetIndex.jsx frontend/src/components/ScanAxis.jsx frontend/src/components/ThreadGrid.jsx frontend/src/components/ThreadRow.jsx frontend/src/styles/drift.css frontend/src/pages/Drift.test.jsx frontend/src/components/TargetIndex.test.jsx frontend/src/components/ThreadGrid.test.jsx
git commit -m "feat(ui): rebuild drift subject and timeline"
```

---

### Task 3: Stored evidence snapshots and mobile thread composition

**Files:**
- Create: `frontend/src/lib/snapshots.js`
- Create: `frontend/src/lib/snapshots.test.js`
- Create: `frontend/src/components/EvidenceSnapshots.jsx`
- Create: `frontend/src/components/EvidenceSnapshots.test.jsx`
- Modify: `frontend/src/components/EvidenceDetail.jsx`
- Modify: `frontend/src/components/ThreadCards.jsx`
- Modify: `frontend/src/pages/Drift.jsx`
- Modify: `frontend/src/styles/drift.css`
- Modify: `frontend/src/styles/responsive.css`
- Test: `frontend/src/components/EvidenceDetail.test.jsx`
- Test: `frontend/src/components/ThreadCards.test.jsx`
- Test: `frontend/src/pages/Drift.test.jsx`

**Interfaces:**
- Consumes: `row.cells[]`, `row.current.classification`, `row.observedAt`, `scans[]`, `client.redactedEvidence(scanId)`.
- Produces: `storedSnapshots(row, scans) -> Array<{ scanId, state, time, detail }>`; `EvidenceSnapshots({ snapshots })`; `EvidenceDetail` keeps the same props.
- Snapshot states may only be `BASELINE`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, or the stored scan summary state `NO DRIFT`.

- [ ] **Step 1: Write failing snapshot tests**

Create `frontend/src/lib/snapshots.test.js`:

```js
import { storedSnapshots } from './snapshots';

it('returns only states present in the stored thread', () => {
  const row = {
    cells: [
      { kind: 'baseline', classification: null, scanId: 1 },
      { kind: 'present', classification: null, scanId: 2 },
      { kind: 'fixed', classification: 'FIXED', scanId: 3 },
      { kind: 'recurring', classification: 'RECURRING', scanId: 4 },
    ],
    current: { classification: 'RECURRING', scanId: 4 },
    observedAt: '2026-11-24T10:00:00Z',
    detail: { cipher: 'RC4' },
  };
  const scans = [1, 2, 3, 4].map((id) => ({
    id,
    completedAt: `2026-11-2${id - 1}T10:00:00Z`,
    summary: { state: id === 1 ? 'BASELINE' : 'CHANGED' },
  }));

  const snapshots = storedSnapshots(row, scans);

  expect(snapshots.map((snapshot) => snapshot.state)).toEqual([
    'BASELINE', 'FIXED', 'RECURRING',
  ]);
  expect(snapshots.every((snapshot) => ['BASELINE', 'FIXED', 'RECURRING']
    .includes(snapshot.state))).toBe(true);
});

it('does not invent a fixed snapshot when none is stored', () => {
  const snapshots = storedSnapshots(
    { cells: [{ kind: 'baseline', classification: null, scanId: 1 }],
      current: { classification: 'BASELINE', scanId: 1 },
      observedAt: null, detail: null },
    [{ id: 1, completedAt: null, summary: { state: 'BASELINE' } }],
  );

  expect(snapshots.some((snapshot) => snapshot.state === 'FIXED')).toBe(false);
});
```

Create `frontend/src/components/EvidenceSnapshots.test.jsx`:

```jsx
it('renders stored snapshot cards without explanatory invention', () => {
  render(<EvidenceSnapshots snapshots={[
    { scanId: 1, state: 'BASELINE', time: '12 Nov 2026 · 09:30 UTC', detail: {} },
    { scanId: 3, state: 'FIXED', time: '14 Nov 2026 · 09:30 UTC', detail: {} },
  ]} />);

  expect(screen.getAllByRole('article')).toHaveLength(2);
  expect(screen.getByText('BASELINE')).toBeTruthy();
  expect(screen.getByText('FIXED')).toBeTruthy();
  expect(screen.queryByText(/Verified Fix/)).toBeNull();
});
```

Add to `frontend/src/components/ThreadCards.test.jsx`:

```jsx
it('keeps every stored thread reachable and expands the selected one', () => {
  const model = {
    scans: [{ id: 1 }, { id: 2 }],
    groups: [{ key: 'TLS', rows: [
      { fingerprint: 'a', title: 'First thread', resource: 'r1', severity: 'High',
        cells: [{ kind: 'baseline' }, { kind: 'present' }],
        current: { classification: 'PERSISTENT', scanId: 2 } },
      { fingerprint: 'b', title: 'Second thread', resource: 'r2', severity: 'Low',
        cells: [{ kind: 'baseline' }, { kind: 'fixed' }],
        current: { classification: 'FIXED', scanId: 2 } },
    ] }],
  };

  render(<ThreadCards model={model} selected="a" onSelect={vi.fn()} />);

  expect(screen.getByRole('heading', { name: 'First thread' })).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Second thread' })).toBeTruthy();
  expect(screen.getByRole('button', { name: /First thread/ }).closest('li')
    .className).toContain('is-expanded');
});
```

- [ ] **Step 2: Run new and affected tests to verify they fail**

Run: `cd frontend && npm test -- src/lib/snapshots.test.js src/components/EvidenceSnapshots.test.jsx src/components/ThreadCards.test.jsx src/components/EvidenceDetail.test.jsx src/pages/Drift.test.jsx`

Expected: FAIL because `snapshots.js` and `EvidenceSnapshots.jsx` do not exist and mobile expansion is absent.

- [ ] **Step 3: Implement stored snapshots and reference detail composition**

In `snapshots.js`, export `storedSnapshots(row, scans)`. Select the first observed cell, the first `fixed` cell if present, and the last observed cell if different; deduplicate by `scanId`, preserving that order. Map `cell.classification` to state when present; otherwise use `scan.summary.state === 'BASELINE' ? 'BASELINE' : storedCurrentState(row).classification` for the first/last observed cell and `FIXED` for a fixed cell. Drop a card whose state is not a frozen stored classification — an unclassified current observation is omitted, never labelled `PERSISTENT`. Set `time` from `formatDateTime(scan.completedAt ?? scan.startedAt)`. Set `detail` from `scan.item.evidence.find((item) => item.fingerprint === row.fingerprint)?.details`, or `null` when that scan has no stored evidence for the fingerprint — never from `row.detail`, which is the latest observation. Sort the final cards by `scanId` after deduplication. Never create a snapshot from `incomplete`, `pending`, `absent`, or `never` cells.

In `EvidenceSnapshots.jsx`, render an `<article className="snapshot-card state-{state.toLowerCase()}">` per snapshot with the state, `#{scanId}`, time, and a mono `<pre>` of stored detail. Do not render explanatory prose or unverified fix claims.

In `EvidenceDetail.jsx`, keep all existing copy/export behaviour and injected `copy`/`download` props. Restructure the component into: header badges (`storedCurrentLabel(row)`, category, resource), title, stored snapshot cards, `.detail-actions` with existing buttons, a collapsed `<details className="accordion-trigger">` provenance block showing scan id, stored scan label, and `row.observedAt`, then the existing `.detail-local` raw-detail block with `LOCAL DETAIL · NOT REDACTED`. When no frozen classification is stored for the current scan, the badge reads `NO STORED CLASSIFICATION` instead of the UI fallback. Only the redacted endpoint is used for copy/export.

In `ThreadCards.jsx`, add `is-expanded` to the selected card and render `EvidenceSnapshots` plus the selected card’s stored state inside it. Keep the hidden timeline text (`#{id} — MARK_TEXT`) intact and keep every `onSelect` button reachable.

In `Drift.jsx`, initialise `selectedFingerprint` to the first stored row fingerprint when the model first becomes available, and preserve selection on reload for the same target. On narrow screens render `ThreadCards` followed by `EvidenceDetail` for the selected row; do not hide unselected real threads.

Rewrite the detail and mobile parts of `drift.css`/`responsive.css`: three snapshot cards in a 3-column desktop grid, stacked on mobile; collapsed provenance accordion; mobile subject/auth/KPI cards with 16px gutters and a 2×2 metric grid; bottom tab-bar padding cleared.

- [ ] **Step 4: Run affected tests and full frontend suite**

Run: `cd frontend && npm test -- src/lib/snapshots.test.js src/components/EvidenceSnapshots.test.jsx src/components/ThreadCards.test.jsx src/components/EvidenceDetail.test.jsx src/pages/Drift.test.jsx && npm test`

Expected: all PASS; EvidenceDetail still calls `client.redactedEvidence(2)` for the last observed scan.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/snapshots.js frontend/src/lib/snapshots.test.js frontend/src/components/EvidenceSnapshots.jsx frontend/src/components/EvidenceSnapshots.test.jsx frontend/src/components/EvidenceDetail.jsx frontend/src/components/ThreadCards.jsx frontend/src/pages/Drift.jsx frontend/src/styles/drift.css frontend/src/styles/responsive.css frontend/src/components/EvidenceDetail.test.jsx frontend/src/components/ThreadCards.test.jsx frontend/src/pages/Drift.test.jsx
git commit -m "feat(ui): rebuild stored evidence detail and mobile threads"
```

---

### Task 4: Targets register and stored target-state pills

**Files:**
- Create: `frontend/src/lib/target-state.js`
- Create: `frontend/src/lib/target-state.test.js`
- Create: `frontend/src/state/useTargetStates.js`
- Create: `frontend/src/state/useTargetStates.test.js`
- Create: `frontend/src/components/TargetStatePill.jsx`
- Create: `frontend/src/components/TargetStatePill.test.jsx`
- Modify: `frontend/src/pages/Targets.jsx`
- Modify: `frontend/src/styles/targets.css`
- Test: `frontend/src/pages/Targets.test.jsx`

**Interfaces:**
- Consumes: `client.history(id)` and `/api/targets` fields `id`, `name`, `address`, `target_type`, `authorization_status`, `authorized_by`, `authorized_at`, `authorization_basis`, `approved_scope`, `approved_ports`, `last_scan`, `scannable`, `refusal_reasons`.
- Produces: `latestStoredState(history) -> { classification, scanId } | null`; `useTargetStates(client, targets) -> { states, loading }`; `TargetStatePill({ state })`.
- `states[id]` uses only stored `drift[].classification` or stored `summary.state`.

- [ ] **Step 1: Write failing stored-state tests**

Create `frontend/src/lib/target-state.test.js`:

```js
import { latestStoredState } from './target-state';

it('reads the newest stored drift classification', () => {
  expect(latestStoredState({ scans: [
    { comparable: true, scan: { id: 1 }, drift: [], summary: { state: 'BASELINE' } },
    { comparable: true, scan: { id: 2 },
      drift: [{ classification: 'RECURRING', recorded_at: '2026-11-24T10:00:00Z' }],
      summary: { state: 'CHANGED' } },
  ] })).toEqual({ classification: 'RECURRING', scanId: 2 });
});

it('reads a stored clean state without inventing a finding', () => {
  expect(latestStoredState({ scans: [
    { comparable: true, scan: { id: 1 }, drift: [], summary: { state: 'NO DRIFT' } },
  ] })).toEqual({ classification: 'NO DRIFT', scanId: 1 });
});

it('returns null when no comparable scan exists', () => {
  expect(latestStoredState({ scans: [
    { comparable: false, scan: { id: 1, status: 'queued' }, drift: [], summary: {} },
  ] })).toBeNull();
});
```

Create `frontend/src/state/useTargetStates.test.js`:

```jsx
it('reads one stored history per target and exposes the latest state', async () => {
  const client = {
    history: vi.fn().mockResolvedValue({ scans: [
      { comparable: true, scan: { id: 9 }, drift: [], summary: { state: 'NO DRIFT' } },
    ] }),
  };
  const { result } = renderHook(() => useTargetStates(client, [{ id: 1 }, { id: 2 }]));

  await waitFor(() => expect(result.current.loading).toBe(false));

  expect(client.history).toHaveBeenCalledTimes(2);
  expect(client.history).toHaveBeenCalledWith(1);
  expect(client.history).toHaveBeenCalledWith(2);
  expect(result.current.states[1]).toEqual({ classification: 'NO DRIFT', scanId: 9 });
});
```

Create `frontend/src/components/TargetStatePill.test.jsx`:

```jsx
it('shows a stored frozen state or an honest no-state mark', () => {
  const { rerender } = render(<TargetStatePill state={{ classification: 'FIXED', scanId: 3 }} />);
  expect(screen.getByText('FIXED')).toBeTruthy();

  rerender(<TargetStatePill state={null} />);
  expect(screen.getByText('—')).toBeTruthy();
  expect(screen.getByLabelText(/No stored drift state/)).toBeTruthy();
});
```

Add to `frontend/src/pages/Targets.test.jsx`:

```jsx
it('shows one stored drift state pill per target', async () => {
  const props = renderPage({
    client: {
      ...makeClient(),
      history: vi.fn().mockResolvedValue({ scans: [
        { comparable: true, scan: { id: 7 },
          drift: [{ classification: 'RECURRING', recorded_at: '2026-11-24T10:00:00Z' }],
          summary: { state: 'CHANGED' } },
      ] }),
    },
    targets: [target, civic],
  });

  await waitFor(() => expect(props.client.history).toHaveBeenCalledTimes(2));
  expect(screen.getAllByText('RECURRING')).toHaveLength(2);
});
```

Use `makeClient()` from the existing test file’s client helper; do not hardcode new finding data in product code.

- [ ] **Step 2: Run new and affected tests to verify they fail**

Run: `cd frontend && npm test -- src/lib/target-state.test.js src/state/useTargetStates.test.js src/components/TargetStatePill.test.jsx src/pages/Targets.test.jsx`

Expected: FAIL because the new modules do not exist and Targets does not read history.

- [ ] **Step 3: Implement target state lookup, hook, pill, and reference register**

In `target-state.js`, sort comparable scans by `scan.id` ascending, take the last one, and choose the drift event with the greatest `recorded_at` (falling back to array order) when `drift` is non-empty. Otherwise use `summary.state` only when it is `BASELINE` or `NO DRIFT`. Return `null` for all other cases.

In `useTargetStates.js`, on `targets` change, call `client.history(id)` exactly once per target, ignore stale responses, and return `{ states: Record<number, {classification, scanId}|null>, loading }`. No retry loops and no classification derivation.

In `TargetStatePill.jsx`, render `<span className="status-pill" aria-label={...}>` with the stored classification or `—` plus a visually-hidden `No stored drift state` label when null.

In `Targets.jsx`, keep all existing filters, search, role gates, register sheet, scan handlers, and callback identities. Add the hook and render `TargetStatePill` in each roster card. Rebuild the page markup into: page head (`TARGET REGISTER` / `Targets` / lede / Register target), three stat tiles (`Registered`, `Authorized`, `Refused`), one toolbar with `All/Authorized/Pending/Refused` tabs and labelled search, then vertical roster cards. Each card shows identity, stored state pill, `AuthorisationStamp compact`, scope/ports, last scan, and Open/Run scan actions. Refused cards get `.is-refused` with a left stripe and the stored `refusal_reasons` callout; no other card receives that stripe.

Rewrite `targets.css` to the reference: 3 stat cards, compact shared toolbar, 12px roster cards with 16/24px padding, `xl` two-column card split, right-anchored register drawer, 16px mobile gutters, 3-up bento stats, and horizontally scrollable filter chips.

- [ ] **Step 4: Run affected tests and full frontend suite**

Run: `cd frontend && npm test -- src/lib/target-state.test.js src/state/useTargetStates.test.js src/components/TargetStatePill.test.jsx src/pages/Targets.test.jsx && npm test`

Expected: all PASS; each target causes exactly one history read.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/target-state.js frontend/src/lib/target-state.test.js frontend/src/state/useTargetStates.js frontend/src/state/useTargetStates.test.js frontend/src/components/TargetStatePill.jsx frontend/src/components/TargetStatePill.test.jsx frontend/src/pages/Targets.jsx frontend/src/styles/targets.css frontend/src/pages/Targets.test.jsx
git commit -m "feat(ui): rebuild target register with stored state pills"
```

---

### Task 5: Research evaluation report

**Files:**
- Modify: `frontend/src/pages/Evaluation.jsx`
- Modify: `frontend/src/styles/evaluation.css`
- Test: `frontend/src/pages/Evaluation.test.jsx`

**Interfaces:**
- Consumes: `client.evaluation()` response exactly as defined by `/api/evaluation`.
- Produces: reference page order: header → methodology notice → four KPI cards → per-area table → lower 7/5 module. No κ, F1, Merkle seal, CLI snippet, or benchmark action.

- [ ] **Step 1: Write failing Evaluation lower-module tests**

Add to `frontend/src/pages/Evaluation.test.jsx`:

```jsx
it('keeps the reference lower two-column module with real measurement scope', async () => {
  render(<Evaluation client={{ evaluation: vi.fn().mockResolvedValue(available) }} />);
  await screen.findByText('DETECTION ACCURACY');

  const left = document.querySelector('.fidelity-panel');
  const right = document.querySelector('.scope-panel');
  expect(left).toBeTruthy();
  expect(right).toBeTruthy();
  expect(left.textContent).toContain('TLS');
  expect(right.textContent).toContain('24 Nov 2026');
  expect(right.textContent).toContain('S5');
  expect(right.textContent).toContain('unmeasured');
  expect(screen.queryByText(/Cohen/)).toBeNull();
  expect(screen.queryByText(/F1/)).toBeNull();
  expect(screen.queryByText(/Merkle/)).toBeNull();
});
```

Keep the existing five Evaluation tests unchanged.

- [ ] **Step 2: Run Evaluation tests to verify they fail**

Run: `cd frontend && npm test -- src/pages/Evaluation.test.jsx`

Expected: FAIL because `.fidelity-panel` and `.scope-panel` do not exist.

- [ ] **Step 3: Rebuild Evaluation to the reference shape**

In `Evaluation.jsx`, keep the fetch/retry state machine and unavailable single-panel branch unchanged. On the available branch, render: page header with `ACCURACY REPORT`, title, and real `generated_at`; methodology notice containing the existing caveats; four `.kpi-card` readouts with full-bleed footer bands (`detections/present_total`, `false_positives/absent_total`, unmeasured count, down observations); the existing accessible `area-table`; `.unmeasured`; `.caveat`; then a `.lower-module` with `.fidelity-panel` (real `per_area` counts rendered as progress rows) and `.scope-panel` (real `generated_at`, unmeasured label lists, and the honest caveat). Do not add any score the backend does not return.

Rewrite `evaluation.css` to the reference: 1536px canvas, 36px display title, 16px gaps, full-bleed KPI footer bands, horizontally scrollable table with `min-width: 960px`, 7/5 lower split, and a tinted provenance panel in the right column. Do not render a dark terminal or CLI block; the supplied CLI snippet and seal are fabricated and have no backend counterpart. Mobile: 2×2 KPIs, per-area cards, stacked lower panels, and no invented toast.

- [ ] **Step 4: Run Evaluation tests and full frontend suite**

Run: `cd frontend && npm test -- src/pages/Evaluation.test.jsx && npm test`

Expected: all PASS; unavailable branch still renders no numbers and no table.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Evaluation.jsx frontend/src/styles/evaluation.css frontend/src/pages/Evaluation.test.jsx
git commit -m "feat(ui): rebuild evaluation report"
```

---

### Task 6: Service settings panels

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/pages/Settings.jsx`
- Modify: `frontend/src/styles/settings.css`
- Test: `frontend/src/pages/Settings.test.jsx`

**Interfaces:**
- Consumes: `client.stats()`, `session`, `apiBase`, and new `targets` prop from `App.jsx`.
- Produces: reference page order: title bar → four-cell telemetry ribbon → 2×2 panels A–D → closing evidence-only banner.

- [ ] **Step 1: Write failing Settings tests**

Change `renderSettings` in `frontend/src/pages/Settings.test.jsx` to pass a `targets` array and add:

```jsx
it('shows real authorisation provenance in the operator panel', async () => {
  render(<Settings
    client={{ stats: vi.fn().mockResolvedValue(stats) }}
    session={null}
    apiBase="http://127.0.0.1:8000"
    targets={[{
      id: 1,
      name: 'eservices-lab',
      authorization_status: 'authorized',
      authorized_by: 'A. Owner',
      authorized_at: '2026-11-12T09:30:00Z',
      authorization_basis: 'written approval',
      approved_scope: ['tls', 'network'],
      approved_ports: [8443],
    }]}
  />);

  await screen.findByText('Connection');
  expect(screen.getByText('A. Owner')).toBeTruthy();
  expect(screen.getByText('written approval')).toBeTruthy();
  expect(screen.getByText(/TLS \/ NETWORK/)).toBeTruthy();
  expect(screen.queryByText(/PID/)).toBeNull();
  expect(screen.queryByText(/GPG/)).toBeNull();
});
```

Keep the existing four Settings tests intact, including the `.footprint-tiles li` count of 4.

- [ ] **Step 2: Run Settings tests to verify they fail**

Run: `cd frontend && npm test -- src/pages/Settings.test.jsx src/App.test.jsx`

Expected: FAIL because `Settings` does not accept/read `targets` and no provenance panel exists.

- [ ] **Step 3: Rebuild Settings panels**

In `App.jsx`, pass `targets={targets}` to `<Settings>`.

In `Settings.jsx`, keep the `stats()` fetch/retry state machine and unreachable single-panel branch unchanged. Replace the current five sections with: title bar (`SERVICE STATE` / `Settings`); telemetry ribbon with four real cells from `stats.targets`, `stats.scans`, `stats.evidence`, `stats.drift_events`; panel A “Service connection” (`apiBase`, `/api/stats` reachability, `auth_mode`, session or local-research fact); panel B “Authorisation provenance” (first stored target’s `name`, `authorized_by`, `authorized_at`, `authorization_basis`, `formatScope`, `formatPorts`, or an explicit empty state); panel C “Redaction” (real enabled state plus neutral field-name legend `Authorization`, `Cookie`, `X-Api-Key` → tokenised); panel D “Data footprint” with the existing `.footprint-tiles` four items, `APP_VERSION`, and record-generated timestamp. Add a closing banner with the factual statement that only completed scans populate the console. Do not render PIDs, keys, digests, sync percentages, latency, or checksum actions.

Rewrite `settings.css` to the reference: 2×2 equal-height panels with letter badges A–D and aligned footers, tinted ribbon with dividers from `md`, 12px cards, mobile single-column stacked panels with tinted header bands, 3-up footprint tiles, and 44px touch targets.

- [ ] **Step 4: Run Settings/App tests and full frontend suite**

Run: `cd frontend && npm test -- src/pages/Settings.test.jsx src/App.test.jsx && npm test`

Expected: all PASS; `App.test.jsx` still resolves default Drift and sign-in flows.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx frontend/src/pages/Settings.jsx frontend/src/styles/settings.css frontend/src/pages/Settings.test.jsx
git commit -m "feat(ui): rebuild service settings panels"
```

---

### Task 7: Resemblance gate, live-data audit, and handoff

**Files:**
- Modify: `docs/DEMO_GUIDE.md`
- Modify: `docs/PROJECT-STATE.md`
- Modify: `docs/development-log.md`
- Create outside repo only: `/tmp/opencode/driftguard-rebuild-shots/*.png`

**Interfaces:**
- Consumes: running API on `127.0.0.1:8000` backed by `demo-driftguard.db`, Vite on `127.0.0.1:5173`, five lab targets up.
- Produces: verified side-by-side resemblance and an updated handoff.

- [ ] **Step 1: Add the verification commands to the session ledger**

Append a checklist to `docs/development-log.md` with these exact commands and expected outputs:

```bash
cd frontend && npm test
# Expected: Test Files 24 passed; Tests 93 passed (or updated count after new tests), no failures

cd frontend && npm run build
# Expected: production build succeeds

cd backend && .venv/bin/python -m unittest discover -s tests
# Expected: 145 tests pass, unchanged

if git grep -n -E 'Skipped|Regressed|comparator|synthetic|simulated' -- frontend/src docs/DEMO_GUIDE.md; then echo 'FORBIDDEN COPY FOUND'; exit 1; else echo 'forbidden-copy check clean'; fi
# Expected: prints "forbidden-copy check clean" and exits 0
```

- [ ] **Step 2: Run static verification**

Run the four commands from Step 1.

Expected: all suites green, build succeeds, no forbidden user-facing strings. If a test count changed because new tests were added, record the new count in `docs/PROJECT-STATE.md`.

- [ ] **Step 3: Run live resemblance comparison**

Start or confirm:

```bash
# Run from the repo root; the env assignments apply to the uvicorn process.
(cd backend && env DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db DRIFTGUARD_SCAN_RATE_LIMIT=60/minute .venv/bin/uvicorn driftguard.main:app --host 127.0.0.1 --port 8000)
cd frontend && npm run dev
```

Using CDP or another local browser capture tool, save screenshots to `/tmp/opencode/driftguard-rebuild-shots/` at exactly `1440x900` and `390x844` for `#/drift/1`, `#/targets`, `#/evaluation`, and `#/settings`. Compare each against the matching `stitch_driftguard_research_security_console/*/screen.png`. Record any structural divergence in `docs/PROJECT-STATE.md` with a one-line evidence-only reason; do not add invented content to close a visual gap.

- [ ] **Step 4: Audit live DOM values**

For each route, confirm the rendered DOM contains only values returned by the demo API. Specifically confirm: Drift shows `eservices-lab` with frozen stored classifications; no `api-debug` step and no present API findings; Targets shows five targets with four clean/unlabelled; Evaluation shows `7/12`, `5` misses, `0` false positives, TLS `7/7`, Network `0/5`; Settings shows `local_research`, redaction enabled, and footprint counts `5/25/7/8`. Confirm research DB counts remain `targets 1 / scans 3 / scan_evidence 0 / drift_events 0`.

- [ ] **Step 5: Update handoff docs and commit**

In `docs/DEMO_GUIDE.md`, note the new section order and the target-state pills. In `docs/PROJECT-STATE.md`, record what changed, the new test count, the resemblance result, and the decision not to add telemetry or fake provenance. In `docs/development-log.md`, log changes, reason, new knowledge, and remaining issues.

```bash
git add docs/DEMO_GUIDE.md docs/PROJECT-STATE.md docs/development-log.md
git commit -m "docs: record faithful screen rebuild verification"
git push origin main
```

Expected: `origin/main` contains all seven commits and the working tree is clean apart from intentionally untracked local-only state.
