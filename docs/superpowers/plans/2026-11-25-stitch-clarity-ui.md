# Clarity SecOps UI (Stitch export) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle all four DriftGuard frontend surfaces (Drift, Targets, Evaluation, Settings) to the approved Clarity SecOps design from the Stitch export, without changing any API contract, behaviour, or evidence-only guarantee.

**Architecture:** The React components and their data flow stay as they are; this is a presentation-layer replacement. Design tokens are swapped at the root (`tokens.css`), fonts/icons move to CDN links, the top navigation strip becomes a fixed 240px left sidebar (desktop) plus a fixed bottom tab bar (mobile), and each page's JSX/CSS is reworked to the corresponding Stitch example — with every mock-only element dropped rather than translated.

**Tech Stack:** React 19 + Vite + plain CSS (no Tailwind, no new UI dependencies). Google Fonts + Material Symbols Outlined via CDN. Vitest + Testing Library.

**Spec:**
- `stitch_driftguard_research_security_console/clarity_secops/DESIGN.md` — palette (YAML frontmatter), typography scale, layout, shapes, components.
- `stitch_driftguard_research_security_console/{driftguard_drift_console_redesigned,driftguard_targets_register_redesigned,driftguard_research_evaluation_redesigned,driftguard_system_settings_redesigned}/code.html` — desktop screens.
- `stitch_driftguard_research_security_console/{driftguard_drift_console_mobile_redesign,driftguard_targets_register_mobile_redesign,driftguard_research_evaluation_mobile_redesign,driftguard_system_settings_mobile_redesign}/code.html` — mobile screens.
- Approved decisions (session): desktop shell = fixed left sidebar; icons/fonts = CDN; mock content = strictly dropped.

## Global Constraints

- **Evidence only.** Nothing fabricated, seeded, or simulated may appear in the UI. The following example elements are **dropped, not translated**: Export Report / Download Evidence / Export Node Config / Validate Checksums / Prune Buffers buttons; Run Benchmark Calibration; Merkle root/hash/proof panels and copy buttons; CVE / CWE / mandate / exemption IDs (`#AUTH-2026-089-UG`, `CVE-2015-2808`); "days remaining" badges; fictional people, roles, environments, and authorities (Dr. M. Ssewanyana, NITA-U, "Staging Environment", "Lead Security Analyst"); daemon + latency footer; progress rings, state-fidelity bars, CLI terminal panels, redaction diff previews, benchmark tables; fabricated KPI values (`98.3%`, `Cohen's κ`, `F1`, `p < 0.001`); the `⌘K` shortcut chip; notification bell.
- **Palette authority:** `DESIGN.md` YAML frontmatter (the values the examples actually use) — `#faf8ff`, `#004ac6`, `#006e2d`, `#ac0031`, `#ba1a1a`. Amber for pending/warning comes from the DESIGN.md prose (`#b45309`), which the frontmatter does not define. Do **not** use the prose "Colors" section slate values (`#F8FAFC`/`#2563EB`).
- **Typography:** Plus Jakarta Sans (headings/display), Inter (body/labels), JetBrains Mono (identifiers/code only — never navigation or labels, per DESIGN.md).
- **Icons:** Material Symbols Outlined via Google Fonts CDN. Every icon `<span>` must carry `aria-hidden="true"` so ligature text never enters an accessible name.
- **Breakpoints:** desktop shell from `768px` up (DESIGN.md tablet 64px icon rail is an agreed YAGNI simplification — sidebar stays 240px); mobile below `768px` gets the fixed top header + fixed bottom tab bar. Drift's existing 900px grid→cards query and TargetIndex 900px select stay as they are.
- **No backend changes.** No new endpoints, no changes to `backend/`, `lab/`, or the API client. Keep the frozen taxonomy strings exactly: `BASELINE` · `NEW` · `PERSISTENT` · `FIXED` · `RECURRING` · `NO DRIFT`.
- **Keep every existing test string passing.** No test asserts class names; several assert exact text/roles. Baseline before this work: **24 files, 86 tests passing** (`cd frontend && npm test`).
- **Out of scope:** the four pre-existing review findings recorded under "Known limitations" in `docs/PROJECT-STATE.md`. Do not fix them here; do not let this work make them worse.

## Review Focus

1. **Icon ligature text polluting accessible names** — a link named "monitoring Drift" silently breaks every `getByRole('link', { name: 'Drift' })` assertion and screen-reader navigation. Owned by Task 2: `AppShell.test.jsx` asserts exact link names and `getAllByRole('navigation')` length.
2. **Two navigation landmarks at once** — rendering both the sidebar and the tab bar duplicates the "Primary" landmark and the `aria-current` page. Owned by Task 2: `AppShell.test.jsx` asserts exactly one `<nav>` in both modes.
3. **Metric cards inventing numbers** — showing counts when the latest comparable summary carries no `counts` object would be a fabricated metric. Owned by Task 3: `Drift.test.jsx` asserts the cards are absent in that case.
4. **Search/filter hiding evidence the operator needs** — a filter that silently hides a refused target, or a no-match state that looks like an empty register, is a correctness bug. Owned by Task 4: `Targets.test.jsx` asserts that the non-scannable target still appears under the default "All" filter and that a distinct no-match message (not "No targets registered.") is shown when a filter hides everything.
5. **CDN failure (offline run)** — Google Fonts/icons may not load on an offline machine. Owned by Task 1: `tokens.css` keeps `ui-sans-serif/system-ui/monospace` fallbacks in every font stack, and Task 2 keeps text labels on every nav item so navigation works without the icon font.

---

## File Structure

| File | Change |
|---|---|
| `frontend/src/styles/tokens.css` | Rewrite: Clarity palette, type, radii, shadows, layout vars |
| `frontend/src/styles/base.css` | Restyle body, `.engraved`, buttons, inputs, focus |
| `frontend/index.html` | Fonts + Material Symbols links, theme-color |
| `frontend/src/main.jsx` | Remove Chivo fontsource imports |
| `frontend/package.json`, `package-lock.json` | Remove `@fontsource-variable/chivo*` |
| `frontend/src/lib/version.js` | **Create** — single `APP_VERSION` constant |
| `frontend/src/components/Icon.jsx` | **Create** — `aria-hidden` Material Symbols span |
| `frontend/src/components/AppShell.jsx` + `.test.jsx` | Sidebar / mobile header + tab bar |
| `frontend/src/App.jsx` | `narrow` prop at 767px (replaces `navNarrow`) |
| `frontend/src/styles/shell.css` | Shell, sidebar, tab bar, state blocks, sheets; settings rules move out |
| `frontend/src/styles/settings.css` | **Create** — settings page rules (moved from `shell.css`) |
| `frontend/src/styles/index.css` | Import `settings.css` |
| `frontend/src/pages/Drift.jsx` + `Drift.test.jsx` | Subject header, metric cards, strip layout |
| `frontend/src/styles/drift.css` | Strip, metric cards, thread view, detail rail |
| `frontend/src/pages/Targets.jsx` + `Targets.test.jsx` | Stat tiles, search, filter tabs, card roster |
| `frontend/src/styles/targets.css` | Register sheet, tiles, toolbar, roster cards, stamp |
| `frontend/src/pages/Evaluation.jsx` + `Evaluation.test.jsx` | Two extra real KPI cards |
| `frontend/src/styles/evaluation.css` | KPI cards + table restyle |
| `frontend/src/pages/Settings.jsx` | Card layout, use `APP_VERSION` |
| `frontend/src/styles/responsive.css` | Rewrite media queries for the new shell |

---

### Task 1: Design foundation — tokens, fonts, global element styles

**Files:**
- Modify: `frontend/src/styles/tokens.css` (full rewrite)
- Modify: `frontend/src/styles/base.css:1-76`
- Modify: `frontend/index.html`
- Modify: `frontend/src/main.jsx:3-4`
- Modify: `frontend/package.json:14-15`

**Interfaces:**
- Consumes: nothing.
- Produces: the token names every later task uses — `--surface`, `--surface-container-lowest/low/high/highest`, `--on-surface`, `--on-surface-variant`, `--outline`, `--outline-variant`, `--primary`, `--on-primary`, `--primary-container`, `--secondary`, `--secondary-container`, `--on-secondary-container`, `--tertiary`, `--error`, `--error-container`, `--on-error-container`, `--pending`, `--surface-container`, `--space-1`…`--space-7`, `--step--1`…`--step-4`, `--row-height`, plus legacy aliases `--paper`, `--sheet`, `--muted`, `--hover`, `--ink`, `--ink-2`, `--rule`, `--signal`, `--risk`, `--verified`, `--font-ui`, `--font-display`, `--font-mono`, `--radius-sm/md/lg/full`, `--shadow-card`, `--shadow-overlay`, `--sidebar-width`, `--top-height`, `--tabbar-height`, `--content-max`.

- [ ] **Step 1: Rewrite `tokens.css`**

Replace the file with:

```css
:root {
  /* Clarity SecOps palette — authority: clarity_secops/DESIGN.md YAML frontmatter */
  --surface: #faf8ff;
  --surface-dim: #d2d9f4;
  --surface-container-lowest: #ffffff;
  --surface-container-low: #f2f3ff;
  --surface-container: #eaedff;
  --surface-container-high: #e2e7ff;
  --surface-container-highest: #dae2fd;
  --on-surface: #131b2e;
  --on-surface-variant: #434655;
  --outline: #737686;
  --outline-variant: #c3c6d7;
  --primary: #004ac6;
  --on-primary: #ffffff;
  --primary-container: #2563eb;
  --on-primary-container: #eeefff;
  --secondary: #006e2d;
  --secondary-container: #7cf994;
  --on-secondary-container: #007230;
  --tertiary: #ac0031;
  --tertiary-container: #d71142;
  --on-tertiary-container: #ffecec;
  --error: #ba1a1a;
  --error-container: #ffdad6;
  --on-error-container: #93000a;
  --inverse-surface: #283044;
  --inverse-on-surface: #eef0ff;
  --pending: #b45309; /* amber — DESIGN.md prose "Warnings / Drift" */

  /* Legacy aliases: keep untouched component rules correct while pages are reworked */
  --paper: var(--surface);
  --sheet: var(--surface-container-lowest);
  --muted: var(--surface-container-low);
  --hover: var(--surface-container);
  --ink: var(--on-surface);
  --ink-2: var(--on-surface-variant);
  --rule: var(--outline-variant);
  --signal: var(--primary);
  --risk: var(--error);
  --verified: var(--secondary);

  --font-ui: 'Inter', ui-sans-serif, system-ui, sans-serif;
  --font-display: 'Plus Jakarta Sans', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  --step--1: 0.75rem;   /* 12px label-sm */
  --step-0: 0.875rem;   /* 14px body-md */
  --step-1: 1rem;       /* 16px body-lg / headline-sm */
  --step-2: 1.5rem;     /* 24px headline-lg */
  --step-3: 1.75rem;    /* 28px */
  --step-4: 2.25rem;    /* 36px display */

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-full: 9999px;
  --shadow-card: 0 1px 2px rgba(19, 27, 46, 0.05);
  --shadow-overlay: 0 10px 25px -5px rgba(15, 23, 42, 0.04),
    0 8px 10px -6px rgba(15, 23, 42, 0.02);

  --sidebar-width: 240px;
  --top-height: 64px;
  --tabbar-height: 64px;
  --content-max: 1280px;
  --row-height: 38px;
}
```

(`--index-width` is deleted; its only use is removed in Task 3.)

- [ ] **Step 2: Restyle the global element rules in `base.css`**

Keep every selector and class name; change only values:
- `body`: `background: var(--surface); color: var(--on-surface); font-family: var(--font-ui); font-size: var(--step-0); line-height: 1.5;`
- `a`: `color: var(--primary);`
- `:focus-visible`: `outline: 2px solid var(--primary); outline-offset: 2px;`
- `.engraved`: `font-family: var(--font-ui); font-size: var(--step--1); font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; color: var(--outline);` (DESIGN.md reserves mono for identifiers).
- `.mono`: `font-family: var(--font-mono);`
- `.primary-button`: `background: var(--primary); color: var(--on-primary); border: 1px solid var(--primary); border-radius: var(--radius-sm); padding: 8px 16px; font-family: var(--font-ui); font-size: var(--step-0); font-weight: 500; letter-spacing: normal; text-transform: none;` hover → `background: #1d4ed8`.
- `.secondary-button`: `background: var(--surface-container-lowest); color: var(--on-surface); border: 1px solid var(--outline-variant); border-radius: var(--radius-sm); padding: 8px 16px; font-family: var(--font-ui); font-size: var(--step-0); font-weight: 500; letter-spacing: normal; text-transform: none;` hover → `background: var(--surface-container-low);`.
- Disabled states keep `opacity: 0.42`.
- Both button classes become `display: inline-flex; align-items: center; justify-content: center; gap: 6px;` so inline `Icon`s align with their labels.
- `.text-button` (used by Sign out and Close): `color: var(--on-surface-variant); font-family: var(--font-ui); text-decoration: none; padding: 6px 10px; border-radius: var(--radius-sm);` hover → `background: var(--surface-container-low); color: var(--on-surface);`.
- `.sheet`: `background: var(--surface-container-lowest); border: 1px solid var(--outline-variant); border-radius: var(--radius-lg);`

- [ ] **Step 3: Wire fonts and icons**

`index.html` — inside `<head>`, add (and update `theme-color` to `#faf8ff`):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@600;700&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap" rel="stylesheet" />
```

`main.jsx` — delete the two `@fontsource-variable/...` imports. `package.json` — delete both `@fontsource-variable/*` dependencies.

- [ ] **Step 4: Refresh the lockfile**

Run: `cd frontend && npm install`
Expected: lockfile updated, no errors.

- [ ] **Step 5: Verify the suite and build**

Run: `cd frontend && npm test`
Expected: **24 files, 86 tests passing** (unchanged baseline).

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html frontend/package.json frontend/package-lock.json frontend/src/main.jsx frontend/src/styles/tokens.css frontend/src/styles/base.css
git commit -m "feat(ui): adopt Clarity SecOps tokens, CDN fonts, and Material Symbols"
```

---

### Task 2: AppShell — fixed sidebar (desktop) + header and tab bar (mobile)

**Files:**
- Create: `frontend/src/lib/version.js`
- Create: `frontend/src/components/Icon.jsx`
- Modify: `frontend/src/components/AppShell.jsx`
- Modify: `frontend/src/components/AppShell.test.jsx`
- Modify: `frontend/src/App.jsx:43,124`
- Modify: `frontend/src/styles/shell.css:1-42`

**Interfaces:**
- Consumes: Task 1 tokens; `useMediaQuery` (returns `false` under jsdom, so tests render the desktop shell).
- Produces:
  - `AppShell({ route, mode, onSignOut, narrow = false, children })` — `narrow` **replaces** `navNarrow`.
  - `Icon({ name })` → `<span className="material-symbols-outlined" aria-hidden="true">{name}</span>`.
  - `APP_VERSION` (string) exported from `frontend/src/lib/version.js`.
  - CSS classes: `.sidebar`, `.side-nav`, `.brand`, `.version-chip`, `.sidebar-foot`, `.mobile-bar`, `.tab-bar`.

- [ ] **Step 1: Write the failing tests**

Rewrite `AppShell.test.jsx` to exactly three tests: a new test 1 (folds the original test 1's assertions), a new test 2 (replaces the Menu test — the Menu button no longer exists), and the untouched test 3 (local-research vs operator sign-out). Add `within` to the `@testing-library/react` import.

Both new tests must fail against the current implementation: they query `.sidebar`/`.tab-bar` structure and a version chip, none of which exist yet.

```jsx
it('renders a fixed sidebar navigation and marks the current page', () => {
  render(
    <AppShell route={{ page: 'targets', targetId: null }}
      mode={{ kind: 'operator', username: 'alice', role: 'admin' }} onSignOut={vi.fn()}>
      <p>body</p>
    </AppShell>,
  );

  expect(document.querySelector('.sidebar')).toBeTruthy();
  expect(document.querySelector('.tab-bar')).toBeNull();
  expect(screen.getAllByRole('navigation')).toHaveLength(1);
  expect(screen.getByRole('link', { name: 'Drift' })).toBeTruthy();
  expect(screen.getByRole('link', { name: 'Targets' }).getAttribute('aria-current')).toBe('page');
  expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
  expect(screen.getByText(/^v\d+\.\d+\.\d+$/)).toBeTruthy();
  expect(screen.getByText('body')).toBeTruthy();
});

it('renders a bottom tab bar at narrow widths instead of the sidebar', () => {
  render(
    <AppShell route={{ page: 'drift', targetId: 1 }} mode={{ kind: 'local' }} narrow>
      <p>body</p>
    </AppShell>,
  );

  expect(document.querySelector('.tab-bar')).toBeTruthy();
  expect(document.querySelector('.sidebar')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Menu' })).toBeNull();
  const nav = screen.getByRole('navigation', { name: 'Primary' });
  expect(screen.getAllByRole('navigation')).toHaveLength(1);
  expect(within(nav).getAllByRole('link')).toHaveLength(4);
  expect(screen.getByRole('link', { name: 'Drift' }).getAttribute('aria-current')).toBe('page');
  expect(screen.getByRole('link', { name: 'Drift' }).getAttribute('href')).toBe('#/drift');
  expect(screen.getByText('LOCAL RESEARCH')).toBeTruthy();
});
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run: `cd frontend && npm test -- src/components/AppShell.test.jsx`
Expected: FAIL — both new tests query `.sidebar`/`.tab-bar` structure and the version chip, none of which exist yet (test 2 also fails on the still-present Menu button).

- [ ] **Step 3: Implement `version.js`, `Icon.jsx`, and the new `AppShell`**

`frontend/src/lib/version.js`:

```js
export const APP_VERSION = typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : '0.0.0';
```

`frontend/src/components/Icon.jsx`:

```jsx
export function Icon({ name }) {
  return <span className="material-symbols-outlined" aria-hidden="true">{name}</span>;
}
```

`AppShell.jsx` — `DESTINATIONS` becomes `[['drift','Drift','monitoring'], ['targets','Targets','dns'], ['evaluation','Evaluation','analytics'], ['settings','Settings','tune']]`. Render **either** the sidebar (when `!narrow`) **or** the mobile chrome (when `narrow`), never both:

- Sidebar (`<aside className="sidebar">`): brand link (`#/drift`, shield icon + `DriftGuard` + `<span className="version-chip">v{APP_VERSION}</span>`), `<nav className="side-nav" aria-label="Primary" id="primary-nav">` with one link per destination (Icon + label, `aria-current={route.page === page ? 'page' : undefined}`, `href={page === 'drift' ? '#/drift' : '#/' + page}`), then `.sidebar-foot` with the mode chip (`LOCAL RESEARCH` / `OPERATOR · ${mode.username}`, prefixed by a dot span) and the `Sign out` button when `mode.kind === 'operator'`.
- Mobile (`narrow`): `<header className="mobile-bar">` with shield icon + `DriftGuard` + `<span className="version-chip">v{APP_VERSION}</span>` + the same mode chip + `Sign out` button; `<nav className="tab-bar" aria-label="Primary" id="primary-nav">` with the four destinations as icon-over-label links (Icon + label text).
- The mode chip carries no `mono` class (DESIGN.md: mono is never used for labels); every icon goes through `Icon`, which is `aria-hidden`.
- `<main className="console">{children}</main>` stays exactly as it is.

Drop the `menuOpen` state and the `Menu` button entirely.

- [ ] **Step 4: Point `App.jsx` at the new prop**

In `App.jsx` replace `const navNarrow = useMediaQuery('(max-width: 600px)');` with `const narrow = useMediaQuery('(max-width: 767px)');` and pass `narrow={narrow}` to `AppShell`.

- [ ] **Step 5: Restyle `shell.css` for the new shell**

Replace lines 1–42 (`.shell`, `.top-strip`, `.wordmark`, `.top-nav*`, `.mode*`, `.console`) with:

```css
.shell { min-height: 100vh; }

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  width: var(--sidebar-width);
  padding: var(--space-5) var(--space-4);
  background: var(--surface-container-lowest);
  border-right: 1px solid var(--outline-variant);
}
.brand { display: flex; align-items: center; gap: var(--space-2); color: var(--on-surface); text-decoration: none; font-family: var(--font-display); font-weight: 700; font-size: var(--step-1); }
.brand .material-symbols-outlined { display: grid; place-items: center; width: 36px; height: 36px; border-radius: var(--radius-md); background: var(--primary); color: var(--on-primary); font-size: 20px; }
.version-chip { margin-left: auto; padding: 2px var(--space-2); border-radius: var(--radius-sm); background: var(--surface-container-high); color: var(--on-surface-variant); font-family: var(--font-mono); font-size: var(--step--1); }
.side-nav { display: flex; flex-direction: column; gap: 2px; }
.side-nav a { display: flex; align-items: center; gap: var(--space-3); padding: 10px var(--space-3); border-radius: var(--radius-sm); color: var(--on-surface-variant); text-decoration: none; font-size: var(--step-0); font-weight: 500; }
.side-nav a:hover { background: var(--surface-container-low); color: var(--on-surface); }
.side-nav a[aria-current='page'] { background: var(--surface-container); color: var(--primary); font-weight: 600; }
.sidebar-foot { margin-top: auto; display: flex; flex-direction: column; gap: var(--space-2); padding-top: var(--space-4); border-top: 1px solid var(--outline-variant); }
.mode-chip { display: flex; align-items: center; gap: var(--space-2); font-size: var(--step--1); font-weight: 500; letter-spacing: 0.04em; color: var(--on-surface-variant); }
.mode-chip::before { content: ''; width: 8px; height: 8px; border-radius: var(--radius-full); background: var(--secondary); }

.mobile-bar, .tab-bar { display: none; }

.console { min-height: 100vh; }

@media (min-width: 768px) {
  .shell { padding-left: var(--sidebar-width); }
}

@media (max-width: 767px) {
  .sidebar { display: none; }
  .mobile-bar {
    position: fixed; inset: 0 0 auto; z-index: 30;
    display: flex; align-items: center; gap: var(--space-2);
    height: calc(var(--top-height) + env(safe-area-inset-top, 0px)); padding: 0 var(--space-4);
    padding-top: env(safe-area-inset-top, 0px);
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--outline-variant);
  }
  .mobile-bar .brand { font-size: var(--step-0); }
  .mobile-bar .mode-chip { margin-left: auto; }
  .tab-bar {
    position: fixed; inset: auto 0 0; z-index: 30;
    display: flex; justify-content: space-around;
    height: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px));
    padding-bottom: env(safe-area-inset-bottom, 0px);
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--outline-variant);
  }
  .tab-bar a { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; min-width: 56px; min-height: 44px; color: var(--on-surface-variant); text-decoration: none; font-size: var(--step--1); font-weight: 500; }
  .tab-bar a .material-symbols-outlined { font-size: 22px; }
  .tab-bar a[aria-current='page'] { color: var(--primary); font-weight: 600; }
  .console { padding-top: calc(var(--top-height) + env(safe-area-inset-top, 0px)); padding-bottom: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px)); }
}
```

Also delete the now-dead shell rules from the `@media (max-width: 600px)` block in `responsive.css` — currently lines 48–62 (`.top-strip`, `.top-nav*`, `.mode`, `.nav-menu`). Keep the block opener at line 47 and the `.subject`/`.subject-actions`/`.register-actions`/`.readout-value`/`.area-table` rules that follow it. Delete by selector after reading the file, not by assumed line number — Task 7 rewrites the whole file later.

- [ ] **Step 6: Run the tests**

Run: `cd frontend && npm test`
Expected: **24 files, 86 tests passing** (AppShell tests rewritten, count unchanged: 3 tests before, 3 after).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/version.js frontend/src/components/Icon.jsx frontend/src/components/AppShell.jsx frontend/src/components/AppShell.test.jsx frontend/src/App.jsx frontend/src/styles/shell.css frontend/src/styles/responsive.css
git commit -m "feat(ui): replace the top nav with a Clarity sidebar and mobile tab bar"
```

---

### Task 3: Drift surface — subject header, metric cards, subject strip

**Files:**
- Modify: `frontend/src/pages/Drift.jsx:98-197`
- Modify: `frontend/src/pages/Drift.test.jsx`
- Modify: `frontend/src/styles/drift.css`
- Modify: `frontend/src/styles/responsive.css` (Drift rules only)

**Interfaces:**
- Consumes: `model.latestComparable.summary.counts` (already exposed by `buildThreadModel`), `Icon`, Task 1 tokens.
- Produces: `.metric-cards` (a `<ul>` of four `<li>`), `.drift-page` as a single column, `.target-index` as a horizontal strip. Existing props and callbacks are unchanged.

- [ ] **Step 1: Write the failing metric-card tests**

Append to `Drift.test.jsx` (the existing `renderDrift` helper and fixtures stay):

```jsx
it('shows the latest comparable counts as four metric cards', async () => {
  const counts = { NEW: 1, PERSISTENT: 3, FIXED: 2, RECURRING: 1 };
  renderDrift({
    client: {
      history: vi.fn().mockResolvedValue({
        target,
        scans: [{
          scan: {
            id: 2, target_id: 1, status: 'completed',
            started_at: '2026-11-14T09:30:00Z', completed_at: '2026-11-14T09:31:00Z',
            is_baseline: false, label: null, error: null,
          },
          comparable: true,
          evidence: [{
            id: 9, scan_id: 2, fingerprint: 'eservices-lab/TLS/a', category: 'TLS',
            title: 'Legacy TLS', severity: 'High', resource: '127.0.0.1:8443',
            details: {}, observed_at: '2026-11-14T09:30:00Z',
          }],
          drift: [],
          summary: { state: 'CHANGED', counts },
        }],
        fingerprints: {
          'eservices-lab/TLS/a': {
            title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: '127.0.0.1:8443',
          },
        },
      }),
      runScan: vi.fn(),
    },
  });

  await screen.findByRole('heading', { name: 'eservices-lab' });
  expect(screen.getByText('New findings').closest('li').textContent).toContain('1');
  expect(screen.getByText('Persistent findings').closest('li').textContent).toContain('3');
  expect(screen.getByText('Fixed findings').closest('li').textContent).toContain('2');
  expect(screen.getByText('Recurring findings').closest('li').textContent).toContain('1');
});

it('omits the metric cards when the latest summary carries no counts', async () => {
  renderDrift({
    client: {
      history: vi.fn().mockResolvedValue({
        target,
        scans: [{
          scan: {
            id: 2, target_id: 1, status: 'completed',
            started_at: '2026-11-14T09:30:00Z', completed_at: '2026-11-14T09:31:00Z',
            is_baseline: false, label: null, error: null,
          },
          comparable: true, evidence: [], drift: [],
          summary: { state: 'CHANGED' },
        }],
        fingerprints: {},
      }),
      runScan: vi.fn(),
    },
  });

  await screen.findByRole('heading', { name: 'eservices-lab' });
  expect(screen.queryByText('New findings')).toBeNull();
  expect(screen.queryByText('Persistent findings')).toBeNull();
});
```

- [ ] **Step 2: Run them to confirm they fail**

Run: `cd frontend && npm test -- src/pages/Drift.test.jsx`
Expected: the first test FAILS (`getByText('New findings')` is null — the element is not rendered). The second test is a regression pin: it passes before and after the change, which is expected — keep it.

- [ ] **Step 3: Implement the metric cards in `Drift.jsx`**

Inside the `model?.hasComparable` block, immediately after `<DifferenceLine model={model} />` (before `<PendingScanPanel>`), add:

```jsx
{model.latestComparable?.summary?.counts && (
  <ul className="metric-cards" aria-label="Counts in the latest comparable scan">
    {[
      ['NEW', 'New findings', 'metric-new', 'add'],
      ['PERSISTENT', 'Persistent findings', 'metric-persistent', 'keep'],
      ['FIXED', 'Fixed findings', 'metric-fixed', 'check_circle'],
      ['RECURRING', 'Recurring findings', 'metric-recurring', 'repeat'],
    ].map(([key, label, cls, icon]) => (
      <li key={key} className={`metric-card ${cls}`}>
        <span className="metric-icon"><Icon name={icon} /></span>
        <p className="metric-label">{label}</p>
        <p className="metric-value">{model.latestComparable.summary.counts[key] ?? 0}</p>
        <p className="metric-note">in the latest comparable scan</p>
      </li>
    ))}
  </ul>
)}
```

Add `import { Icon } from '../components/Icon';` to the page imports.

No other JSX on this page changes except class restyling of the subject header: keep `<h1>{target.name}</h1>`, the `.subject-meta` address line, `Refresh` and `Run scan` buttons (add `<Icon name="refresh" />` and `<Icon name="play_arrow" />` before their labels), `<AuthorisationStamp>`, refusal/status lines, `DifferenceLine`, `PendingScanPanel`, `ThreadGrid`/`ThreadCards`, `EvidenceDetail`, and the detail prompt — all exactly as they are today.

- [ ] **Step 4: Run the Drift tests**

Run: `cd frontend && npm test -- src/pages/Drift.test.jsx`
Expected: PASS — 6 tests (4 existing + 2 new).

- [ ] **Step 5: Restyle `drift.css` (layout, strip, cards, thread view)**

Concrete changes (selectors stay, values change):
- `.drift-page`: `display: block; min-height: auto;` (drop `grid-template-columns: var(--index-width) …` and the `100vh - top-height` calc).
- `.target-index`: becomes a horizontal strip — `display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3) var(--space-6); border-bottom: 1px solid var(--rule); background: var(--surface-container-lowest); overflow-x: auto;` with `.target-index ul { display: flex; gap: var(--space-2); margin: 0; }` and each `.target-index a` as a chip: `display: flex; gap: var(--space-2); white-space: nowrap; padding: var(--space-2) var(--space-3); border: 1px solid var(--rule); border-radius: var(--radius-full);` selected chip → `background: var(--surface-container); border-color: var(--primary); color: var(--primary);`.
- `.metric-cards`: `display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-5); margin: var(--space-5) 0; list-style: none; padding: 0;`
- `.metric-card`: `padding: var(--space-5); background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card);`
- `.metric-icon`: `display: grid; place-items: center; width: 36px; height: 36px; border-radius: var(--radius-sm); background: var(--surface-container); color: var(--primary); margin-bottom: var(--space-3);` with `.metric-recurring .metric-icon { background: rgba(255, 255, 255, 0.65); color: var(--on-error-container); }` and `.metric-fixed .metric-icon { color: var(--secondary); }`.
- `.metric-label` becomes a chip with the DESIGN.md 6px dot: `display: inline-flex; align-items: center; gap: 6px; padding: 2px var(--space-2); border-radius: var(--radius-full); background: var(--surface-container); color: var(--on-surface-variant); font-size: var(--step--1); font-weight: 500;` and `.metric-label::before { content: ''; width: 6px; height: 6px; border-radius: var(--radius-full); background: currentColor; }`
- `.metric-value`: `font-family: var(--font-display); font-size: var(--step-4); font-weight: 700; letter-spacing: -0.025em; font-variant-numeric: tabular-nums; margin-top: var(--space-2);` `.metric-note`: `font-size: var(--step--1); color: var(--outline);`
- Card accents: `.metric-new .metric-value { color: var(--primary); }`, `.metric-persistent .metric-value { color: var(--on-surface-variant); }`, `.metric-fixed .metric-value { color: var(--secondary); }`, `.metric-recurring { background: var(--error-container); border-color: transparent; }` with `.metric-recurring .metric-value, .metric-recurring .metric-label { color: var(--on-error-container); }`.
- `.drift-subject`: `padding: var(--space-6) var(--space-5); max-width: var(--content-max); margin: 0 auto;`
- `.subject`: `border-bottom: 0; padding-bottom: 0;` `.subject h1 { font-family: var(--font-display); font-size: var(--step-2); letter-spacing: -0.02em; }`
- Thread view: `.thread-grid { font-variant-numeric: tabular-nums; }`, `.thread-grid th, .thread-grid td { border-color: var(--rule); }`, header row `.thread-group th` → `font-family: var(--font-ui); text-transform: uppercase; letter-spacing: 0.04em; color: var(--on-surface-variant); border-bottom-color: var(--outline-variant);` (mono is reserved for identifiers), `.axis-scan.kind-baseline, .thread-row:hover/.is-selected` → `background: var(--hover);`, `.mark-new/.mark-recurring` → `background: var(--primary);`, `.mark-fixed` → `border-color: var(--secondary); background: var(--surface-container-lowest);`, `.difference-changed { color: var(--primary); }`, `.difference-no-drift { color: var(--secondary); }`.
- `.detail-rail dt` (and any other label-role `dt`): `font-family: var(--font-ui); text-transform: uppercase; letter-spacing: 0.04em; color: var(--outline);` — verify against the actual selectors in `drift.css` while editing.
- Card treatment (DESIGN.md cards): the element wrapping `.thread-grid` (find its selector in `drift.css`/`ThreadGrid.jsx`) and `.detail-rail` get `background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card);` instead of bare top rules.
- `.detail-rail` / `.detail-prompt`: `border-top: 1px solid var(--rule);` and `border-top-color: var(--rule)` (drop the 2px ink rules).
- Responsive: no edits here — Task 7 rewrites `responsive.css` and owns every media query (`.metric-cards` stays 2-across down to phone widths, matching the mobile examples).

- [ ] **Step 6: Run the full suite**

Run: `cd frontend && npm test`
Expected: **24 files, 88 tests passing**.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Drift.jsx frontend/src/pages/Drift.test.jsx frontend/src/styles/drift.css frontend/src/styles/responsive.css
git commit -m "feat(ui): restyle the drift console with Clarity metric cards and subject strip"
```

---

### Task 4: Targets surface — stat tiles, search, filter tabs, card roster

**Files:**
- Modify: `frontend/src/pages/Targets.jsx`
- Modify: `frontend/src/pages/Targets.test.jsx`
- Modify: `frontend/src/styles/targets.css`

**Interfaces:**
- Consumes: `Icon`, Task 1 tokens. Existing props (`client`, `targets`, `loading`, `error`, `onReload`, `onOpen`, `onScanQueued`, `onRegistered`, `session`) and all callbacks are unchanged.
- Produces: `.stat-tiles`, `.roster-toolbar`, `.filter-tabs`, `.filter-count`, card-based `.roster`. Filter state is local to the component: `query` (string), `filter` (`'all' | 'authorized' | 'pending' | 'refused'`).

- [ ] **Step 1: Write the failing tests**

Add a second fixture after `target` in `Targets.test.jsx`:

```jsx
const civic = {
  ...target,
  id: 2,
  name: 'civic',
  address: 'https://127.0.0.1:8445',
  authorization_status: 'pending',
  authorized_by: null,
  authorized_at: null,
  authorization_basis: null,
  approved_scope: [],
  approved_ports: [],
  last_scan: null,
  scannable: false,
  refusal_reasons: ['target must be explicitly authorized'],
};
```

Append three tests:

```jsx
it('filters the roster by search text', async () => {
  renderPage({ targets: [target, civic] });
  await userEvent.setup().type(screen.getByLabelText('Search targets'), 'eservices');
  expect(screen.getByText('eservices-lab')).toBeTruthy();
  expect(screen.queryByText('civic')).toBeNull();
});

it('filters by authorisation status and shows real counts', async () => {
  renderPage({ targets: [target, civic] });
  // the non-scannable ("refused") target is visible under the default All filter
  expect(screen.getByText('civic')).toBeTruthy();
  const user = userEvent.setup();
  const pending = screen.getByRole('button', { name: /Pending/ });
  expect(pending.textContent).toContain('1');
  await user.click(pending);

  expect(pending.getAttribute('aria-pressed')).toBe('true');
  expect(screen.queryByText('eservices-lab')).toBeNull();
  expect(screen.getByText('civic')).toBeTruthy();
});

it('distinguishes a filtered-empty register from an empty register', async () => {
  renderPage({ targets: [target] });
  await userEvent.setup().click(screen.getByRole('button', { name: /Refused/ }));
  expect(screen.queryByText('eservices-lab')).toBeNull();
  expect(screen.queryByText('No targets registered.')).toBeNull();
  expect(screen.getByRole('status').textContent).toContain('No targets match');
});
```

Note: assertions about an absent element must use `queryByText(...)` — `getByText` throws instead of failing the assertion.

- [ ] **Step 2: Run them to confirm they fail**

Run: `cd frontend && npm test -- src/pages/Targets.test.jsx`
Expected: FAIL — `getByLabelText('Search targets')` is null.

- [ ] **Step 3: Implement search, filters, and stat tiles in `Targets.jsx`**

Add state and derived data above `register`:

```jsx
const [query, setQuery] = useState('');
const [filter, setFilter] = useState('all');

const matches = {
  all: () => true,
  authorized: (t) => t.authorization_status === 'authorized',
  pending: (t) => t.authorization_status !== 'authorized',
  refused: (t) => !t.scannable,
};
const countFor = (key) => targets.filter(matches[key]).length;
const needle = query.trim().toLowerCase();
const visible = targets.filter((target) => matches[filter](target)
  && (!needle || [target.name, target.address, target.target_type,
    formatScope(target.approved_scope), formatPorts(target.approved_ports)]
    .join(' ').toLowerCase().includes(needle)));
```

Render, between `<header className="page-head">` and the roster:
- `<ul className="stat-tiles">` with three `<li>` tiles: **Registered** `targets.length`, **Authorized** `countFor('authorized')`, **Refused** `countFor('refused')` — each as `<span className="tile-icon"><Icon name="…" /></span><p className="tile-label">…</p><p className="tile-value">…</p>` (icons: `list_alt`, `verified_user`, `block`). (All three are derived from real records; no rates, no sweep timers.)
- `<div className="roster-toolbar">` containing `<div className="search-field"><Icon name="search" /><input type="search" aria-label="Search targets" placeholder="Search by name, address, or scope" value={query} onChange={(e) => setQuery(e.target.value)} /></div>` and `<div className="filter-tabs" role="group" aria-label="Filter targets">` with four buttons — `All`, `Authorized`, `Pending`, `Refused` — each rendering `{label} <span className="filter-count">{countFor(key)}</span>`, carrying `aria-pressed={filter === key}` and `onClick={() => setFilter(key)}`. Add `import { Icon } from '../components/Icon';`.
- Button icons (labels stay, so accessible names are unchanged): `Register target` → `<Icon name="add" />`, `Open` → `<Icon name="open_in_new" />`, `Run scan` → `<Icon name="play_arrow" />`.

Then replace the roster condition: `targets.length === 0` keeps the existing `EmptySheet` unchanged; otherwise render `<ul className="roster">` over `visible`, and when `visible.length === 0` render `<p role="status">No targets match this filter or search.</p>` instead of the list.

Each roster `<li>` keeps its existing children and text exactly (identity button + address, `<AuthorisationStamp compact>`, SCOPE field, LAST SCAN field, `Open` / `Run scan` buttons, refusal `<p className="refusal">`) — the only markup change is the class: `className={`roster-row${target.scannable ? '' : ' is-refused'}`}` for the left accent. Do **not** add a separate status chip: `AuthorisationStamp` already renders the `AUTHORIZED` / `PENDING` state text, and a second label with the same words would be ambiguous (the stamp's state text is restyled as the chip in CSS instead).

- [ ] **Step 4: Run the Targets tests**

Run: `cd frontend && npm test -- src/pages/Targets.test.jsx`
Expected: PASS — 7 tests (4 existing + 3 new).

- [ ] **Step 5: Restyle `targets.css`**

- `.targets-page`: `max-width: var(--content-max); margin: 0 auto; padding: var(--space-6) var(--space-5);`
- `.page-head`: `border-bottom: 0;` `.page-head h1 { font-family: var(--font-display); font-size: var(--step-2); letter-spacing: -0.02em; }` `.lede { color: var(--on-surface-variant); }`
- `.stat-tiles`: `display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-5); margin: var(--space-5) 0; list-style: none; padding: 0;` `.stat-tiles li { padding: var(--space-5); background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); }` `.tile-label { font-size: var(--step--1); font-weight: 500; color: var(--on-surface-variant); margin: 0; }` `.tile-value { font-family: var(--font-display); font-size: var(--step-3); font-weight: 700; margin: var(--space-2) 0 0; }`
- `.roster-toolbar`: `display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; justify-content: space-between; margin-bottom: var(--space-5);` input: `padding: 10px var(--space-4); border: 1px solid var(--outline-variant); border-radius: var(--radius-sm); background: var(--muted); min-width: 280px;` focus → `border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0, 74, 198, 0.12); outline: none;`
- `.filter-tabs`: `display: flex; gap: var(--space-1); padding: 4px; background: var(--muted); border-radius: var(--radius-sm);` `.filter-tabs button { border: 0; background: none; padding: 6px var(--space-3); border-radius: var(--radius-sm); font-size: var(--step-0); font-weight: 500; color: var(--on-surface-variant); display: flex; gap: var(--space-2); align-items: center; }` `[aria-pressed='true'] { background: var(--surface-container-lowest); color: var(--on-surface); font-weight: 600; box-shadow: var(--shadow-card); }` `.filter-count { font-family: var(--font-mono); font-size: 11px; padding: 0 6px; border-radius: var(--radius-full); background: var(--surface-container-high); color: var(--on-surface-variant); }`
- `.roster`: `border-top: 0; display: flex; flex-direction: column; gap: var(--space-5);` `.roster-row`: `display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr) minmax(0, 0.8fr) minmax(0, 1.1fr) auto; gap: var(--space-4); align-items: start; padding: var(--space-5); background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card);` — five columns for the five existing children (identity, stamp, scope, last scan, actions); `.roster-actions { justify-items: end; }`; `.roster-row.is-refused { border-left: 4px solid var(--tertiary); }`
- `.roster-name`: `font-family: var(--font-display); font-size: var(--step-1); font-weight: 600;`
- `.stamp-state` (the stamp's own state text becomes the status chip — no separate chip element): `display: inline-flex; align-items: center; gap: 6px; padding: 2px var(--space-2); border-radius: var(--radius-full); font-size: var(--step--1); font-weight: 600; background: var(--secondary-container); color: var(--on-secondary-container);` with `.stamp-state::before { content: ''; width: 6px; height: 6px; border-radius: var(--radius-full); background: currentColor; }` and `.stamp.is-pending .stamp-state { background: #fffbeb; color: var(--pending); }`
- `.refusal`: `color: var(--pending);` `.stamp`: `background: var(--muted); border: 1px solid var(--rule); border-radius: var(--radius-md);` `.stamp.is-pending { border-color: var(--pending); background: #fffbeb; }`
- `.register-sheet`: `border-top: 0; border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-overlay);` inputs/selects: `border: 1px solid var(--outline-variant); border-radius: var(--radius-sm); background: var(--muted);`
- Register sheet becomes a right-anchored slide-over (DESIGN.md Components → Slide-over): in `RegisterTargetSheet.jsx` add `is-drawer` to the `.sheet-backdrop` div; then `.sheet-backdrop.is-drawer { padding: 0; place-items: stretch; justify-content: end; }` and `.register-sheet { height: 100%; max-height: 100%; width: min(560px, 100%); border-radius: 0; overflow-y: auto; }`. The centered `.signin-sheet` keeps the plain backdrop.
- Responsive: no edits here — Task 7 rewrites `responsive.css` (stat tiles stay 3-across with a small gap on phones per the mobile example; the roster keeps its existing single-column rule at ≤900px).

- [ ] **Step 6: Run the full suite**

Run: `cd frontend && npm test`
Expected: **24 files, 91 tests passing**.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Targets.jsx frontend/src/pages/Targets.test.jsx frontend/src/styles/targets.css frontend/src/styles/responsive.css
git commit -m "feat(ui): restyle the target register with tiles, search, and filter tabs"
```

---

### Task 5: Evaluation surface — four real KPI cards + restyled table

**Files:**
- Modify: `frontend/src/pages/Evaluation.jsx`
- Modify: `frontend/src/pages/Evaluation.test.jsx`
- Modify: `frontend/src/styles/evaluation.css`

**Interfaces:**
- Consumes: `client.evaluation()` response shape (`overall.{detection_accuracy, detections, present_total, false_positive_rate, false_positives, absent_total, unmeasured_scans, down_observations}`, `per_area`, `unmeasured`, `generated_at`, `available`, `reason`, `duplicates`).
- Produces: `Readout({ label, value, numerator, denominator, icon })` where the fraction line renders only when `denominator != null` and `icon` is an optional Material Symbols name; four `<li>` KPI cards; the area table gains `data-label` attributes (text unchanged).

- [ ] **Step 1: Write the failing test**

Append to `Evaluation.test.jsx`:

```jsx
it('shows unmeasured scans and down observations as KPI cards', async () => {
  const client = { evaluation: vi.fn().mockResolvedValue(available) };
  render(<Evaluation client={client} />);

  await screen.findByText('DETECTION ACCURACY');
  expect(screen.getByText('UNMEASURED SCANS').closest('li').textContent).toContain('4');
  expect(screen.getByText('DOWN OBSERVATIONS').closest('li').textContent).toContain('2');
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- src/pages/Evaluation.test.jsx`
Expected: FAIL — `getByText('UNMEASURED SCANS')` is null.

- [ ] **Step 3: Implement the four KPI cards**

Update `Readout` to take an optional `icon`, drop `mono` from the value (DESIGN.md reserves mono for identifiers), and render the fraction only when `denominator != null`:

```jsx
function Readout({ label, value, numerator, denominator, icon }) {
  return (
    <div className="readout">
      {icon && <span className="readout-icon"><Icon name={icon} /></span>}
      <p className="engraved">{label}</p>
      <p className="readout-value">{value}</p>
      {denominator != null && <p className="readout-fraction mono">{numerator}/{denominator}</p>}
    </div>
  );
}
```

Add `import { Icon } from '../components/Icon';`. Wrap the four readouts in `<ul className="readouts" aria-label="Key metrics">` with each `Readout` inside an `<li>` (change `.readouts` from a `div` of `div`s to a `ul` of `li`s — `Readout` itself stays a `div`). Give the existing two readouts the icons `accuracy` and `gpp_maybe`, and add after the false-positive readout:

```jsx
<Readout
  label="UNMEASURED SCANS"
  value={String(data.overall.unmeasured_scans ?? 0)}
  icon="help_outline"
/>
<Readout
  label="DOWN OBSERVATIONS"
  value={String(data.overall.down_observations ?? 0)}
  icon="cloud_off"
/>
```

For the mobile card layout, add `data-label` to every area-table `<td>` in both `tbody` and `tfoot`: `<td key={key} data-label={label}>{String(...)}</td>` (the `label` is already in the `COLUMNS` tuple) — Task 7 turns these into labelled card rows at ≤767px.

Everything else on the page (header copy, `available`/error states, `COLUMNS`, area-table text, unmeasured-labels block, caveats) keeps its existing text exactly.

- [ ] **Step 4: Run the Evaluation tests**

Run: `cd frontend && npm test -- src/pages/Evaluation.test.jsx`
Expected: PASS — 5 tests (4 existing + 1 new).

- [ ] **Step 5: Restyle `evaluation.css`**

- `.evaluation-page`: `max-width: var(--content-max); margin: 0 auto; padding: var(--space-6) var(--space-5);`
- `.readouts`: `display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-5); margin: var(--space-5) 0; list-style: none; padding: 0;` `.readouts li { list-style: none; }`
- `.readout`: `padding: var(--space-5); background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); border-top: 0;` (replace the `border-top: 2px solid var(--ink)` rule)
- `.readout .engraved` → keep label styling from `base.css`; `.readout-value { font-family: var(--font-display); font-size: var(--step-4); font-weight: 700; letter-spacing: -0.025em; font-variant-numeric: tabular-nums; margin: var(--space-3) 0 0; }` `.readout-fraction { color: var(--on-surface-variant); margin: var(--space-1) 0 0; font-family: var(--font-mono); }`
- `.readout-icon`: `display: grid; place-items: center; width: 36px; height: 36px; border-radius: var(--radius-sm); background: var(--surface-container); color: var(--primary); margin-bottom: var(--space-3);`
- `.area-table`: `background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); overflow: hidden; font-variant-numeric: tabular-nums;` `th, td { border-bottom-color: var(--rule); padding: var(--space-3); }` `thead th { background: var(--muted); color: var(--on-surface-variant); border-bottom: 1px solid var(--outline-variant); }` `tfoot td, tfoot th { border-top: 1px solid var(--outline-variant); background: var(--muted); }`
- `.area-table caption`: `font-family: var(--font-ui); text-transform: uppercase; letter-spacing: 0.04em; font-size: var(--step--1); color: var(--outline); text-align: left; padding-bottom: var(--space-2);` (mono is reserved for identifiers)
- `.caveat`: `background: var(--muted); border-left: 3px solid var(--primary); border-radius: var(--radius-sm); color: var(--on-surface-variant);`
- `.unavailable`: `border-top: 0; border: 1px solid var(--pending); background: #fffbeb; border-radius: var(--radius-lg);`
- Responsive: no edits here — Task 7 rewrites `responsive.css` (`.readouts` stays 2-across down to phone widths, matching the mobile examples).

- [ ] **Step 6: Run the full suite**

Run: `cd frontend && npm test`
Expected: **24 files, 92 tests passing**.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/Evaluation.jsx frontend/src/pages/Evaluation.test.jsx frontend/src/styles/evaluation.css frontend/src/styles/responsive.css
git commit -m "feat(ui): restyle evaluation with four real KPI cards"
```

---

### Task 6: Settings surface — card layout + `settings.css` split

**Files:**
- Create: `frontend/src/styles/settings.css`
- Modify: `frontend/src/styles/index.css`
- Modify: `frontend/src/styles/shell.css:95-101` (delete the `.settings-*` rules)
- Modify: `frontend/src/pages/Settings.jsx`

**Interfaces:**
- Consumes: `APP_VERSION` from `../lib/version`, `client.stats()` shape.
- Produces: `.settings-grid` wrapping the existing `Section` component (unchanged signature, `h2` titles unchanged).

- [ ] **Step 1: Write the failing test**

Append to `Settings.test.jsx`:

```jsx
it('renders the footprint as four count tiles and the real UI version', async () => {
  const client = { stats: vi.fn().mockResolvedValue(stats) };
  render(<Settings client={client} session={null} apiBase="http://127.0.0.1:8000" />);

  await screen.findByText('Connection');
  expect(document.querySelectorAll('.footprint-tiles li')).toHaveLength(4);
  expect(screen.getByText('scans')).toBeTruthy();
  expect(screen.getByText('9')).toBeTruthy();
  expect(screen.getByText('evidence')).toBeTruthy();
  expect(screen.getByText('142')).toBeTruthy();
  expect(screen.getByText(/^driftguard-ui \d+\.\d+\.\d+$/)).toBeTruthy();
});
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- src/pages/Settings.test.jsx`
Expected: FAIL — `.footprint-tiles li` does not exist yet (the footprint is still a `dl`, so `querySelectorAll` returns 0). The version regex already passes today; it is a regression pin.

- [ ] **Step 3: Implement the settings layout**

- In `Settings.jsx`: import `APP_VERSION` from `../lib/version`, delete the local `version` computation, use `driftguard-ui {APP_VERSION}` in the Version section, and wrap the five `Section`s in `<div className="settings-grid">`. Convert the Data-footprint `dl` into count tiles: `<ul className="footprint-tiles">{FOOTPRINT.map(([key, label]) => <li key={key}><p className="tile-label">{label}</p><p className="tile-value mono">{String(stats[key] ?? 0)}</p></li>)}</ul>` — labels and values stay exactly as they are (the existing tests query them by text). No other text changes anywhere.
- Create `frontend/src/styles/settings.css` containing the `.settings-page` / `.settings-section` / `.settings-list` rules moved verbatim from `shell.css:95-101`, restyled as follows, plus the imports update in `index.css` (`@import './settings.css';` after `./evaluation.css`).
- Delete lines 95–101 of `shell.css`.

Settings rules (new file):

```css
.settings-page { max-width: var(--content-max); margin: 0 auto; padding: var(--space-6) var(--space-5); }
.settings-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-5); margin-top: var(--space-5); }
.settings-section { padding: var(--space-5); background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); }
.settings-section h2 { font-family: var(--font-display); font-size: var(--step-1); font-weight: 600; margin: 0 0 var(--space-3); }
.settings-list { display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: var(--space-2) var(--space-4); margin: 0; }
.settings-list dt { font-size: var(--step--1); font-weight: 500; letter-spacing: 0.04em; text-transform: uppercase; color: var(--outline); }
.settings-list dd { margin: 0; color: var(--on-surface); }
.footprint-tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3); margin: 0; padding: 0; list-style: none; }
.footprint-tiles li { padding: var(--space-3) var(--space-4); background: var(--muted); border: 1px solid var(--rule); border-radius: var(--radius-md); }
.footprint-tiles .tile-label { font-size: var(--step--1); font-weight: 500; color: var(--on-surface-variant); margin: 0; }
.footprint-tiles .tile-value { font-family: var(--font-display); font-size: var(--step-2); font-weight: 700; font-variant-numeric: tabular-nums; margin: var(--space-1) 0 0; }
```

The `.page-head` rules live once in `targets.css` (Task 4 restyles them; the selectors are unscoped, so Settings and Evaluation inherit them) — do not duplicate them here.

Responsive: no edits here — Task 7 rewrites `responsive.css` (`.settings-grid` collapses to one column at ≤900px).

- [ ] **Step 4: Run the Settings tests**

Run: `cd frontend && npm test -- src/pages/Settings.test.jsx`
Expected: PASS — 4 tests (3 existing + 1 new).

- [ ] **Step 5: Run the full suite and build**

Run: `cd frontend && npm test` → **24 files, 93 tests passing**.
Run: `cd frontend && npm run build` → succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/styles/settings.css frontend/src/styles/index.css frontend/src/styles/shell.css frontend/src/styles/targets.css frontend/src/styles/responsive.css frontend/src/pages/Settings.jsx frontend/src/pages/Settings.test.jsx
git commit -m "feat(ui): restyle settings into Clarity cards and split settings.css"
```

---

### Task 7: Shared component surfaces + responsive rewrite

**Files:**
- Modify: `frontend/src/styles/shell.css` (state blocks, sign-in sheet, pending panel)
- Modify: `frontend/src/styles/responsive.css` (full rewrite of the media queries)
- Modify: `frontend/src/components/StateBlocks.jsx` (markup only where noted)

**Interfaces:**
- Consumes: Task 1 tokens.
- Produces: consistent card treatment for `.sheet-loading`, `.sheet-error`, `.empty-sheet`, `.pending-panel`, `.signin-sheet`, `.register-sheet`, `.fatal`.

- [ ] **Step 1: Restyle the shared state blocks in `shell.css`**

- `.sheet-loading, .sheet-error, .empty-sheet`: `max-width: 720px; margin: var(--space-7) auto; padding: var(--space-6); background: var(--surface-container-lowest); border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-card);` (replace the `border-top: 2px solid var(--ink)` rule).
- `.sheet-error { border: 1px solid var(--error); background: var(--error-container); color: var(--on-error-container); }` and its `.engraved` child colour → `var(--on-error-container)`.
- `.skeleton-row { background: var(--surface-container-high); }`
- `.pending-panel { border-left: 3px solid var(--pending); background: #fffbeb; border-radius: var(--radius-sm); }`
- `.sheet-backdrop { background: rgba(19, 27, 46, 0.4); }`
- `.signin-sheet`: `border-top: 0; border: 1px solid var(--rule); border-radius: var(--radius-lg); box-shadow: var(--shadow-overlay);` inputs → `border: 1px solid var(--outline-variant); border-radius: var(--radius-sm); background: var(--muted);`; `label` elements → `font-family: var(--font-ui); font-size: var(--step-0);` (mono is reserved for identifiers).
- `.fatal { border-top: 0; border: 1px solid var(--error); border-radius: var(--radius-lg); }`
- `.form-error { color: var(--error); }`

- [ ] **Step 2: Rewrite `responsive.css`**

The dead `.top-strip`/`.top-nav`/`.mode`/`.nav-menu` rules were removed from the 600px block in Task 2 — do not reintroduce them. The file should contain exactly four blocks:

1. `@media (max-width: 900px)` — Drift: `.drift-page` single column is already the default; keep `.target-select-label` select styling, `.roster-row`/`.detail-rail` single column, the `ThreadCards` card list rules, `.metric-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }`, `.readouts { grid-template-columns: repeat(2, minmax(0, 1fr)); }`, `.settings-grid { grid-template-columns: minmax(0, 1fr); }`.
2. `@media (max-width: 767px)` — mobile: `.drift-subject` and the three page wrappers (`.targets-page`, `.evaluation-page`, `.settings-page`) get `padding-left/right: var(--space-4)` (16px mobile gutters per the mobile examples), `.stat-tiles { gap: var(--space-2); }` (stays 3-across), `.roster-actions { justify-items: stretch; }`, `.page-head { flex-direction: column; align-items: stretch; }`, `.register-actions { flex-direction: column; }`, and the **area table becomes card modules** (DESIGN.md: complex tables re-render as cards on mobile):

   ```css
   .area-table, .area-table tbody, .area-table tfoot { display: block; }
   .area-table thead { display: none; }
   .area-table tr { display: block; margin-bottom: var(--space-3); padding: var(--space-3); border: 1px solid var(--rule); border-radius: var(--radius-md); background: var(--surface-container-lowest); }
   .area-table th, .area-table td { display: flex; justify-content: space-between; gap: var(--space-4); border: 0; padding: var(--space-1) 0; text-align: left; }
   .area-table td::before { content: attr(data-label); color: var(--on-surface-variant); font-size: var(--step--1); }
   ```

3. `@media (max-width: 600px)` — `.subject { flex-direction: column; }`, `.subject-actions { width: 100%; }`, `.settings-list { grid-template-columns: minmax(0, 1fr); }`, `.page-head h1, .subject h1 { font-size: var(--step-3); }` (28px display-mobile). Do **not** collapse `.readouts`/`.metric-cards` to one column — the mobile examples keep them 2-across (2×2).
4. The existing `prefers-reduced-motion` block and `thread-draw` keyframes — unchanged.

- [ ] **Step 3: Verify no orphaned selectors remain**

Run from inside `frontend/`: `grep -rn "top-strip\|top-nav\|nav-menu\|navNarrow\|--index-width" src`
Expected: no output — grep exits 1 when it finds nothing, which is the passing condition here.

- [ ] **Step 4: Run the full suite and build**

Run: `cd frontend && npm test` → **24 files, 93 tests passing**.
Run: `cd frontend && npm run build` → succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles/shell.css frontend/src/styles/responsive.css
git commit -m "feat(ui): unify state-block surfaces and rewrite responsive rules"
```

---

### Task 8: Verification — suite, build, backend, runtime screenshots

**Files:**
- Create: screenshots under `/tmp/opencode/driftguard-ui-shots/` (not committed)

**Interfaces:**
- Consumes: everything above.
- Produces: visual evidence for approve/reject.

- [ ] **Step 1: Run both suites**

```bash
cd frontend && npm test && npm run build   # expect 24 files, 93 tests passing, then a successful build
cd backend && .venv/bin/python -m unittest discover -s tests   # expect 143 passing, untouched
```

Run these as two separate shell invocations, each starting from the repo root — do not chain `cd` commands in one persistent shell.

- [ ] **Step 2: Start the services**

Start each as its own background shell invocation from the repo root:

```bash
cd backend && .venv/bin/uvicorn driftguard.main:app --host 127.0.0.1 --port 8000   # background
cd frontend && npm run dev                                                          # background
```

- [ ] **Step 3: Register one real target through the UI**

Open `http://127.0.0.1:5173/#/targets`, use the real **Register target** form to add `eservices-lab` (`https://127.0.0.1:8443`, scope TLS + Network, port 8443, authorised). This is ordinary data entry through the product's own flow — no seeded or fabricated findings.

- [ ] **Step 4: Capture screenshots**

```bash
mkdir -p /tmp/opencode/driftguard-ui-shots
for route in targets drift evaluation settings; do
  google-chrome --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 \
    --window-size=1440,900 \
    --screenshot=/tmp/opencode/driftguard-ui-shots/${route}-desktop.png \
    "http://127.0.0.1:5173/#/${route}"
  google-chrome --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 \
    --window-size=390,844 \
    --screenshot=/tmp/opencode/driftguard-ui-shots/${route}-mobile.png \
    "http://127.0.0.1:5173/#/${route}"
done
ls -la /tmp/opencode/driftguard-ui-shots/
```

Expected: 8 PNGs. With a freshly registered target and no scans yet, Drift shows the subject header, the authorisation stamp, the subject strip, and the "No observations yet." empty state — the metric cards and thread view appear only after a completed comparable scan, so their absence in this capture is the honest state.

- [ ] **Step 5: Optional stretch — real observations for the Drift view**

If Docker is available, bring up one lab target so the thread view has real evidence (see `lab/README.md`), e.g. `cd lab && python3 domain.py status` then `python3 domain.py on eservices-lab tls-legacy` and `python3 domain.py verify`. Re-run the Drift captures. **Skip this step rather than inventing data if the lab does not come up quickly.**

- [ ] **Step 6: Present for approval**

Leave both servers running, report the live URL (`http://127.0.0.1:5173`) and the screenshot folder path, and ask for approve/reject per surface.

- [ ] **Step 7: Update project state and push**

Update `docs/PROJECT-STATE.md` with what changed, what is next, and a pointer to this plan's header for the approved decisions (do not re-list them), then:

```bash
git add docs/PROJECT-STATE.md
git commit -m "docs: record the Clarity SecOps UI restyle in project state"
git push origin main
```

---

## Self-review notes

- **Spec coverage:** DESIGN.md palette → Task 1; typography → Tasks 1 + per-page rules; sidebar/tab-bar layout → Task 2; shapes (8px controls, 16px cards) → Tasks 1/2/4; components (buttons, chips, inputs, cards) → Tasks 1/4; the four screens → Tasks 3–6; mobile examples → Task 2 (shell) + Task 7 (page rules); every dropped mock element is enumerated in Global Constraints.
- **Type consistency:** `narrow` (not `navNarrow`) everywhere from Task 2 on; `Icon({ name })`; `APP_VERSION`; `Readout` keeps its signature with an optional denominator; filter keys `all|authorized|pending|refused` used identically in JSX and tests.
- **Test counts:** baseline 86 → Task 2 nets 0 (three AppShell tests: two rewritten, Menu test replaced) → 88 (Drift +2) → 91 (Targets +3) → 92 (Evaluation +1) → 93 (Settings +1).
