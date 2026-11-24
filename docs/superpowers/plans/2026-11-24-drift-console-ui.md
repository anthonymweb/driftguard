# Drift Console UI — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development`
> (recommended) or `executing-plans` to implement this plan task by task. Steps use
> checkbox (`- [ ]`) syntax. Work in the repository root. Do not start a task before the
> previous task's tests and build pass.

**Goal:** Replace the generic dark dashboard with the approved comparison-first Drift
console: a light measurement sheet where one authorised target's scan history is read as
a calibrated thread grid, and every state is backed by stored evidence.

**Architecture:** React 19 + Vite single-page application. Plain CSS with design tokens;
no routing, state, or chart library. A small API client owns auth headers and error
mapping. Pure modules own routing, formatting, thread construction, difference copy, and
CSV. The console makes one `/api/targets` call for the index and one
`/api/targets/{id}/history` call per selected target, removing the old N+1 fetch pattern.

**Tech stack:** React 19, Vite 8, Vitest 5, jsdom, Testing Library, Fontsource
(Chivo + Chivo Mono), plain CSS. No TypeScript, no Tailwind, no component library.

**Spec:** `docs/superpowers/specs/2026-11-24-drift-console-design.md` (approved).
**Backend contract:** `docs/superpowers/plans/2026-11-24-drift-read-api.md`. Implement the
backend plan first. Frontend tests mock the API, but live integration depends on
`last_scan`/`scannable`/`refusal_reasons`, `/history`, `/stats`, and `/evaluation`.

---

## Global constraints

- **Evidence only.** No sample findings, seeded demo rows, illustrative failures, or
  implied “all clear” when the database is empty.
- **Only completed scans are compared.** `queued` and `running` are pending columns;
  `failed` and `completed_with_errors` are `NOT COMPARED` hatched columns. Evidence from
  an incomplete scan never creates a thread row and never produces a `FIXED` mark.
- **Frozen labels verbatim:** `BASELINE`, `NO DRIFT`, `NEW`, `PERSISTENT`, `FIXED`,
  `RECURRING`. No synonyms. Scan-level summary states are `BASELINE`, `NO DRIFT`,
  `CHANGED`, `INCOMPLETE`.
- **User-facing language:** product is “security drift detection”; mechanism is
  “comparison” / “what changed between scans”. Never print “comparator”.
- **No invented authorisation.** Pending targets show `PENDING — scanning refused` and
  no authorisation fields. Only display fields the API returns.
- **Redaction before export.** Downloaded CSV and copied JSON come from
  `/api/scans/{id}/evidence/redacted`. Raw `details` are shown in the local-only detail
  rail and are never placed in an export.
- **One request per subject.** `/api/targets` once for the index; one `/history` call per
  selected target. No per-target fan-out. Abort in-flight requests on target switch.
- **Polling is narrow.** Poll only while a scan the user just queued is `queued` or
  `running`; stop when it settles.
- **A11y floor:** real table semantics, visible focus ring, keyboard-operable rows and
  sheets, text alternatives for every mark, `prefers-reduced-motion` honoured, WCAG AA
  contrast on paper/sheet.

## Visual system (fixed by the spec)

| Token | Value | Use |
|---|---|---|
| `--paper` | `#ECEAE3` | page ground |
| `--sheet` | `#F5F3ED` | raised sheet / selected row |
| `--ink` | `#15181A` | primary text, rules, marks |
| `--ink-2` | `#565B5B` | secondary text |
| `--rule` | `#C7C3B7` | hairlines, grid, separators |
| `--signal` | `#1E45C8` | change, focus, links, newest scan |
| `--risk` | `#A93627` | Critical/High severity only |
| `--verified` | `#2C6A4F` | FIXED / verified only |
| `--pending` | `#8A600F` | pending authorisation, warnings |

Chivo for UI, Chivo Mono for data. No gradients, glows, cards, sparklines, or icon
navigation. Rules of 1px `--rule`; emphasis rules 2px `--ink`. Classification tokens and
engraved labels are uppercase mono, 11px, `0.08em` tracking.

## File map

Create:

```text
frontend/vite.config.js
frontend/src/test/setup.js
frontend/src/api/client.js              frontend/src/api/client.test.js
frontend/src/state/session.js           frontend/src/state/session.test.js
frontend/src/state/useHashRoute.js      frontend/src/state/useHashRoute.test.js
frontend/src/state/useTargets.js
frontend/src/state/useHistory.js
frontend/src/lib/format.js              frontend/src/lib/format.test.js
frontend/src/lib/threads.js             frontend/src/lib/threads.test.js
frontend/src/lib/difference.js          frontend/src/lib/difference.test.js
frontend/src/lib/csv.js                 frontend/src/lib/csv.test.js
frontend/src/lib/target-form.js         frontend/src/lib/target-form.test.js
frontend/src/components/AppShell.jsx
frontend/src/components/StateBlocks.jsx
frontend/src/components/SignIn.jsx
frontend/src/components/ErrorBoundary.jsx
frontend/src/components/TargetIndex.jsx
frontend/src/components/AuthorisationStamp.jsx
frontend/src/components/DifferenceLine.jsx
frontend/src/components/ScanAxis.jsx
frontend/src/components/ThreadGrid.jsx
frontend/src/components/ThreadRow.jsx
frontend/src/components/EvidenceDetail.jsx
frontend/src/components/RegisterTargetSheet.jsx
frontend/src/pages/Drift.jsx
frontend/src/pages/Targets.jsx
frontend/src/pages/Evaluation.jsx
frontend/src/pages/Settings.jsx
frontend/src/styles/index.css
frontend/src/styles/tokens.css
frontend/src/styles/base.css
frontend/src/styles/shell.css
frontend/src/styles/drift.css
frontend/src/styles/targets.css
frontend/src/styles/evaluation.css
frontend/src/styles/responsive.css
```

Delete after the replacement is wired: `frontend/src/styles.css`,
`frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/preview.png`.
Replace `frontend/src/App.jsx`. Keep `frontend/src/main.jsx` as the entry point.

---

## Task 1: Test harness, formatting, fonts, tokens

**Files:**
- Modify: `frontend/package.json`, `frontend/index.html`, `frontend/src/main.jsx`
- Create: `frontend/vite.config.js`, `frontend/src/test/setup.js`,
  `frontend/src/lib/format.js`, `frontend/src/lib/format.test.js`,
  `frontend/src/styles/index.css`, `frontend/src/styles/tokens.css`,
  `frontend/src/styles/base.css`, and empty `shell.css`, `drift.css`, `targets.css`,
  `evaluation.css`, `responsive.css`
- Delete: `frontend/tailwind.config.js`, `frontend/postcss.config.js`,
  `frontend/preview.png`, `frontend/src/styles.css`

**Interfaces:**
- Produces:
  - `formatDate(value: string|null): string` → `12 Nov 2026`, `—` for missing/invalid.
  - `formatDateTime(value): string` → `12 Nov 2026 · 09:30 UTC`.
  - `formatPorts(ports: number[]): string` → `8443, 8080`; `—` when empty.
  - `formatScope(scope: string[]): string` → `TLS / NETWORK / API`; `—` when empty.
  - `countLabel(count: number, label: string): string` → `1 new`, `2 persistent`.
  - `formatRate(rate: number|null): string` → `96.4%`; `—` when null.
  - `__APP_VERSION__` injected by Vite.

- [ ] **Step 1: Write the failing formatting tests**

Create `frontend/src/lib/format.test.js`:

```js
import { describe, expect, it } from 'vitest';

import {
  countLabel,
  formatDate,
  formatDateTime,
  formatPorts,
  formatRate,
  formatScope,
} from './format';

describe('format', () => {
  it('formats dates in UTC so the sheet reads the same everywhere', () => {
    expect(formatDate('2026-11-12T09:30:00Z')).toBe('12 Nov 2026');
    expect(formatDateTime('2026-11-12T09:30:00Z')).toBe('12 Nov 2026 · 09:30 UTC');
  });

  it('returns an em dash for missing or invalid dates', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('not-a-date')).toBe('—');
    expect(formatDateTime(undefined)).toBe('—');
  });

  it('formats approved scope and ports without inventing values', () => {
    expect(formatScope(['tls', 'network', 'http_api'])).toBe('TLS / NETWORK / API');
    expect(formatScope([])).toBe('—');
    expect(formatPorts([8443, 8080])).toBe('8443, 8080');
    expect(formatPorts([])).toBe('—');
  });

  it('formats counts and rates for the difference line and readouts', () => {
    expect(countLabel(1, 'new')).toBe('1 new');
    expect(countLabel(2, 'persistent')).toBe('2 persistent');
    expect(formatRate(0.964)).toBe('96.4%');
    expect(formatRate(0)).toBe('0.0%');
    expect(formatRate(null)).toBe('—');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/lib/format.test.js
```

Expected: FAIL because `./format` cannot be resolved (dependencies not installed yet is
also acceptable; install them in Step 3).

- [ ] **Step 3: Replace the tooling and implement the formatter**

Rewrite `frontend/package.json` as:

```json
{
  "name": "driftguard-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vite build",
    "preview": "vite preview --host 127.0.0.1",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@fontsource-variable/chivo": "^5.3.0",
    "@fontsource-variable/chivo-mono": "^5.3.0",
    "react": "19.3.1",
    "react-dom": "19.3.1"
  },
  "devDependencies": {
    "@testing-library/react": "^16.3.3",
    "@testing-library/user-event": "^14.6.13",
    "@vitejs/plugin-react": "^6.3.0",
    "jsdom": "^31.0.1",
    "vite": "^8.3.6",
    "vitest": "^5.1.1"
  }
}
```

Two deliberate tooling decisions:

- **Fonts:** the spec says self-hosted under `src/assets/fonts/`. Fontsource packages
  are the same thing delivered through npm: the WOFF2 files ship in the package and are
  bundled by Vite, so the built console makes **no network request for fonts** (a hard
  requirement — the console may run offline). Import the package root (the `wght`
  variable axis), and keep the fallback stacks from `tokens.css` so layout does not
  materially change if a font is missing.
- **`lucide-react` is removed, not kept.** The spec retains it *only* for universal
  actions, but every action in this console is named in words (`Refresh`, `Close`,
  `Run scan`, `Export redacted evidence`), and icon-only chrome is an anti-goal. An
  unused dependency is worse than none. Do not re-add an icon set without a written
  reason in the design doc.

Create `frontend/vite.config.js`:

```js
import { readFileSync } from 'node:fs';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'));

export default defineConfig({
  plugins: [react()],
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
  server: { host: '127.0.0.1', port: 5173 },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    include: ['src/**/*.test.{js,jsx}'],
  },
});
```

Create `frontend/src/test/setup.js`:

```js
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => cleanup());
```

Create `frontend/src/lib/format.js`:

```js
const DATE = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
});
const TIME = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC',
});

function asDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value) {
  const date = asDate(value);
  return date ? DATE.format(date) : '—';
}

export function formatDateTime(value) {
  const date = asDate(value);
  return date ? `${DATE.format(date)} · ${TIME.format(date)} UTC` : '—';
}

export function formatPorts(ports) {
  return ports?.length ? ports.join(', ') : '—';
}

const SCOPE_LABELS = { tls: 'TLS', network: 'NETWORK', http_api: 'API' };

export function formatScope(scope) {
  return scope?.length
    ? scope.map((item) => SCOPE_LABELS[item] ?? item.toUpperCase()).join(' / ')
    : '—';
}

export function countLabel(count, label) {
  return `${count} ${label}`;
}

export function formatRate(rate) {
  return rate == null ? '—' : `${(rate * 100).toFixed(1)}%`;
}
```

Create `frontend/src/styles/tokens.css` with the palette plus spacing/type tokens:

```css
:root {
  --paper: #ECEAE3;
  --sheet: #F5F3ED;
  --ink: #15181A;
  --ink-2: #565B5B;
  --rule: #C7C3B7;
  --signal: #1E45C8;
  --risk: #A93627;
  --verified: #2C6A4F;
  --pending: #8A600F;

  --font-ui: 'Chivo Variable', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'Chivo Mono Variable', ui-monospace, monospace;

  --step--1: 0.6875rem;
  --step-0: 0.875rem;
  --step-1: 1rem;
  --step-2: 1.5rem;
  --step-3: 1.75rem;
  --step-4: 2.5rem;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;

  --index-width: 236px;
  --top-height: 64px;
  --row-height: 38px;
}
```

Create `frontend/src/styles/base.css` with the reset and shared primitives:

```css
* { box-sizing: border-box; }

html, body, #root { min-height: 100%; }

body {
  margin: 0;
  min-width: 320px;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-ui);
  font-size: var(--step-0);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

button, input, select, textarea { font: inherit; color: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; }
a { color: var(--signal); text-underline-offset: 3px; }

:focus-visible {
  outline: 2px solid var(--signal);
  outline-offset: 2px;
}

.visually-hidden {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}

.engraved {
  font-family: var(--font-mono);
  font-size: var(--step--1);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-2);
}

.mono { font-family: var(--font-mono); }

.rule { border: 0; border-top: 1px solid var(--rule); margin: 0; }

.sheet {
  background: var(--sheet);
  border: 1px solid var(--rule);
}

.text-button {
  border: 0;
  background: none;
  padding: 0;
  color: var(--signal);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.primary-button,
.secondary-button {
  border: 1px solid var(--ink);
  padding: 8px 14px;
  font-family: var(--font-mono);
  font-size: var(--step--1);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.primary-button { background: var(--ink); color: var(--paper); }
.primary-button:disabled,
.secondary-button:disabled { opacity: 0.42; }
.secondary-button { background: transparent; color: var(--ink); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

Create `frontend/src/styles/index.css`:

```css
@import './tokens.css';
@import './base.css';
@import './shell.css';
@import './drift.css';
@import './targets.css';
@import './evaluation.css';
@import './responsive.css';
```

Create the four imported-but-not-yet-filled files with a one-line comment so Vite can
resolve them.

Update `frontend/src/main.jsx`:

```jsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/chivo';
import '@fontsource-variable/chivo-mono';
import './styles/index.css';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
```

Update `frontend/index.html` head: `theme-color` `#ECEAE3`, description
`Security drift detection for authorised targets`, title `DriftGuard · Drift console`.

Delete the Tailwind config, PostCSS config, old stylesheet, and stale screenshot.

- [ ] **Step 4: Install and verify**

```bash
cd frontend && npm install
npm test -- --run src/lib/format.test.js
npm run build
```

Expected: formatting tests PASS and the old app still builds (it renders with default
browser styles until later tasks replace it).

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.js \
  frontend/index.html frontend/src/main.jsx frontend/src/test/setup.js \
  frontend/src/lib/format.js frontend/src/lib/format.test.js frontend/src/styles
git rm frontend/tailwind.config.js frontend/postcss.config.js \
  frontend/preview.png frontend/src/styles.css
git commit -m "chore(ui): vitest, self-hosted fonts, and the measurement-sheet tokens"
```

---

## Task 2: API client and session storage

**Files:**
- Create: `frontend/src/api/client.js`, `frontend/src/api/client.test.js`
- Create: `frontend/src/state/session.js`, `frontend/src/state/session.test.js`

**Interfaces:**
- Produces:
  - `class ApiError extends Error` with `status: number` (0 for transport failures) and
    `detail: string|object|null`.
  - `createApiClient({ baseUrl, getToken, fetchImpl, onUnauthorized })` → object with
    `targets()`, `target(id)`, `history(id, {limit, signal})`, `stats()`,
    `evaluation()`, `redactedEvidence(scanId, {signal})`,
    `login(username, password)`, `createTarget(payload)`, `runScan(id)`.
  - `SESSION_KEY`, `toSession(tokenResponse, now)`, `loadSession(storage, now)`,
    `saveSession(session, storage)`, `clearSession(storage)`.

- [ ] **Step 1: Write the failing client tests**

Create `frontend/src/api/client.test.js`:

```js
import { describe, expect, it, vi } from 'vitest';

import { ApiError, createApiClient } from './client';

function jsonResponse(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function makeClient(overrides = {}) {
  const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
  const onUnauthorized = vi.fn();
  const client = createApiClient({
    baseUrl: 'http://127.0.0.1:8000',
    getToken: () => 'tok-123',
    fetchImpl,
    onUnauthorized,
    ...overrides,
  });
  return { client, fetchImpl, onUnauthorized };
}

describe('api client', () => {
  it('sends the bearer token and parses JSON', async () => {
    const { client, fetchImpl } = makeClient();
    await client.targets();

    expect(fetchImpl).toHaveBeenCalledOnce();
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8000/api/targets');
    expect(init.headers.Authorization).toBe('Bearer tok-123');
  });

  it('omits the token header in local-research mode', async () => {
    const { client, fetchImpl } = makeClient({ getToken: () => null });
    await client.stats();
    expect(fetchImpl.mock.calls[0][1].headers).not.toHaveProperty('Authorization');
  });

  it('requests one history page with the default limit and forwards abort signals', async () => {
    const { client, fetchImpl } = makeClient();
    const controller = new AbortController();
    await client.history(7, { signal: controller.signal });

    expect(fetchImpl.mock.calls[0][0]).toBe(
      'http://127.0.0.1:8000/api/targets/7/history?limit=20',
    );
    expect(fetchImpl.mock.calls[0][1].signal).toBe(controller.signal);
  });

  it('posts credentials and target payloads as JSON', async () => {
    const { client, fetchImpl } = makeClient();
    await client.login('alice', 'correct horse');
    await client.createTarget({ name: 'svc' });

    const [, loginInit] = fetchImpl.mock.calls[0];
    expect(loginInit.method).toBe('POST');
    expect(loginInit.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(loginInit.body)).toEqual({ username: 'alice', password: 'correct horse' });
    expect(fetchImpl.mock.calls[1][1].method).toBe('POST');
  });

  it('reports 401, notifies the shell, and keeps the status', async () => {
    const { client, onUnauthorized } = makeClient({
      fetchImpl: vi.fn().mockResolvedValue(jsonResponse({ detail: 'Not authenticated' }, 401)),
    });
    await expect(client.targets()).rejects.toMatchObject({ status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('turns a transport failure into actionable copy', async () => {
    const { client } = makeClient({
      fetchImpl: vi.fn().mockRejectedValue(new TypeError('fetch failed')),
    });
    await expect(client.targets()).rejects.toBeInstanceOf(ApiError);
    await expect(client.targets()).rejects.toThrow(
      'API unreachable at 127.0.0.1:8000. Start the backend, then retry.',
    );
  });

  it('surfaces a scan refusal without the raw FastAPI prefix', async () => {
    const { client } = makeClient({
      fetchImpl: vi.fn().mockResolvedValue(jsonResponse(
        { detail: 'Scan refused: target must be explicitly authorized' }, 422,
      )),
    });
    await expect(client.runScan(4)).rejects.toThrow(
      'The request was refused: target must be explicitly authorized',
    );
  });

  it('does not notify on abort', async () => {
    const abort = Object.assign(new Error('aborted'), { name: 'AbortError' });
    const { client, onUnauthorized } = makeClient({
      fetchImpl: vi.fn().mockRejectedValue(abort),
    });
    await expect(client.targets()).rejects.toBe(abort);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
```

Create `frontend/src/state/session.test.js`:

```js
import { describe, expect, it } from 'vitest';

import { SESSION_KEY, clearSession, loadSession, saveSession, toSession } from './session';

function memoryStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

describe('session storage', () => {
  it('converts a token response into an expiring session', () => {
    const session = toSession(
      { access_token: 'jwt', expires_in: 3600, username: 'alice', role: 'admin' },
      1_000,
    );
    expect(session).toEqual({
      token: 'jwt', username: 'alice', role: 'admin', expiresAt: 3_601_000,
    });
  });

  it('round-trips a live session', () => {
    const storage = memoryStorage();
    saveSession({ token: 'jwt', username: 'alice', role: 'admin', expiresAt: 5_000 }, storage);
    expect(loadSession(storage, 4_999)).toMatchObject({ token: 'jwt', username: 'alice' });
  });

  it('drops expired and malformed sessions instead of using them', () => {
    const expired = memoryStorage({
      [SESSION_KEY]: JSON.stringify({
        token: 'jwt', username: 'alice', role: 'admin', expiresAt: 5_000,
      }),
    });
    expect(loadSession(expired, 5_000)).toBeNull();
    expect(expired.getItem(SESSION_KEY)).toBeNull();

    const malformed = memoryStorage({ [SESSION_KEY]: '{not json' });
    expect(loadSession(malformed, 1)).toBeNull();
    expect(clearSession(malformed)).toBeUndefined();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/api/client.test.js src/state/session.test.js
```

Expected: FAIL, modules not found.

- [ ] **Step 3: Implement the client and session module**

Create `frontend/src/api/client.js`:

```js
const DEFAULT_BASE = (import.meta.env?.VITE_API_URL || 'http://127.0.0.1:8000')
  .replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, detail = null, cause } = {}) {
    super(message, { cause });
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

function hostOf(baseUrl) {
  try { return new URL(baseUrl).host; } catch { return baseUrl; }
}

function cleanDetail(detail) {
  if (typeof detail !== 'string') return null;
  return detail.replace(/^Scan refused:\s*/i, '').trim() || null;
}

export function describeStatus(status, detail) {
  const value = cleanDetail(detail);
  switch (status) {
    case 401: return 'Sign in to continue.';
    case 403: return value ?? 'This action is not permitted for your role.';
    case 404: return value ?? 'The requested record was not found.';
    case 409: return value ?? 'That record already exists.';
    case 422: return value
      ? `The request was refused: ${value}`
      : 'The request was refused. Check the fields and approved scope.';
    case 429: return 'Too many attempts. Wait a minute, then retry.';
    case 503: return 'The API is not ready. Check the database, then retry.';
    default: return value ?? `The API returned HTTP ${status}.`;
  }
}

export function createApiClient({
  baseUrl = DEFAULT_BASE,
  getToken = () => null,
  fetchImpl = globalThis.fetch,
  onUnauthorized = () => {},
} = {}) {
  async function request(path, { method = 'GET', body, signal } = {}) {
    const headers = { Accept: 'application/json' };
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    let response;
    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (error) {
      if (error?.name === 'AbortError') throw error;
      throw new ApiError(
        `API unreachable at ${hostOf(baseUrl)}. Start the backend, then retry.`,
        { cause: error },
      );
    }

    if (!response.ok) {
      let detail = null;
      try { detail = (await response.json())?.detail ?? null; } catch { /* non-JSON error */ }
      if (response.status === 401) onUnauthorized();
      throw new ApiError(describeStatus(response.status, detail), {
        status: response.status,
        detail,
      });
    }

    if (response.status === 204) return null;
    return response.json();
  }

  return {
    request,
    targets: () => request('/api/targets'),
    target: (id) => request(`/api/targets/${id}`),
    history: (id, { limit = 20, signal } = {}) =>
      request(`/api/targets/${id}/history?limit=${limit}`, { signal }),
    stats: () => request('/api/stats'),
    evaluation: () => request('/api/evaluation'),
    redactedEvidence: (scanId, { signal } = {}) =>
      request(`/api/scans/${scanId}/evidence/redacted`, { signal }),
    login: (username, password) =>
      request('/api/auth/token', { method: 'POST', body: { username, password } }),
    createTarget: (payload) =>
      request('/api/targets', { method: 'POST', body: payload }),
    runScan: (id) => request(`/api/targets/${id}/scans`, { method: 'POST' }),
  };
}
```

Create `frontend/src/state/session.js`:

```js
export const SESSION_KEY = 'driftguard.session';

export function toSession(tokenResponse, now = Date.now()) {
  return {
    token: tokenResponse.access_token,
    username: tokenResponse.username,
    role: tokenResponse.role,
    expiresAt: now + tokenResponse.expires_in * 1000,
  };
}

export function loadSession(storage = globalThis.sessionStorage, now = Date.now()) {
  let raw;
  try { raw = storage.getItem(SESSION_KEY); } catch { return null; }
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    const valid = value
      && typeof value.token === 'string'
      && typeof value.username === 'string'
      && typeof value.role === 'string'
      && Number.isFinite(value.expiresAt);
    if (!valid || value.expiresAt <= now) {
      storage.removeItem(SESSION_KEY);
      return null;
    }
    return value;
  } catch {
    storage.removeItem(SESSION_KEY);
    return null;
  }
}

export function saveSession(session, storage = globalThis.sessionStorage) {
  storage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(storage = globalThis.sessionStorage) {
  storage.removeItem(SESSION_KEY);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run src/api/client.test.js src/state/session.test.js
```

Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api frontend/src/state/session.js frontend/src/state/session.test.js
git commit -m "feat(ui): typed API client and expiring in-memory session"
```

---

## Task 3: Hash routing

**Files:**
- Create: `frontend/src/state/useHashRoute.js`, `frontend/src/state/useHashRoute.test.js`

**Interfaces:**
- Produces:
  - `parseHash(hash: string): { page: 'drift'|'targets'|'evaluation'|'settings', targetId: number|null }`
  - `routeToHash(route): string`
  - `useHashRoute(): route`
  - `navigate(route, { replace = false, win = window }): void`
- Unknown or malformed hashes resolve to `{ page: 'drift', targetId: null }`; they never
  throw and never silently select a target.

- [ ] **Step 1: Write the failing routing tests**

Create `frontend/src/state/useHashRoute.test.js`:

```js
import { describe, expect, it, vi } from 'vitest';

import { navigate, parseHash, routeToHash } from './useHashRoute';

describe('hash routing', () => {
  it('parses the four destinations', () => {
    expect(parseHash('')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/drift')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/targets')).toEqual({ page: 'targets', targetId: null });
    expect(parseHash('#/evaluation')).toEqual({ page: 'evaluation', targetId: null });
    expect(parseHash('#/settings')).toEqual({ page: 'settings', targetId: null });
  });

  it('deep-links a target', () => {
    expect(parseHash('#/drift/12')).toEqual({ page: 'drift', targetId: 12 });
    expect(parseHash('#/drift/12/')).toEqual({ page: 'drift', targetId: 12 });
  });

  it('falls back to Drift for unknown or malformed input', () => {
    expect(parseHash('#/nope')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/drift/abc')).toEqual({ page: 'drift', targetId: null });
    expect(parseHash('#/drift/0')).toEqual({ page: 'drift', targetId: null });
  });

  it('round-trips destinations', () => {
    expect(routeToHash({ page: 'targets' })).toBe('#/targets');
    expect(routeToHash({ page: 'drift', targetId: 3 })).toBe('#/drift/3');
    expect(parseHash(routeToHash({ page: 'drift', targetId: 9 })))
      .toEqual({ page: 'drift', targetId: 9 });
  });

  it('replaces history without stacking entries', () => {
    const win = {
      location: { hash: '#/targets' },
      history: { replaceState: vi.fn() },
      dispatchEvent: vi.fn(),
      Event: globalThis.Event,
    };
    navigate({ page: 'drift', targetId: 2 }, { replace: true, win });
    expect(win.history.replaceState).toHaveBeenCalledWith(null, '', '#/drift/2');
    expect(win.dispatchEvent).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/state/useHashRoute.test.js
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement routing**

Create `frontend/src/state/useHashRoute.js`:

```js
import { useEffect, useState } from 'react';

export const PAGES = ['drift', 'targets', 'evaluation', 'settings'];
const TARGET_HASH = /^\/drift\/([1-9]\d*)\/?$/;

export function parseHash(hash = '') {
  const raw = hash.replace(/^#/, '');
  if (!raw || raw === '/') return { page: 'drift', targetId: null };
  if (raw === '/drift' || raw === '/drift/') {
    return { page: 'drift', targetId: null };
  }
  const target = TARGET_HASH.exec(raw);
  if (target) return { page: 'drift', targetId: Number(target[1]) };
  const page = raw.replace(/^\/|\/$/g, '');
  if (PAGES.includes(page)) return { page, targetId: null };
  return { page: 'drift', targetId: null };
}

export function routeToHash({ page = 'drift', targetId = null } = {}) {
  if (page === 'drift') {
    return targetId == null ? '#/drift' : `#/drift/${targetId}`;
  }
  return `#/${page}`;
}

export function navigate(route, { replace = false, win = window } = {}) {
  const hash = routeToHash(route);
  if (win.location.hash === hash) return;
  if (replace) {
    win.history.replaceState(null, '', hash);
    win.dispatchEvent(new win.Event('hashchange'));
  } else {
    win.location.hash = hash;
  }
}

export function useHashRoute(win = window) {
  const [route, setRoute] = useState(() => parseHash(win.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseHash(win.location.hash));
    onChange();
    win.addEventListener('hashchange', onChange);
    return () => win.removeEventListener('hashchange', onChange);
  }, [win]);

  return route;
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd frontend && npm test -- --run src/state/useHashRoute.test.js
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/state/useHashRoute.js frontend/src/state/useHashRoute.test.js
git commit -m "feat(ui): deep-linkable hash routes for the four console pages"
```

---

## Task 4: Thread model

This is the core of the console. Build it as a pure function before any component. The
model must agree with the stored `DriftEvent` rows; it never infers a finding from a scan
that was not completed.

**Files:**
- Create: `frontend/src/lib/threads.js`, `frontend/src/lib/threads.test.js`

**Interfaces:**
- `buildThreadModel(history)` → model:
  ```js
  {
    scans: [{ id, status, startedAt, completedAt, label, comparable, pending,
              summary, kind, item }],
    groups: [{ key: 'TLS'|'NETWORK'|'API'|'OTHER',
               rows: [{ fingerprint, title, category, area, severity, resource,
                        cells, current: { classification, scanId },
                        detail, observedAt }] }],
    latestComparable: scan|null,
    previousComparable: scan|null,
    hasComparable: boolean,
    pendingScans: scan[],
  }
  ```
- Scan `kind`: `baseline` | `compared` | `incomplete` | `pending`.
- Cell `kind`: `baseline` | `present` | `new` | `recurring` | `fixed` | `absent` |
  `never` | `incomplete` | `pending`.
- Cells are aligned with `model.scans`, oldest first. `lineLeft`/`lineRight` describe the
  rule segments the renderer draws around a mark.

- [ ] **Step 1: Write the failing thread tests**

Create `frontend/src/lib/threads.test.js`:

```js
import { describe, expect, it } from 'vitest';

import { buildThreadModel } from './threads';

const META = {
  't/TLS/a': { title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: 't:8443' },
  't/Network/b': { title: 'Plain HTTP', category: 'Network', severity: 'High', resource: 't:8080' },
  't/Network/c': { title: 'Open port', category: 'Network', severity: 'Medium', resource: 't:9000' },
  't/API/d': { title: 'Debug endpoint', category: 'API', severity: 'Medium', resource: '/debug' },
};

function history(scans, fingerprints = META) {
  return {
    target: { id: 1, name: 't' },
    scans: scans.map(({
      id, status = 'completed', evidence = [], drift = {},
      state = 'CHANGED', counts = {},
    }) => ({
      scan: {
        id,
        target_id: 1,
        status,
        started_at: '2026-11-12T09:30:00Z',
        completed_at: status === 'completed' ? '2026-11-12T09:31:00Z' : null,
        is_baseline: state === 'BASELINE',
        label: null,
        error: null,
      },
      comparable: status === 'completed',
      evidence: evidence.map((fingerprint, index) => ({
        id: id * 10 + index, scan_id: id, fingerprint,
      })),
      drift: Object.entries(drift).map(([evidence_fingerprint, classification], index) => ({
        id: index, scan_id: id, evidence_fingerprint, classification,
      })),
      summary: {
        state,
        counts: { NEW: 0, PERSISTENT: 0, FIXED: 0, RECURRING: 0, ...counts },
      },
    })),
    fingerprints,
  };
}

function row(model, fingerprint) {
  return model.groups.flatMap((group) => group.rows)
    .find((candidate) => candidate.fingerprint === fingerprint);
}

describe('thread model', () => {
  it('orders scans oldest first and classifies presence, new, fixed, and never observed', () => {
    const model = buildThreadModel(history([
      {
        id: 2, evidence: ['t/TLS/a', 't/Network/c'],
        drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'FIXED', 't/Network/c': 'NEW' },
        counts: { PERSISTENT: 1, FIXED: 1, NEW: 1 },
      },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a', 't/Network/b'] },
    ]));

    expect(model.scans.map((scan) => scan.id)).toEqual([1, 2]);
    expect(model.latestComparable.id).toBe(2);
    expect(model.previousComparable.id).toBe(1);

    expect(row(model, 't/TLS/a').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'present']);
    expect(row(model, 't/TLS/a').current.classification).toBe('PERSISTENT');

    expect(row(model, 't/Network/b').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'fixed']);
    expect(row(model, 't/Network/b').current.classification).toBe('FIXED');

    expect(row(model, 't/Network/c').cells.map((cell) => cell.kind))
      .toEqual(['never', 'new']);
    expect(row(model, 't/Network/c').current.classification).toBe('NEW');
  });

  it('keeps FIXED current through later absences and clears it only on a recurrence', () => {
    const fixedThenAbsent = buildThreadModel(history([
      { id: 3, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT' } },
      { id: 2, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'FIXED' } },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a', 't/Network/b'] },
    ]));
    expect(row(fixedThenAbsent, 't/Network/b').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'fixed', 'absent']);
    expect(row(fixedThenAbsent, 't/Network/b').current.classification).toBe('FIXED');

    const recurring = buildThreadModel(history([
      {
        id: 3, evidence: ['t/TLS/a', 't/Network/b'],
        drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'RECURRING' },
      },
      { id: 2, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT', 't/Network/b': 'FIXED' } },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a', 't/Network/b'] },
    ]));
    expect(row(recurring, 't/Network/b').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'fixed', 'recurring']);
    expect(row(recurring, 't/Network/b').current.classification).toBe('RECURRING');
  });

  it('does not advance the thread through an incomplete scan', () => {
    const model = buildThreadModel(history([
      { id: 5 },
      { id: 4, evidence: ['t/TLS/a'], drift: { 't/TLS/a': 'PERSISTENT' } },
      {
        id: 3, status: 'completed_with_errors',
        evidence: ['t/TLS/a', 't/API/d'], drift: { 't/TLS/a': 'FIXED' },
      },
      { id: 2, state: 'BASELINE', evidence: ['t/TLS/a'] },
    ]));

    expect(model.scans.map((scan) => scan.kind))
      .toEqual(['baseline', 'incomplete', 'compared', 'compared']);
    expect(row(model, 't/TLS/a').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'incomplete', 'present', 'absent']);
    expect(row(model, 't/API/d')).toBeUndefined();
    expect(model.groups.flatMap((group) => group.rows)).toHaveLength(1);
  });

  it('keeps pending scans as pending columns without comparing them', () => {
    const model = buildThreadModel(history([
      { id: 2, status: 'running' },
      { id: 1, state: 'BASELINE', evidence: ['t/TLS/a'] },
    ]));
    expect(model.pendingScans.map((scan) => scan.id)).toEqual([2]);
    expect(model.scans.map((scan) => scan.kind)).toEqual(['baseline', 'pending']);
    expect(row(model, 't/TLS/a').cells.map((cell) => cell.kind))
      .toEqual(['baseline', 'pending']);
    expect(row(model, 't/TLS/a').current.classification).toBe('BASELINE');
  });

  it('reports no comparable history when only incomplete scans exist', () => {
    const model = buildThreadModel(history([
      { id: 1, status: 'failed', evidence: ['t/TLS/a'] },
    ]));
    expect(model.hasComparable).toBe(false);
    expect(model.latestComparable).toBeNull();
    expect(model.groups).toEqual([]);
  });

  it('groups rows in TLS, NETWORK, API order and sorts by title', () => {
    const model = buildThreadModel(history([
      {
        id: 1, state: 'BASELINE',
        evidence: ['t/API/d', 't/Network/c', 't/TLS/a'],
      },
    ]));
    expect(model.groups.map((group) => group.key)).toEqual(['TLS', 'NETWORK', 'API']);
    expect(model.groups[1].rows.map((entry) => entry.title)).toEqual(['Open port']);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/lib/threads.test.js
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement the model**

Create `frontend/src/lib/threads.js`:

```js
const AREA_ORDER = ['TLS', 'NETWORK', 'API'];
const PRESENT_KINDS = new Set(['present', 'baseline', 'new', 'recurring']);

function areaOf(category) {
  const key = String(category ?? '').toUpperCase();
  return AREA_ORDER.includes(key) ? key : 'OTHER';
}

function isPending(status) {
  return status === 'queued' || status === 'running';
}

function nextComparableCell(cells, scans, index) {
  for (let cursor = index + 1; cursor < cells.length; cursor += 1) {
    if (scans[cursor].comparable) return cells[cursor];
  }
  return null;
}

function previousComparableCell(cells, scans, index) {
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    if (scans[cursor].comparable) return cells[cursor];
  }
  return null;
}

export function buildThreadModel(history = {}) {
  const fingerprints = history.fingerprints ?? {};
  const items = [...(history.scans ?? [])].sort((a, b) => a.scan.id - b.scan.id);

  const scans = items.map((item) => {
    const comparable = item.comparable === true && item.scan.status === 'completed';
    const summary = item.summary
      ?? { state: comparable ? 'CHANGED' : 'INCOMPLETE', counts: {} };
    let kind = 'incomplete';
    if (comparable) kind = summary.state === 'BASELINE' ? 'baseline' : 'compared';
    else if (isPending(item.scan.status)) kind = 'pending';
    return {
      id: item.scan.id,
      status: item.scan.status,
      startedAt: item.scan.started_at,
      completedAt: item.scan.completed_at,
      label: item.scan.label ?? null,
      comparable,
      pending: isPending(item.scan.status),
      summary,
      kind,
      item,
    };
  });

  const comparableScans = scans.filter((scan) => scan.comparable);
  const latestComparable = comparableScans.at(-1) ?? null;
  const previousComparable = comparableScans.at(-2) ?? null;

  const driftByScan = new Map();
  const referenced = new Set();
  for (const scan of scans) {
    if (!scan.comparable) continue;
    const drift = new Map();
    for (const event of scan.item.drift ?? []) {
      drift.set(event.evidence_fingerprint, event.classification);
      referenced.add(event.evidence_fingerprint);
    }
    driftByScan.set(scan.id, drift);
    for (const evidence of scan.item.evidence ?? []) {
      referenced.add(evidence.fingerprint);
    }
  }

  const rows = [];
  for (const fingerprint of referenced) {
    const meta = fingerprints[fingerprint] ?? {
      title: fingerprint,
      category: 'OTHER',
      severity: 'Unknown',
      resource: '—',
    };
    const cells = [];
    let everSeen = false;
    let latestEvidence = null;
    let current = null;

    for (const scan of scans) {
      if (!scan.comparable) {
        cells.push({
          scanId: scan.id,
          kind: scan.pending ? 'pending' : 'incomplete',
          classification: null,
          lineLeft: false,
          lineRight: false,
        });
        continue;
      }

      const evidence = (scan.item.evidence ?? [])
        .find((candidate) => candidate.fingerprint === fingerprint);
      const observed = Boolean(evidence);
      const classification = driftByScan.get(scan.id)?.get(fingerprint) ?? null;
      let kind;

      if (observed) {
        everSeen = true;
        latestEvidence = evidence;
        if (scan.kind === 'baseline') kind = 'baseline';
        else if (classification === 'NEW') kind = 'new';
        else if (classification === 'RECURRING') kind = 'recurring';
        else kind = 'present';
        current = {
          classification: kind === 'baseline'
            ? 'BASELINE'
            : kind === 'present' ? 'PERSISTENT' : classification,
          scanId: scan.id,
        };
      } else if (classification === 'FIXED') {
        kind = 'fixed';
        current = { classification: 'FIXED', scanId: scan.id };
      } else {
        kind = everSeen ? 'absent' : 'never';
      }

      cells.push({
        scanId: scan.id, kind, classification, lineLeft: false, lineRight: false,
      });
    }

    if (!current) continue;

    for (let index = 0; index < cells.length; index += 1) {
      const cell = cells[index];
      if (cell.kind === 'present') {
        cell.lineLeft = true;
        cell.lineRight = true;
      } else if (PRESENT_KINDS.has(cell.kind)) {
        cell.lineRight = PRESENT_KINDS.has(
          nextComparableCell(cells, scans, index)?.kind,
        );
      } else if (cell.kind === 'fixed') {
        cell.lineLeft = PRESENT_KINDS.has(
          previousComparableCell(cells, scans, index)?.kind,
        );
      }
    }

    rows.push({
      fingerprint,
      title: meta.title,
      category: meta.category,
      area: areaOf(meta.category),
      severity: meta.severity,
      resource: meta.resource,
      cells,
      current,
      detail: latestEvidence?.details ?? null,
      observedAt: latestEvidence?.observed_at ?? null,
    });
  }

  const groups = [...AREA_ORDER, 'OTHER']
    .map((key) => ({
      key,
      rows: rows
        .filter((entry) => entry.area === key)
        .sort((a, b) => a.title.localeCompare(b.title)
          || a.resource.localeCompare(b.resource)
          || a.fingerprint.localeCompare(b.fingerprint)),
    }))
    .filter((group) => group.rows.length > 0);

  return {
    scans,
    groups,
    latestComparable,
    previousComparable,
    hasComparable: comparableScans.length > 0,
    pendingScans: scans.filter((scan) => scan.pending),
  };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd frontend && npm test -- --run src/lib/threads.test.js
```

Expected: PASS (6 tests). If the grouping fixture is awkward, keep only
`t/API/d`, `t/Network/c`, and `t/TLS/a`, and assert `['Open port']` for `NETWORK`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/threads.js frontend/src/lib/threads.test.js
git commit -m "feat(ui): thread model for completed, fixed, recurring, and not-compared scans"
```

---

## Task 5: Difference line copy

**Files:**
- Create: `frontend/src/lib/difference.js`, `frontend/src/lib/difference.test.js`

**Interfaces:**
- `describeDifference(model)` → `{ text, state }` where `state` is `EMPTY`, `BASELINE`,
  `NO DRIFT`, or `CHANGED`. Counts come from `summary.counts`; the previous scan id comes
  from the model, never from arithmetic on the latest id.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/difference.test.js`:

```js
import { describe, expect, it } from 'vitest';

import { describeDifference } from './difference';

const previous = { id: 12 };

describe('difference line', () => {
  it('says there are no completed observations yet', () => {
    expect(describeDifference({ latestComparable: null })).toEqual({
      text: 'No completed observations yet.', state: 'EMPTY',
    });
  });

  it('dates the baseline instead of inventing a count', () => {
    expect(describeDifference({
      latestComparable: {
        id: 13, kind: 'baseline', startedAt: '2026-11-12T09:30:00Z',
        completedAt: '2026-11-12T09:31:00Z',
        summary: { state: 'BASELINE', counts: {} },
      },
      previousComparable: null,
    })).toEqual({ text: 'Baseline recorded 12 Nov 2026.', state: 'BASELINE' });
  });

  it('names the scan that was compared against', () => {
    expect(describeDifference({
      latestComparable: {
        id: 13, summary: { state: 'NO DRIFT', counts: {} },
      },
      previousComparable: previous,
    })).toEqual({ text: 'No change since scan #12.', state: 'NO DRIFT' });
  });

  it('prints exact counts in scan-level order', () => {
    expect(describeDifference({
      latestComparable: {
        id: 13,
        summary: {
          state: 'CHANGED',
          counts: { NEW: 1, PERSISTENT: 2, FIXED: 1, RECURRING: 0 },
        },
      },
      previousComparable: previous,
    })).toEqual({
      text: '1 new · 2 persistent · 1 fixed since scan #12.', state: 'CHANGED',
    });
  });

  it('falls back honestly when a changed scan has no counts', () => {
    expect(describeDifference({
      latestComparable: { id: 13, summary: { state: 'CHANGED', counts: {} } },
      previousComparable: previous,
    })).toEqual({ text: 'Changed since scan #12.', state: 'CHANGED' });
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/lib/difference.test.js
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement the copy**

Create `frontend/src/lib/difference.js`:

```js
import { formatDate } from './format';

const PARTS = [
  ['NEW', 'new'],
  ['PERSISTENT', 'persistent'],
  ['FIXED', 'fixed'],
  ['RECURRING', 'recurring'],
];

export function describeDifference(model) {
  const latest = model?.latestComparable;
  if (!latest) {
    return { text: 'No completed observations yet.', state: 'EMPTY' };
  }

  const state = latest.summary?.state ?? 'CHANGED';
  if (state === 'BASELINE') {
    return {
      text: `Baseline recorded ${formatDate(latest.completedAt ?? latest.startedAt)}.`,
      state: 'BASELINE',
    };
  }

  const counts = latest.summary?.counts ?? {};
  const since = model.previousComparable
    ? ` since scan #${model.previousComparable.id}`
    : '';
  const parts = PARTS
    .filter(([key]) => (counts[key] ?? 0) > 0)
    .map(([key, label]) => `${counts[key]} ${label}`);

  if (state === 'NO DRIFT' || parts.length === 0) {
    return state === 'NO DRIFT'
      ? { text: `No change${since}.`, state: 'NO DRIFT' }
      : { text: `Changed${since}.`, state: 'CHANGED' };
  }

  return { text: `${parts.join(' · ')}${since}.`, state: 'CHANGED' };
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd frontend && npm test -- --run src/lib/difference.test.js
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/difference.js frontend/src/lib/difference.test.js
git commit -m "feat(ui): exact difference line from stored summary counts"
```

---

## Task 6: Shell, empty/loading/error states, and sign-in

**Files:**
- Create: `frontend/src/components/AppShell.jsx`, `AppShell.test.jsx`
- Create: `frontend/src/components/StateBlocks.jsx`
- Create: `frontend/src/components/ErrorBoundary.jsx`
- Create: `frontend/src/components/SignIn.jsx`, `SignIn.test.jsx`
- Fill: `frontend/src/styles/shell.css`

**Interfaces:**
- `AppShell({ route, mode, onSignOut, children })`; `mode` is
  `{ kind: 'local' }` or `{ kind: 'operator', username, role }`.
- `SheetLoading({ label })`, `SheetError({ message, onRetry })`,
  `EmptySheet({ title, children, action })`, `PendingScanPanel({ scans })`.
- `ErrorBoundary` wraps the page tree.
- `SignIn({ onSubmit, error, busy })`; `onSubmit(username, password)` returns a promise.

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/AppShell.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AppShell } from './AppShell';

describe('AppShell', () => {
  it('renders typographic navigation and marks the current page', () => {
    render(
      <AppShell
        route={{ page: 'targets', targetId: null }}
        mode={{ kind: 'operator', username: 'alice', role: 'admin' }}
        onSignOut={vi.fn()}
      >
        <p>body</p>
      </AppShell>,
    );

    expect(screen.getByRole('link', { name: 'Drift' })).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Targets' }).getAttribute('aria-current'))
      .toBe('page');
    expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
    expect(screen.getByText('body')).toBeTruthy();
  });

  it('states local-research mode and offers sign-out only for an operator', async () => {
    const onSignOut = vi.fn();
    const { rerender } = render(
      <AppShell route={{ page: 'drift', targetId: 2 }} mode={{ kind: 'local' }}>
        <p>body</p>
      </AppShell>,
    );
    expect(screen.getByText('LOCAL RESEARCH')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull();

    rerender(
      <AppShell
        route={{ page: 'drift', targetId: 2 }}
        mode={{ kind: 'operator', username: 'alice', role: 'admin' }}
        onSignOut={onSignOut}
      >
        <p>body</p>
      </AppShell>,
    );
    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign out' }));
    expect(onSignOut).toHaveBeenCalledOnce();
  });
});
```

Create `frontend/src/components/SignIn.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SignIn } from './SignIn';

describe('SignIn', () => {
  it('submits trimmed credentials', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<SignIn onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('Username'), '  alice  ');
    await user.type(screen.getByLabelText('Password'), 'correct horse');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(onSubmit).toHaveBeenCalledWith('alice', 'correct horse');
  });

  it('explains a missing field before calling the API', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<SignIn onSubmit={onSubmit} />);

    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(screen.getByRole('alert').textContent).toContain('username and password');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows the API error verbatim', () => {
    render(<SignIn onSubmit={vi.fn()} error="Invalid credentials" />);
    expect(screen.getByRole('alert').textContent).toBe('Invalid credentials');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/components/AppShell.test.jsx src/components/SignIn.test.jsx
```

Expected: FAIL, modules not found.

- [ ] **Step 3: Implement the components**

Create `frontend/src/components/AppShell.jsx`:

```jsx
const DESTINATIONS = [
  ['drift', 'Drift'],
  ['targets', 'Targets'],
  ['evaluation', 'Evaluation'],
  ['settings', 'Settings'],
];

export function AppShell({ route, mode, onSignOut, children }) {
  return (
    <div className="shell">
      <header className="top-strip">
        <a className="wordmark" href="#/drift" aria-label="DriftGuard drift console">
          driftguard
        </a>
        <nav className="top-nav" aria-label="Primary">
          {DESTINATIONS.map(([page, label]) => (
            <a
              key={page}
              href={page === 'drift' ? '#/drift' : `#/${page}`}
              aria-current={route.page === page ? 'page' : undefined}
            >
              {label}
            </a>
          ))}
        </nav>
        <div className="mode">
          <span className="mode-chip mono">
            {mode.kind === 'operator' ? `OPERATOR · ${mode.username}` : 'LOCAL RESEARCH'}
          </span>
          {mode.kind === 'operator' && (
            <button type="button" className="text-button" onClick={onSignOut}>
              Sign out
            </button>
          )}
        </div>
      </header>
      <main className="console">{children}</main>
    </div>
  );
}
```

Create `frontend/src/components/StateBlocks.jsx`:

```jsx
export function SheetLoading({ label = 'Loading the record' }) {
  return (
    <div className="sheet-loading" role="status" aria-live="polite">
      <p className="engraved">{label}</p>
      {[0, 1, 2, 3].map((row) => <span key={row} className="skeleton-row" />)}
    </div>
  );
}

export function SheetError({ message, onRetry }) {
  return (
    <div className="sheet-error" role="alert">
      <p className="engraved">REQUEST FAILED</p>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="secondary-button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptySheet({ title, children, action }) {
  return (
    <section className="empty-sheet">
      <p className="engraved">NO RECORD</p>
      <h1>{title}</h1>
      {children}
      {action}
    </section>
  );
}

export function PendingScanPanel({ scans }) {
  if (!scans.length) return null;
  return (
    <div className="pending-panel" role="status" aria-live="polite">
      {scans.map((scan) => (
        <p key={scan.id}>
          Scan #{scan.id} is {scan.status}. The column becomes comparable only when the
          scan completes; until then it is not compared.
        </p>
      ))}
    </div>
  );
}
```

Create `frontend/src/components/ErrorBoundary.jsx`:

```jsx
import { Component } from 'react';

export class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="fatal" role="alert">
          <p className="engraved">CONSOLE ERROR</p>
          <h1>The console hit an unexpected error.</h1>
          <p className="mono">{this.state.error.message}</p>
          <button
            type="button"
            className="secondary-button"
            onClick={() => window.location.reload()}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

Create `frontend/src/components/SignIn.jsx`:

```jsx
import { useState } from 'react';

export function SignIn({ onSubmit, error, busy = false }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState(null);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setLocalError('Enter the operator username and password.');
      return;
    }
    setLocalError(null);
    await onSubmit(username.trim(), password);
  }

  const message = localError ?? error;

  return (
    <div className="sheet-backdrop">
      <section
        className="signin-sheet sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="signin-title"
      >
        <p className="engraved">AUTHENTICATION REQUIRED</p>
        <h1 id="signin-title">Sign in to the console</h1>
        <p>
          The API requires a bearer token. The token is kept for this browser session only.
        </p>
        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="signin-username">Username</label>
          <input
            id="signin-username"
            autoComplete="username"
            autoFocus
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
          <label htmlFor="signin-password">Password</label>
          <input
            id="signin-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {message && <p className="form-error" role="alert">{message}</p>}
          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </div>
  );
}
```

Fill `frontend/src/styles/shell.css`:

```css
.shell { min-height: 100vh; }

.top-strip {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--space-6);
  height: var(--top-height);
  padding: 0 var(--space-5);
  background: var(--paper);
  border-bottom: 2px solid var(--ink);
}

.wordmark {
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--ink);
  text-decoration: none;
}

.top-nav { display: flex; gap: var(--space-5); }
.top-nav a {
  color: var(--ink-2);
  text-decoration: none;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}
.top-nav a[aria-current='page'] { color: var(--ink); border-bottom-color: var(--signal); }

.mode {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
.mode-chip { color: var(--ink-2); letter-spacing: 0.08em; font-size: var(--step--1); }

.console { min-height: calc(100vh - var(--top-height)); }

.sheet-loading,
.sheet-error,
.empty-sheet {
  max-width: 720px;
  margin: var(--space-7) auto;
  padding: var(--space-6);
  border-top: 2px solid var(--ink);
}

.skeleton-row {
  display: block;
  height: 18px;
  margin: var(--space-3) 0;
  background: repeating-linear-gradient(
    90deg, var(--rule) 0 120px, transparent 120px 100%
  );
  opacity: 0.55;
}

.sheet-error { border-top-color: var(--risk); }
.empty-sheet h1,
.fatal h1 { font-size: var(--step-2); margin: var(--space-2) 0 var(--space-3); }

.pending-panel {
  margin: var(--space-4) 0;
  padding: var(--space-3) var(--space-4);
  border-left: 2px solid var(--pending);
  background: var(--sheet);
}

.sheet-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: var(--space-5);
  background: rgba(21, 24, 26, 0.28);
}

.signin-sheet {
  width: min(420px, 100%);
  padding: var(--space-6);
  border-top: 2px solid var(--ink);
}
.signin-sheet h1 { font-size: var(--step-2); margin: var(--space-2) 0; }
.signin-sheet form { display: grid; gap: var(--space-2); margin-top: var(--space-5); }
.signin-sheet label { font-family: var(--font-mono); font-size: var(--step--1); text-transform: uppercase; letter-spacing: 0.08em; }
.signin-sheet input { padding: 8px 10px; border: 1px solid var(--ink); background: var(--sheet); }
.signin-sheet .primary-button { margin-top: var(--space-3); }
.form-error { color: var(--risk); }
.fatal { max-width: 720px; margin: var(--space-7) auto; padding: var(--space-6); border-top: 2px solid var(--risk); }
```

- [ ] **Step 4: Run the tests and the build**

```bash
cd frontend && npm test -- --run src/components/AppShell.test.jsx src/components/SignIn.test.jsx
npm run build
```

Expected: 5 component tests PASS; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AppShell.jsx frontend/src/components/AppShell.test.jsx \
  frontend/src/components/StateBlocks.jsx frontend/src/components/ErrorBoundary.jsx \
  frontend/src/components/SignIn.jsx frontend/src/components/SignIn.test.jsx \
  frontend/src/styles/shell.css
git commit -m "feat(ui): ruled shell, explicit sheet states, and session sign-in"
```

---

## Task 7: Target form logic and registration sheet

**Files:**
- Create: `frontend/src/lib/target-form.js`, `frontend/src/lib/target-form.test.js`
- Create: `frontend/src/components/RegisterTargetSheet.jsx`,
  `frontend/src/components/RegisterTargetSheet.test.jsx`
- Fill: `frontend/src/styles/targets.css` (sheet rules; register roster follows in Task 8)

**Interfaces:**
- `emptyTargetForm()` → the blank form state.
- `parsePorts(text)` → `{ ports: number[], error: string|null }`; dedupes and sorts.
- `validateTargetForm(form)` → `{ [field]: message }`; an `authorized` target requires
  the full authorisation record, at least one approved area, and at least one port.
  A `pending` target may have empty scope; it cannot be scanned.
- `toTargetPayload(form)` → the exact `TargetCreate` body. Pending targets send `null`
  authorisation fields; discovery sends `null` wordlist when disabled.
- `RegisterTargetSheet({ onSubmit, onClose, busy, error })`.

- [ ] **Step 1: Write the failing form tests**

Create `frontend/src/lib/target-form.test.js`:

```js
import { describe, expect, it } from 'vitest';

import {
  emptyTargetForm,
  parsePorts,
  toTargetPayload,
  validateTargetForm,
} from './target-form';

function filled(overrides = {}) {
  return {
    ...emptyTargetForm(),
    name: 'eservices-lab',
    address: 'https://127.0.0.1:8443',
    ...overrides,
  };
}

describe('target form', () => {
  it('parses, dedupes, and sorts approved ports', () => {
    expect(parsePorts('8443, 8080 8443')).toEqual({ ports: [8080, 8443], error: null });
    expect(parsePorts('')).toEqual({ ports: [], error: null });
  });

  it('rejects non-numeric and out-of-range ports with specific copy', () => {
    expect(parsePorts('8443, https').error).toBe('“https” is not a port number.');
    expect(parsePorts('0').error).toBe('Port 0 is outside 1–65535.');
    expect(parsePorts('65536').error).toBe('Port 65536 is outside 1–65535.');
  });

  it('allows a pending target with no scope, because it cannot be scanned', () => {
    expect(validateTargetForm(filled())).toEqual({});
  });

  it('requires who, when, why, scope, and ports when authorisation is claimed', () => {
    const errors = validateTargetForm(filled({ authorization_status: 'authorized' }));
    expect(errors.authorized_by).toContain('who authorised');
    expect(errors.authorized_at).toContain('when');
    expect(errors.authorization_basis).toContain('basis');
    expect(errors.approved_scope).toContain('approved area');
    expect(errors.approved_ports).toContain('approved port');
  });

  it('requires a wordlist only when discovery is enabled', () => {
    expect(validateTargetForm(filled({ discovery_enabled: true })).discovery_wordlist)
      .toContain('wordlist');
    expect(validateTargetForm(filled({ discovery_enabled: false }))).toEqual({});
  });

  it('builds the exact payload and leaves pending authorisation fields null', () => {
    const payload = toTargetPayload(filled({
      approved_scope: ['tls', 'network'],
      approved_ports: [8443],
    }));
    expect(payload).toEqual({
      name: 'eservices-lab',
      address: 'https://127.0.0.1:8443',
      target_type: 'web',
      authorization_status: 'pending',
      authorized_by: null,
      authorized_at: null,
      authorization_basis: null,
      approved_scope: ['tls', 'network'],
      approved_ports: [8443],
      discovery_enabled: false,
      discovery_wordlist: null,
      status: 'active',
    });
  });

  it('sends an ISO UTC instant for an authorised target', () => {
    const payload = toTargetPayload(filled({
      authorization_status: 'authorized',
      authorized_by: 'A. Owner',
      authorized_at: '2026-11-12',
      authorization_basis: 'written approval',
      approved_scope: ['tls'],
      approved_ports: [8443],
    }));
    expect(payload.authorized_at).toBe('2026-11-12T00:00:00.000Z');
    expect(payload.authorized_by).toBe('A. Owner');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/lib/target-form.test.js
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement the form logic**

Create `frontend/src/lib/target-form.js`:

```js
export const SCOPE_OPTIONS = [
  ['tls', 'TLS'],
  ['network', 'Network'],
  ['http_api', 'API'],
];

export function emptyTargetForm() {
  return {
    name: '',
    address: '',
    target_type: 'web',
    authorization_status: 'pending',
    authorized_by: '',
    authorized_at: '',
    authorization_basis: '',
    approved_scope: [],
    approved_ports: [],
    discovery_enabled: false,
    discovery_wordlist: '',
    status: 'active',
  };
}

export function parsePorts(value) {
  const tokens = String(value ?? '').split(/[\s,]+/).filter(Boolean);
  const ports = [];
  for (const token of tokens) {
    if (!/^\d+$/.test(token)) {
      return { ports: [], error: `“${token}” is not a port number.` };
    }
    const port = Number(token);
    if (port < 1 || port > 65535) {
      return { ports: [], error: `Port ${port} is outside 1–65535.` };
    }
    ports.push(port);
  }
  return { ports: [...new Set(ports)].sort((a, b) => a - b), error: null };
}

export function validateTargetForm(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = 'Enter a target name.';
  if (!form.address.trim()) {
    errors.address = 'Enter an address, for example https://127.0.0.1:8443.';
  }
  if (!['web', 'api', 'host'].includes(form.target_type)) {
    errors.target_type = 'Choose a target type.';
  }
  if (form.authorization_status === 'authorized') {
    if (!form.authorized_by.trim()) {
      errors.authorized_by = 'Record who authorised this assessment.';
    }
    if (!form.authorized_at) {
      errors.authorized_at = 'Record when authorisation was given.';
    }
    if (!form.authorization_basis.trim()) {
      errors.authorization_basis = 'Record the basis for authorisation.';
    }
    if (form.approved_scope.length === 0) {
      errors.approved_scope = 'Select at least one approved area.';
    }
    if (form.approved_ports.length === 0) {
      errors.approved_ports = 'Add at least one approved port.';
    }
  }
  if (form.discovery_enabled && !form.discovery_wordlist.trim()) {
    errors.discovery_wordlist = 'Add a wordlist path for discovery.';
  }
  return errors;
}

export function toTargetPayload(form) {
  const authorized = form.authorization_status === 'authorized';
  return {
    name: form.name.trim(),
    address: form.address.trim(),
    target_type: form.target_type,
    authorization_status: form.authorization_status,
    authorized_by: authorized ? form.authorized_by.trim() : null,
    authorized_at: authorized
      ? new Date(`${form.authorized_at}T00:00:00Z`).toISOString()
      : null,
    authorization_basis: authorized ? form.authorization_basis.trim() : null,
    approved_scope: [...form.approved_scope],
    approved_ports: [...form.approved_ports],
    discovery_enabled: form.discovery_enabled,
    discovery_wordlist: form.discovery_enabled
      ? form.discovery_wordlist.trim()
      : null,
    status: form.status,
  };
}
```

- [ ] **Step 4: Create the registration sheet**

Create `frontend/src/components/RegisterTargetSheet.jsx` with three ruled
`<fieldset>` sections. Use controlled inputs and `aria-invalid`/`aria-describedby` for
each error. Required structure:

```jsx
import { useState } from 'react';

import {
  SCOPE_OPTIONS,
  emptyTargetForm,
  parsePorts,
  toTargetPayload,
  validateTargetForm,
} from '../lib/target-form';

export function RegisterTargetSheet({ onSubmit, onClose, busy = false, error = null }) {
  const [form, setForm] = useState(emptyTargetForm);
  const [portsText, setPortsText] = useState('');
  const [errors, setErrors] = useState({});

  const update = (patch) => setForm((current) => ({ ...current, ...patch }));

  function toggleScope(scope) {
    setForm((current) => ({
      ...current,
      approved_scope: current.approved_scope.includes(scope)
        ? current.approved_scope.filter((item) => item !== scope)
        : [...current.approved_scope, scope],
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const parsed = parsePorts(portsText);
    const candidate = { ...form, approved_ports: parsed.ports };
    const nextErrors = validateTargetForm(candidate);
    if (parsed.error) nextErrors.approved_ports = parsed.error;
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    await onSubmit(toTargetPayload(candidate));
  }

  return (
    <div className="sheet-backdrop">
      <section
        className="register-sheet sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="register-title"
      >
        <header className="register-head">
          <div>
            <p className="engraved">TARGET REGISTER</p>
            <h1 id="register-title">Register target</h1>
          </div>
          <button type="button" className="text-button" onClick={onClose} disabled={busy}>
            Close
          </button>
        </header>

        <form onSubmit={handleSubmit} noValidate>
          <fieldset>
            <legend className="engraved">Identity</legend>
            <label htmlFor="target-name">Name</label>
            <input
              id="target-name"
              value={form.name}
              onChange={(event) => update({ name: event.target.value })}
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? 'target-name-error' : undefined}
            />
            {errors.name && <p id="target-name-error" className="field-error">{errors.name}</p>}

            <label htmlFor="target-address">Address</label>
            <input
              id="target-address"
              value={form.address}
              onChange={(event) => update({ address: event.target.value })}
              aria-invalid={Boolean(errors.address)}
              aria-describedby={errors.address ? 'target-address-error' : undefined}
            />
            {errors.address && <p id="target-address-error" className="field-error">{errors.address}</p>}

            <label htmlFor="target-type">Type</label>
            <select
              id="target-type"
              value={form.target_type}
              onChange={(event) => update({ target_type: event.target.value })}
            >
              <option value="web">web</option>
              <option value="api">api</option>
              <option value="host">host</option>
            </select>
          </fieldset>

          <fieldset>
            <legend className="engraved">Authorisation</legend>
            <label>
              <input
                type="radio"
                name="authorization_status"
                value="pending"
                checked={form.authorization_status === 'pending'}
                onChange={() => update({ authorization_status: 'pending' })}
              />
              Pending — inventory only, scanning refused
            </label>
            <label>
              <input
                type="radio"
                name="authorization_status"
                value="authorized"
                checked={form.authorization_status === 'authorized'}
                onChange={() => update({ authorization_status: 'authorized' })}
              />
              Authorized
            </label>

            {form.authorization_status === 'authorized' && (
              <>
                <label htmlFor="authorized-by">Authorized by</label>
                <input
                  id="authorized-by"
                  value={form.authorized_by}
                  onChange={(event) => update({ authorized_by: event.target.value })}
                />
                {errors.authorized_by && <p className="field-error">{errors.authorized_by}</p>}

                <label htmlFor="authorized-at">Authorized at</label>
                <input
                  id="authorized-at"
                  type="date"
                  value={form.authorized_at}
                  onChange={(event) => update({ authorized_at: event.target.value })}
                />
                {errors.authorized_at && <p className="field-error">{errors.authorized_at}</p>}

                <label htmlFor="authorization-basis">Basis</label>
                <input
                  id="authorization-basis"
                  value={form.authorization_basis}
                  onChange={(event) => update({ authorization_basis: event.target.value })}
                />
                {errors.authorization_basis && <p className="field-error">{errors.authorization_basis}</p>}
              </>
            )}
          </fieldset>

          <fieldset>
            <legend className="engraved">Scope</legend>
            {SCOPE_OPTIONS.map(([value, label]) => (
              <label key={value}>
                <input
                  type="checkbox"
                  checked={form.approved_scope.includes(value)}
                  onChange={() => toggleScope(value)}
                />
                {label}
              </label>
            ))}
            {errors.approved_scope && <p className="field-error">{errors.approved_scope}</p>}

            <label htmlFor="approved-ports">Approved ports</label>
            <input
              id="approved-ports"
              placeholder="8443, 8080"
              value={portsText}
              onChange={(event) => setPortsText(event.target.value)}
            />
            {errors.approved_ports && <p className="field-error">{errors.approved_ports}</p>}

            <label>
              <input
                type="checkbox"
                checked={form.discovery_enabled}
                onChange={(event) => update({ discovery_enabled: event.target.checked })}
              />
              Discovery enabled
            </label>
            {form.discovery_enabled && (
              <>
                <label htmlFor="discovery-wordlist">Discovery wordlist</label>
                <input
                  id="discovery-wordlist"
                  value={form.discovery_wordlist}
                  onChange={(event) => update({ discovery_wordlist: event.target.value })}
                />
                {errors.discovery_wordlist && <p className="field-error">{errors.discovery_wordlist}</p>}
              </>
            )}
          </fieldset>

          {error && <p className="form-error" role="alert">{error}</p>}

          <div className="register-actions">
            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? 'Registering…' : 'Register target'}
            </button>
            <button type="button" className="secondary-button" onClick={onClose} disabled={busy}>
              Cancel
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
```

Add to `frontend/src/styles/targets.css`:

```css
.register-sheet {
  width: min(640px, 100%);
  max-height: calc(100vh - 2 * var(--space-5));
  overflow: auto;
  padding: var(--space-6);
  border-top: 2px solid var(--ink);
}
.register-head { display: flex; align-items: start; justify-content: space-between; gap: var(--space-4); }
.register-sheet h1 { font-size: var(--step-2); margin: var(--space-1) 0 var(--space-4); }
.register-sheet fieldset { border: 0; border-top: 1px solid var(--rule); margin: 0; padding: var(--space-4) 0; display: grid; gap: var(--space-2); }
.register-sheet legend { padding-top: var(--space-3); }
.register-sheet label { display: flex; align-items: center; gap: var(--space-2); }
.register-sheet fieldset > label:has(input:not([type='checkbox']):not([type='radio'])) { display: grid; gap: var(--space-1); }
.register-sheet input:not([type='checkbox']):not([type='radio']),
.register-sheet select { width: 100%; padding: 8px 10px; border: 1px solid var(--ink); background: var(--sheet); }
.register-actions { display: flex; gap: var(--space-3); padding-top: var(--space-4); border-top: 2px solid var(--ink); }
.field-error { color: var(--risk); font-size: var(--step--1); }
```

- [ ] **Step 5: Write the sheet smoke tests**

Create `frontend/src/components/RegisterTargetSheet.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RegisterTargetSheet } from './RegisterTargetSheet';

describe('RegisterTargetSheet', () => {
  it('requires a complete authorisation record before submitting', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<RegisterTargetSheet onSubmit={onSubmit} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'svc');
    await user.type(screen.getByLabelText('Address'), 'https://127.0.0.1:8443');
    await user.click(screen.getByLabelText(/Authorized$/));
    await user.click(screen.getByRole('button', { name: 'Register target' }));

    expect(screen.getByText('Record who authorised this assessment.')).toBeTruthy();
    expect(screen.getByText('Record when authorisation was given.')).toBeTruthy();
    expect(screen.getByText('Select at least one approved area.')).toBeTruthy();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits a pending target with scope and parsed ports', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RegisterTargetSheet onSubmit={onSubmit} onClose={vi.fn()} />);

    await user.type(screen.getByLabelText('Name'), 'svc');
    await user.type(screen.getByLabelText('Address'), 'https://127.0.0.1:8443');
    await user.click(screen.getByLabelText('TLS'));
    await user.type(screen.getByLabelText('Approved ports'), '8443, 8080');
    await user.click(screen.getByRole('button', { name: 'Register target' }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      name: 'svc',
      authorization_status: 'pending',
      approved_scope: ['tls'],
      approved_ports: [8080, 8443],
    }));
  });

  it('closes without submitting', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<RegisterTargetSheet onSubmit={vi.fn()} onClose={onClose} />);
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 6: Run the tests**

```bash
cd frontend && npm test -- --run src/lib/target-form.test.js \
  src/components/RegisterTargetSheet.test.jsx
```

Expected: PASS (9 tests). Fix the `getByLabelText(/Authorized$/)` query if the radio
label wraps the text differently; the accessible name must be “Authorized”.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/target-form.js frontend/src/lib/target-form.test.js \
  frontend/src/components/RegisterTargetSheet.jsx \
  frontend/src/components/RegisterTargetSheet.test.jsx frontend/src/styles/targets.css
git commit -m "feat(ui): authorisation-first target registration"
```

---

## Task 8: Targets page, target index data, and the authorisation stamp

**Files:**
- Create: `frontend/src/state/useTargets.js`
- Create: `frontend/src/components/AuthorisationStamp.jsx`,
  `AuthorisationStamp.test.jsx`
- Create: `frontend/src/pages/Targets.jsx`, `Targets.test.jsx`
- Fill: `frontend/src/styles/targets.css` (register rules added here)

**Interfaces:**
- `useTargets(client)` → `{ targets, loading, error, reload }`.
- `AuthorisationStamp({ target, compact })`; pending targets show no fabricated fields.
- `Targets({ client, targets, loading, error, onReload, onOpen, onScanQueued, onRegistered, session })`
  - `onOpen(id)`, `onScanQueued(target, scan)`, `onRegistered(target)` are callbacks into
    the app.
  - `session` is `null` in local-research mode; otherwise `{ role, ... }`.
  - `Run scan` is disabled when `!target.scannable`, when the role is not
    operator/admin, or while a request is in flight. The exact `refusal_reasons` are
    rendered, not paraphrased.
  - `Register target` requires admin in JWT mode.

- [ ] **Step 1: Write the failing stamp and page tests**

Create `frontend/src/components/AuthorisationStamp.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AuthorisationStamp } from './AuthorisationStamp';

const authorized = {
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls', 'network'],
  approved_ports: [8443, 8080],
};

describe('AuthorisationStamp', () => {
  it('shows who, when, why, and the approved scope', () => {
    render(<AuthorisationStamp target={authorized} />);
    expect(screen.getByText('A. Owner')).toBeTruthy();
    expect(screen.getByText('written approval')).toBeTruthy();
    expect(screen.getByText('12 Nov 2026')).toBeTruthy();
    expect(screen.getByText(/SCOPE TLS \/ NETWORK · PORTS 8443, 8080/)).toBeTruthy();
  });

  it('never invents a record for a pending target', () => {
    render(<AuthorisationStamp target={{ authorization_status: 'pending' }} />);
    expect(screen.getByText('PENDING — scanning refused')).toBeTruthy();
    expect(screen.getByText('No authorisation record is stored for this target.')).toBeTruthy();
    expect(screen.queryByText('A. Owner')).toBeNull();
  });
});
```

Create `frontend/src/pages/Targets.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Targets } from './Targets';

const target = {
  id: 1,
  name: 'eservices-lab',
  address: 'https://127.0.0.1:8443',
  target_type: 'web',
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls', 'network'],
  approved_ports: [8443, 8080],
  last_scan: {
    id: 4, status: 'completed',
    started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z',
  },
  scannable: true,
  refusal_reasons: [],
};

function renderPage(overrides = {}) {
  const props = {
    client: { runScan: vi.fn(), createTarget: vi.fn() },
    targets: [target],
    loading: false,
    error: null,
    onReload: vi.fn(),
    onOpen: vi.fn(),
    onScanQueued: vi.fn(),
    onRegistered: vi.fn(),
    session: null,
    ...overrides,
  };
  render(<Targets {...props} />);
  return props;
}

describe('Targets', () => {
  it('reads as a register: identity, authorisation, scope, last scan', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Targets' })).toBeTruthy();
    expect(screen.getByText('eservices-lab')).toBeTruthy();
    expect(screen.getByText('TLS / NETWORK')).toBeTruthy();
    expect(screen.getByText(/#4 · completed · 12 Nov 2026/)).toBeTruthy();
  });

  it('disables Run scan and states every refusal reason', () => {
    renderPage({
      targets: [{
        ...target,
        scannable: false,
        refusal_reasons: ['target must be active', 'approved scope is empty'],
      }],
    });
    const run = screen.getByRole('button', { name: 'Run scan' });
    expect(run.disabled).toBe(true);
    expect(screen.getByText('target must be active approved scope is empty')).toBeTruthy();
  });

  it('queues a scan and hands the settled request to the app', async () => {
    const queued = { id: 5, status: 'queued' };
    const props = renderPage();
    props.client.runScan.mockResolvedValue(queued);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Run scan' }));

    expect(props.client.runScan).toHaveBeenCalledWith(1);
    expect(props.onScanQueued).toHaveBeenCalledWith(target, queued);
  });

  it('invites registration when the register is empty', () => {
    renderPage({ targets: [] });
    expect(screen.getByText('No targets registered.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Register the first target' })).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/components/AuthorisationStamp.test.jsx \
  src/pages/Targets.test.jsx
```

Expected: FAIL, modules not found.

- [ ] **Step 3: Implement the hook, stamp, and page**

Create `frontend/src/state/useTargets.js`:

```js
import { useCallback, useEffect, useState } from 'react';

export function useTargets(client) {
  const [state, setState] = useState({ targets: [], loading: true, error: null });

  const load = useCallback(async () => {
    setState((current) => ({ ...current, loading: true, error: null }));
    try {
      const targets = await client.targets();
      setState({ targets, loading: false, error: null });
      return targets;
    } catch (error) {
      setState((current) => ({ ...current, loading: false, error }));
      return [];
    }
  }, [client]);

  useEffect(() => { load(); }, [load]);

  return { ...state, reload: load };
}
```

Create `frontend/src/components/AuthorisationStamp.jsx`:

```jsx
import { formatDate, formatPorts, formatScope } from '../lib/format';

export function AuthorisationStamp({ target, compact = false }) {
  if (target.authorization_status !== 'authorized') {
    return (
      <div className="stamp is-pending" data-compact={compact || undefined}>
        <p className="engraved">AUTHORISATION</p>
        <p className="stamp-state">PENDING — scanning refused</p>
        <p className="stamp-line">No authorisation record is stored for this target.</p>
      </div>
    );
  }

  return (
    <div className="stamp" data-compact={compact || undefined}>
      <p className="engraved">AUTHORISATION</p>
      <p className="stamp-state">AUTHORIZED</p>
      <p className="stamp-line">
        <strong>{target.authorized_by}</strong> · {formatDate(target.authorized_at)}
      </p>
      <p className="stamp-line">{target.authorization_basis}</p>
      <p className="stamp-line mono">
        SCOPE {formatScope(target.approved_scope)} · PORTS {formatPorts(target.approved_ports)}
      </p>
    </div>
  );
}
```

Create `frontend/src/pages/Targets.jsx`. Keep `TargetRow` in the same file; it is used
only here. Required behaviour:

```jsx
import { useState } from 'react';

import { AuthorisationStamp } from '../components/AuthorisationStamp';
import { RegisterTargetSheet } from '../components/RegisterTargetSheet';
import { EmptySheet, SheetError, SheetLoading } from '../components/StateBlocks';
import { formatDateTime, formatPorts, formatScope } from '../lib/format';

export function Targets({
  client, targets, loading, error, onReload, onOpen, onScanQueued, onRegistered,
  session,
}) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const canRegister = !session || session.role === 'admin';
  const canScan = !session || ['operator', 'admin'].includes(session.role);

  async function register(payload) {
    setSubmitting(true);
    setFormError(null);
    try {
      const target = await client.createTarget(payload);
      setSheetOpen(false);
      await onRegistered(target);
    } catch (requestError) {
      setFormError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function scan(target) {
    setBusyId(target.id);
    setActionError(null);
    try {
      const queued = await client.runScan(target.id);
      onScanQueued(target, queued);
    } catch (requestError) {
      setActionError(requestError.message);
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <SheetLoading label="Loading the target register" />;
  if (error) return <SheetError message={error.message} onRetry={onReload} />;

  return (
    <section className="targets-page">
      <header className="page-head">
        <div>
          <p className="engraved">TARGET REGISTER</p>
          <h1>Targets</h1>
          <p className="lede">
            A target is observed only after an explicit, attributable authorisation record.
          </p>
        </div>
        <button
          type="button"
          className="primary-button"
          disabled={!canRegister}
          title={canRegister ? undefined : 'Registration requires an admin role.'}
          onClick={() => { setFormError(null); setSheetOpen(true); }}
        >
          Register target
        </button>
      </header>

      {actionError && <p className="form-error" role="alert">{actionError}</p>}

      {targets.length === 0 ? (
        <EmptySheet
          title="No targets registered."
          action={(
            <button
              type="button"
              className="primary-button"
              disabled={!canRegister}
              onClick={() => setSheetOpen(true)}
            >
              Register the first target
            </button>
          )}
        >
          <p>Nothing has been observed. Register an authorised target to start the record.</p>
        </EmptySheet>
      ) : (
        <ul className="roster">
          {targets.map((target) => (
            <li className="roster-row" key={target.id}>
              <div className="roster-identity">
                <button type="button" className="roster-name" onClick={() => onOpen(target.id)}>
                  {target.name}
                </button>
                <span className="mono roster-address">
                  {target.address} · {target.target_type}
                </span>
              </div>

              <AuthorisationStamp target={target} compact />

              <div className="roster-field">
                <span className="engraved">SCOPE</span>
                <span>{formatScope(target.approved_scope)}</span>
                <span className="mono">{formatPorts(target.approved_ports)}</span>
              </div>

              <div className="roster-field">
                <span className="engraved">LAST SCAN</span>
                {target.last_scan ? (
                  <span>
                    #{target.last_scan.id} · {target.last_scan.status} ·{' '}
                    {formatDateTime(target.last_scan.completed_at ?? target.last_scan.started_at)}
                  </span>
                ) : <span>No scans</span>}
              </div>

              <div className="roster-actions">
                <button type="button" className="secondary-button" onClick={() => onOpen(target.id)}>
                  Open
                </button>
                <button
                  type="button"
                  className="primary-button"
                  disabled={!target.scannable || !canScan || busyId === target.id}
                  title={!canScan ? 'Scanning requires an operator role.' : undefined}
                  onClick={() => scan(target)}
                >
                  {busyId === target.id ? 'Queueing…' : 'Run scan'}
                </button>
                {!target.scannable && (
                  <p className="refusal">
                    {target.refusal_reasons.length > 0
                      ? target.refusal_reasons.join(' ')
                      : 'Scanning is not permitted for this target.'}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {sheetOpen && (
        <RegisterTargetSheet
          onSubmit={register}
          onClose={() => setSheetOpen(false)}
          busy={submitting}
          error={formError}
        />
      )}
    </section>
  );
}
```

Add the page/register/stamp rules to `frontend/src/styles/targets.css`:

```css
.targets-page { max-width: 1180px; margin: 0 auto; padding: var(--space-6) var(--space-5); }
.page-head { display: flex; align-items: end; justify-content: space-between; gap: var(--space-5); padding-bottom: var(--space-4); border-bottom: 2px solid var(--ink); }
.page-head h1 { font-size: var(--step-3); margin: var(--space-1) 0; }
.lede { max-width: 62ch; color: var(--ink-2); margin: 0; }

.roster { list-style: none; margin: var(--space-5) 0 0; padding: 0; border-top: 1px solid var(--rule); }
.roster-row { display: grid; grid-template-columns: 1.2fr 1fr 0.8fr 1fr auto; gap: var(--space-4); align-items: start; padding: var(--space-4) 0; border-bottom: 1px solid var(--rule); }
.roster-name { border: 0; background: none; padding: 0; font-size: var(--step-1); font-weight: 600; text-align: left; }
.roster-name:hover { color: var(--signal); }
.roster-address { display: block; color: var(--ink-2); font-size: var(--step--1); margin-top: var(--space-1); }
.roster-field { display: grid; gap: 2px; }
.roster-actions { display: grid; gap: var(--space-2); justify-items: start; }
.refusal { color: var(--pending); font-size: var(--step--1); margin: 0; max-width: 30ch; }

.stamp { border: 1px solid var(--ink); padding: var(--space-3); background: var(--sheet); }
.stamp.is-pending { border-color: var(--pending); }
.stamp[data-compact] { border-width: 1px; padding: var(--space-2); }
.stamp-state { font-family: var(--font-mono); font-size: var(--step--1); letter-spacing: 0.08em; margin: var(--space-1) 0; }
.stamp.is-pending .stamp-state { color: var(--pending); }
.stamp-line { margin: 2px 0; }
```

The `RegisterTargetSheet` rules from Task 7 stay in this file; keep both sections.

- [ ] **Step 4: Run the tests and build**

```bash
cd frontend && npm test -- --run src/components/AuthorisationStamp.test.jsx \
  src/pages/Targets.test.jsx
npm run build
```

Expected: 6 tests PASS; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/state/useTargets.js frontend/src/components/AuthorisationStamp.jsx \
  frontend/src/components/AuthorisationStamp.test.jsx frontend/src/pages/Targets.jsx \
  frontend/src/pages/Targets.test.jsx frontend/src/styles/targets.css
git commit -m "feat(ui): target register with attributable authorisation and honest refusals"
```

---

## Task 9: Drift grid, axis, marks, and difference line

**Files:**
- Create: `frontend/src/components/DifferenceLine.jsx`, `DifferenceLine.test.jsx`
- Create: `frontend/src/components/ScanAxis.jsx`
- Create: `frontend/src/components/ThreadRow.jsx`
- Create: `frontend/src/components/ThreadGrid.jsx`, `ThreadGrid.test.jsx`
- Fill: `frontend/src/styles/drift.css` (grid, axis, marks, target index, subject)

**Interfaces:**
- `DifferenceLine({ model })` renders the exact sentence from `describeDifference`.
- `ScanAxis({ scans })` returns `<thead>` content; column state is `BASELINE`,
  `NO DRIFT`, `CHANGED`, `NOT COMPARED`, or the raw `QUEUED`/`RUNNING` status.
- `ThreadRow({ row, scans, selected, onSelect, rowIndex, drawIndex })` is a real `<tr>`
  with a row header, one cell per scan, hidden text per mark, the current token cell,
  and the scoped draw animation (`rowIndex`/`drawIndex`, see below).
- `ThreadGrid({ model, selected, onSelect })` groups rows under `TLS`, `NETWORK`, `API`.

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/DifferenceLine.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DifferenceLine } from './DifferenceLine';

describe('DifferenceLine', () => {
  it('renders counts and the compared scan id', () => {
    render(<DifferenceLine model={{
      latestComparable: {
        id: 13,
        summary: { state: 'CHANGED', counts: { NEW: 1, PERSISTENT: 2, FIXED: 1, RECURRING: 0 } },
      },
      previousComparable: { id: 12 },
    }} />);
    expect(screen.getByText('1 new · 2 persistent · 1 fixed since scan #12.')).toBeTruthy();
  });
});
```

Create `frontend/src/components/ThreadGrid.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ThreadGrid } from './ThreadGrid';

const model = {
  scans: [
    {
      id: 1, kind: 'baseline', status: 'completed',
      startedAt: '2026-11-12T09:30:00Z', completedAt: '2026-11-12T09:31:00Z',
      summary: { state: 'BASELINE' },
    },
    {
      id: 2, kind: 'incomplete', status: 'failed',
      startedAt: '2026-11-13T09:30:00Z', completedAt: null,
      summary: { state: 'INCOMPLETE' },
    },
    {
      id: 3, kind: 'compared', status: 'completed',
      startedAt: '2026-11-14T09:30:00Z', completedAt: '2026-11-14T09:31:00Z',
      summary: { state: 'CHANGED' },
    },
  ],
  groups: [{
    key: 'TLS',
    rows: [{
      fingerprint: 't/TLS/a', title: 'Legacy TLS', resource: 't:8443', severity: 'High',
      cells: [
        { kind: 'baseline', lineLeft: false, lineRight: false },
        { kind: 'incomplete', lineLeft: false, lineRight: false },
        { kind: 'fixed', lineLeft: true, lineRight: false },
      ],
      current: { classification: 'FIXED', scanId: 3 },
    }],
  }],
};

describe('ThreadGrid', () => {
  it('renders table semantics, the not-compared column, and the current token', () => {
    render(<ThreadGrid model={model} selected={null} onSelect={vi.fn()} />);
    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: /#2/ })).toBeTruthy();
    expect(screen.getByText('NOT COMPARED')).toBeTruthy();
    expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
    expect(screen.getByText('FIXED')).toBeTruthy();
  });

  it('selects a thread on activation', async () => {
    const onSelect = vi.fn();
    render(<ThreadGrid model={model} selected={null} onSelect={onSelect} />);
    await userEvent.setup().click(screen.getByRole('rowheader', { name: /Legacy TLS/ }));
    expect(onSelect).toHaveBeenCalledWith('t/TLS/a');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/components/DifferenceLine.test.jsx \
  src/components/ThreadGrid.test.jsx
```

Expected: FAIL, modules not found.

- [ ] **Step 3: Implement the components**

Create `frontend/src/components/DifferenceLine.jsx`:

```jsx
import { describeDifference } from '../lib/difference';

export function DifferenceLine({ model }) {
  const { text, state } = describeDifference(model);
  return (
    <p
      className={`difference-line difference-${state.toLowerCase().replaceAll(' ', '-')}`}
      aria-live="polite"
    >
      {text}
    </p>
  );
}
```

Create `frontend/src/components/ScanAxis.jsx`:

```jsx
import { formatDate } from '../lib/format';

const COMPARED_LABEL = {
  BASELINE: 'BASELINE',
  'NO DRIFT': 'NO DRIFT',
  CHANGED: 'CHANGED',
};

export function columnState(scan) {
  if (scan.kind === 'baseline') return 'BASELINE';
  if (scan.kind === 'compared') return COMPARED_LABEL[scan.summary?.state] ?? 'CHANGED';
  if (scan.kind === 'incomplete') return 'NOT COMPARED';
  return String(scan.status).toUpperCase();
}

export function ScanAxis({ scans }) {
  return (
    <thead>
      <tr>
        <th scope="col" className="axis-finding">Finding</th>
        {scans.map((scan) => (
          <th
            key={scan.id}
            scope="col"
            className={`axis-scan kind-${scan.kind}`}
          >
            <span className="axis-id mono">#{scan.id}</span>
            <span className="axis-date mono">
              {formatDate(scan.completedAt ?? scan.startedAt)}
            </span>
            <span className="axis-state mono">{columnState(scan)}</span>
          </th>
        ))}
        <th scope="col" className="axis-current">Current</th>
      </tr>
    </thead>
  );
}
```

Create `frontend/src/components/ThreadRow.jsx`:

```jsx
export const MARK_TEXT = {
  baseline: 'baseline observation',
  present: 'present',
  new: 'new',
  recurring: 'recurring',
  fixed: 'fixed',
  absent: 'known absent',
  never: 'not observed',
  incomplete: 'not compared',
  pending: 'scan pending',
};

export function ThreadRow({ row, scans, selected, onSelect, rowIndex = 0, drawIndex = -1 }) {
  return (
    <tr
      className={`thread-row${selected ? ' is-selected' : ''}`}
      tabIndex={0}
      aria-selected={selected}
      onMouseEnter={() => onSelect(row.fingerprint)}
      onFocus={() => onSelect(row.fingerprint)}
      onClick={() => onSelect(row.fingerprint)}
    >
      <th scope="row" className="thread-title">
        <span>{row.title}</span>
        <span className="mono thread-resource">{row.resource}</span>
      </th>
      {row.cells.map((cell, index) => (
        <td
          key={scans[index].id}
          className={`thread-cell kind-${cell.kind}${index === drawIndex ? ' is-drawing' : ''}`}
          style={index === drawIndex
            ? { animationDelay: `${Math.min(rowIndex, 8) * 20}ms` }
            : undefined}
        >
          {cell.lineLeft && <span className="thread-line line-left" aria-hidden="true" />}
          {cell.lineRight && <span className="thread-line line-right" aria-hidden="true" />}
          {!['incomplete', 'pending', 'absent'].includes(cell.kind) && (
            <span className={`mark mark-${cell.kind}`} aria-hidden="true" />
          )}
          {cell.kind === 'absent' && <span className="mark mark-absent" aria-hidden="true" />}
          <span className="visually-hidden">{MARK_TEXT[cell.kind]}</span>
        </td>
      ))}
      <td className={`thread-current current-${row.current.classification.toLowerCase().replaceAll(' ', '-')}`}>
        <span className="mono">{row.current.classification}</span>
        {['Critical', 'High'].includes(row.severity) && (
          <span className="severity mono">{row.severity}</span>
        )}
      </td>
    </tr>
  );
}
```

Create `frontend/src/components/ThreadGrid.jsx`:

```jsx
import { Fragment } from 'react';

import { ScanAxis } from './ScanAxis';
import { ThreadRow } from './ThreadRow';

export function ThreadGrid({ model, selected, onSelect }) {
  const drawIndex = model.scans.reduce(
    (found, scan, index) => (scan.comparable ? index : found),
    -1,
  );
  let rowIndex = 0;

  return (
    <div className="thread-wrap">
      <table className="thread-grid">
        <caption className="visually-hidden">
          Evidence threads across {model.scans.length} scans. Columns marked not compared
          are excluded from the comparison.
        </caption>
        <ScanAxis scans={model.scans} />
        <tbody>
          {model.groups.map((group) => (
            <Fragment key={group.key}>
              <tr className="thread-group">
                <th scope="colgroup" colSpan={model.scans.length + 2}>{group.key}</th>
              </tr>
              {group.rows.map((row) => {
                const index = rowIndex;
                rowIndex += 1;
                return (
                  <ThreadRow
                    key={row.fingerprint}
                    row={row}
                    scans={model.scans}
                    selected={selected === row.fingerprint}
                    onSelect={onSelect}
                    rowIndex={index}
                    drawIndex={drawIndex}
                  />
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Fill the grid styles**

Add to `frontend/src/styles/drift.css`:

```css
.thread-wrap { overflow-x: auto; border-top: 1px solid var(--rule); }

.thread-grid {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: var(--step-0);
}

.thread-grid th,
.thread-grid td { border-bottom: 1px solid var(--rule); }

.axis-finding { width: 220px; text-align: left; padding: var(--space-2) 0; }
.axis-scan {
  width: 92px;
  padding: var(--space-2) 4px;
  border-left: 1px solid var(--rule);
  vertical-align: bottom;
  font-weight: 400;
}
.axis-scan span { display: block; }
.axis-id { font-size: var(--step-0); color: var(--ink); }
.axis-date { font-size: 10px; color: var(--ink-2); }
.axis-state { font-size: 10px; letter-spacing: 0.06em; margin-top: 2px; }
.axis-scan.kind-baseline { background: var(--sheet); }
.axis-scan.kind-incomplete {
  background: repeating-linear-gradient(135deg, transparent 0 6px, rgba(199, 195, 183, 0.55) 6px 7px);
}
.axis-scan.kind-pending { border-bottom: 1px dashed var(--pending); }
.axis-current { width: 128px; text-align: right; padding-right: var(--space-3); }

.thread-group th {
  padding: var(--space-3) 0 var(--space-1);
  text-align: left;
  font-family: var(--font-mono);
  font-size: var(--step--1);
  font-weight: 500;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--ink);
}

.thread-row { height: var(--row-height); }
.thread-row:hover,
.thread-row:focus-visible,
.thread-row.is-selected { background: var(--sheet); }
.thread-row:focus-visible { outline: 2px solid var(--signal); outline-offset: -2px; }

.thread-title { text-align: left; padding: 4px var(--space-2) 4px 0; font-weight: 400; }
.thread-title > span { display: block; }
.thread-resource { color: var(--ink-2); font-size: var(--step--1); }

.thread-cell { position: relative; height: var(--row-height); padding: 0; text-align: center; }
.thread-cell.kind-incomplete {
  background: repeating-linear-gradient(135deg, transparent 0 6px, rgba(199, 195, 183, 0.55) 6px 7px);
}
.thread-cell.kind-incomplete::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  border-top: 1px dotted var(--ink-2);
}
.thread-cell.kind-pending { border-left: 1px dashed var(--pending); }

.thread-line {
  position: absolute;
  top: 50%;
  height: 1px;
  background: var(--ink);
}
.thread-line.line-left { left: 0; width: 50%; }
.thread-line.line-right { right: 0; width: 50%; }

.mark { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); }
.mark-baseline { width: 7px; height: 7px; background: var(--ink); }
.mark-new { width: 8px; height: 8px; background: var(--signal); }
.mark-recurring { width: 8px; height: 8px; background: var(--signal); transform: translate(-50%, -50%) rotate(45deg); }
.mark-fixed { width: 9px; height: 9px; border: 1.5px solid var(--verified); border-radius: 50%; background: var(--paper); }
.mark-absent { width: 12px; height: 1px; background: var(--rule); }

.thread-current { text-align: right; padding-right: var(--space-3); font-size: var(--step--1); }
.thread-current .severity { display: block; color: var(--risk); }
.current-fixed { color: var(--verified); }
.current-new,
.current-recurring { color: var(--signal); }
```

The current token must remain readable in monochrome: the token text is always present;
colour is secondary. Check contrast for `--verified` and `--signal` on `--paper` before
merge.

- [ ] **Step 5: Run the tests**

```bash
cd frontend && npm test -- --run src/components/DifferenceLine.test.jsx \
  src/components/ThreadGrid.test.jsx
```

Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/DifferenceLine.jsx frontend/src/components/DifferenceLine.test.jsx \
  frontend/src/components/ScanAxis.jsx frontend/src/components/ThreadRow.jsx \
  frontend/src/components/ThreadGrid.jsx frontend/src/components/ThreadGrid.test.jsx \
  frontend/src/styles/drift.css
git commit -m "feat(ui): calibrated scan axis and the evidence thread grid"
```

---

## Task 10: Redacted export and the detail rail

**Files:**
- Create: `frontend/src/lib/csv.js`, `frontend/src/lib/csv.test.js`
- Create: `frontend/src/components/EvidenceDetail.jsx`,
  `EvidenceDetail.test.jsx`
- Fill: `frontend/src/styles/drift.css` (detail rail rules)

**Interfaces:**
- `toCsv(rows)` → RFC-4180-style CSV with a fixed header and CRLF line endings.
- `scanCsvFilename(targetName, scanId)` → `driftguard-<slug>-scan-<id>-redacted.csv`.
- `redactedRecordFor(records, fingerprint)` → record or `null`.
- `downloadText(filename, text)` (DOM download; not unit-tested).
- `EvidenceDetail({ row, scans, client, targetName, copy, download })`
  - shows metadata and the raw `details` block marked `LOCAL DETAIL · NOT REDACTED`;
  - `Copy redacted record` fetches `/api/scans/{lastObservedScan}/evidence/redacted`,
    finds the fingerprint, and copies pretty JSON;
  - `Export scan #N` downloads that scan's redacted evidence as CSV;
  - status text uses `role="status"`; errors use `role="alert"`.

- [ ] **Step 1: Write the failing export tests**

Create `frontend/src/lib/csv.test.js`:

```js
import { describe, expect, it } from 'vitest';

import { redactedRecordFor, scanCsvFilename, toCsv } from './csv';

describe('redacted CSV', () => {
  it('writes a fixed header and escapes commas, quotes, and objects', () => {
    const csv = toCsv([{
      fingerprint: 'a', category: 'TLS', title: 'x,y', severity: 'High',
      resource: 'r', observed_at: '2026-11-12T09:30:00Z', details: { a: 1 },
    }]);
    const lines = csv.split('\r\n');
    expect(lines[0]).toBe('fingerprint,category,title,severity,resource,observed_at,details');
    expect(lines[1]).toBe('a,TLS,"x,y",High,r,2026-11-12T09:30:00Z,"{""a"":1}"');
    expect(csv.endsWith('\r\n')).toBe(true);
  });

  it('quotes embedded newlines and doubles embedded quotes', () => {
    const csv = toCsv([{ fingerprint: 'a', title: 'line one\nline "two"' }]);
    expect(csv).toContain('"line one\nline ""two"""');
  });

  it('builds a filesystem-safe filename from the target name', () => {
    expect(scanCsvFilename('eservices lab / 127.0.0.1', 12))
      .toBe('driftguard-eservices-lab-127-0-0-1-scan-12-redacted.csv');
    expect(scanCsvFilename('', 3)).toBe('driftguard-target-scan-3-redacted.csv');
  });

  it('finds the redacted record for one fingerprint', () => {
    const records = [{ fingerprint: 'a' }, { fingerprint: 'b' }];
    expect(redactedRecordFor(records, 'b')).toEqual({ fingerprint: 'b' });
    expect(redactedRecordFor(records, 'missing')).toBeNull();
  });
});
```

Create `frontend/src/components/EvidenceDetail.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EvidenceDetail } from './EvidenceDetail';

const row = {
  fingerprint: 't/TLS/a',
  title: 'Legacy TLS',
  resource: 't:8443',
  severity: 'High',
  current: { classification: 'PERSISTENT', scanId: 2 },
  cells: [{ kind: 'baseline' }, { kind: 'present' }],
  detail: { cipher: 'RC4' },
  observedAt: '2026-11-12T09:30:00Z',
};

const scans = [
  {
    id: 1, startedAt: '2026-11-12T09:30:00Z',
    completedAt: '2026-11-12T09:31:00Z', summary: { state: 'BASELINE' },
  },
  {
    id: 2, startedAt: '2026-11-13T09:30:00Z',
    completedAt: '2026-11-13T09:31:00Z', summary: { state: 'CHANGED' },
  },
];

function renderDetail(overrides = {}) {
  const props = {
    row,
    scans,
    client: {
      redactedEvidence: vi.fn().mockResolvedValue([
        { fingerprint: 't/TLS/a', title: 'Legacy TLS' },
      ]),
    },
    targetName: 'svc',
    copy: vi.fn().mockResolvedValue(undefined),
    download: vi.fn(),
    ...overrides,
  };
  render(<EvidenceDetail {...props} />);
  return props;
}

describe('EvidenceDetail', () => {
  it('marks raw local detail and copies only the redacted record', async () => {
    const props = renderDetail();
    expect(screen.getByText('LOCAL DETAIL · NOT REDACTED')).toBeTruthy();
    expect(screen.getByText(/RC4/)).toBeTruthy();

    await userEvent.setup().click(
      screen.getByRole('button', { name: /Copy redacted record/ }),
    );

    expect(props.client.redactedEvidence).toHaveBeenCalledWith(2);
    expect(props.copy).toHaveBeenCalledWith(
      expect.stringContaining('"fingerprint": "t/TLS/a"'),
    );
    expect(screen.getByRole('status').textContent).toContain('Redacted record copied.');
  });

  it('downloads the last observed scan as redacted CSV', async () => {
    const props = renderDetail();
    await userEvent.setup().click(
      screen.getByRole('button', { name: /Export scan #2/ }),
    );
    expect(props.download).toHaveBeenCalledWith(
      'driftguard-svc-scan-2-redacted.csv',
      expect.stringContaining('fingerprint'),
    );
  });

  it('reports a missing redacted record instead of exporting silently', async () => {
    const props = renderDetail({
      client: { redactedEvidence: vi.fn().mockResolvedValue([]) },
    });
    await userEvent.setup().click(
      screen.getByRole('button', { name: /Copy redacted record/ }),
    );
    expect(props.copy).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toContain('No redacted record');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/lib/csv.test.js \
  src/components/EvidenceDetail.test.jsx
```

Expected: FAIL, modules not found.

- [ ] **Step 3: Implement CSV and download**

Create `frontend/src/lib/csv.js`:

```js
export const CSV_COLUMNS = [
  'fingerprint', 'category', 'title', 'severity', 'resource', 'observed_at', 'details',
];

function cell(value) {
  const text = value == null
    ? ''
    : typeof value === 'string' ? value : JSON.stringify(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function toCsv(rows) {
  const lines = [CSV_COLUMNS.join(',')];
  for (const row of rows) {
    lines.push(CSV_COLUMNS.map((column) => cell(row[column])).join(','));
  }
  return `${lines.join('\r\n')}\r\n`;
}

export function safeFilename(name, fallback = 'target') {
  const slug = String(name ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || fallback;
}

export function scanCsvFilename(targetName, scanId) {
  return `driftguard-${safeFilename(targetName)}-scan-${scanId}-redacted.csv`;
}

export function redactedRecordFor(records, fingerprint) {
  return records.find((record) => record.fingerprint === fingerprint) ?? null;
}

export function downloadText(filename, text, mime = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 4: Implement the detail rail**

Create `frontend/src/components/EvidenceDetail.jsx`:

```jsx
import { useState } from 'react';

import {
  downloadText, redactedRecordFor, scanCsvFilename, toCsv,
} from '../lib/csv';
import { formatDateTime } from '../lib/format';

const clipboardCopy = async (text) => {
  if (!navigator.clipboard?.writeText) {
    throw new Error('Clipboard access is not available in this browser.');
  }
  await navigator.clipboard.writeText(text);
};

function lastObservedIndex(row) {
  for (let index = row.cells.length - 1; index >= 0; index -= 1) {
    if (['baseline', 'present', 'new', 'recurring'].includes(row.cells[index].kind)) {
      return index;
    }
  }
  return -1;
}

export function EvidenceDetail({
  row, scans, client, targetName,
  copy = clipboardCopy,
  download = downloadText,
}) {
  const [busy, setBusy] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const observedIndex = lastObservedIndex(row);
  const scan = observedIndex >= 0 ? scans[observedIndex] : null;

  async function withRecords(action, label) {
    if (!scan) {
      setError('This fingerprint has no completed observation in the current window.');
      return;
    }
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      const records = await client.redactedEvidence(scan.id);
      const record = redactedRecordFor(records, row.fingerprint);
      if (!record) {
        setError(`No redacted record was returned for this fingerprint in scan #${scan.id}.`);
        return;
      }
      await action(record, records);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(null);
    }
  }

  const copyRecord = () => withRecords(
    (record) => copy(JSON.stringify(record, null, 2))
      .then(() => setMessage('Redacted record copied.')),
    'copy',
  );

  const exportScan = () => withRecords(
    (_record, records) => {
      download(scanCsvFilename(targetName, scan.id), toCsv(records));
      setMessage(`Redacted evidence for scan #${scan.id} downloaded.`);
    },
    'export',
  );

  return (
    <aside className="detail-rail" aria-labelledby="detail-title">
      <div>
        <p className="engraved">SELECTED FINGERPRINT</p>
        <h2 id="detail-title">{row.title}</h2>
        <dl>
          <div><dt>Resource</dt><dd className="mono">{row.resource}</dd></div>
          <div><dt>Severity</dt><dd>{row.severity}</dd></div>
          <div><dt>Fingerprint</dt><dd className="mono">{row.fingerprint}</dd></div>
          <div>
            <dt>Last observed</dt>
            <dd>
              {scan
                ? `#${scan.id} · ${formatDateTime(scan.completedAt ?? scan.startedAt)}`
                : 'Never in this window'}
            </dd>
          </div>
          <div><dt>Current</dt><dd className="mono">{row.current.classification}</dd></div>
        </dl>
        <div className="detail-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={copyRecord}
            disabled={busy !== null || !scan}
          >
            {busy === 'copy' ? 'Copying…' : 'Copy redacted record'}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={exportScan}
            disabled={busy !== null || !scan}
          >
            {busy === 'export' ? 'Exporting…' : `Export scan #${scan?.id ?? '—'}`}
          </button>
        </div>
        <p className="detail-note">
          Export and copy use the redacted evidence endpoint. The token map never leaves
          the backend process.
        </p>
        {message && <p className="detail-status" role="status">{message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </div>

      <div className="detail-local">
        <p className="engraved">LOCAL DETAIL · NOT REDACTED</p>
        <pre>{JSON.stringify(row.detail ?? {}, null, 2)}</pre>
      </div>
    </aside>
  );
}
```

Add to `frontend/src/styles/drift.css`:

```css
.detail-rail {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 2px solid var(--ink);
}
.detail-rail h2 { margin: var(--space-1) 0 var(--space-3); font-size: var(--step-2); }
.detail-rail dl { display: grid; gap: var(--space-2); margin: 0 0 var(--space-4); }
.detail-rail dt {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-2);
}
.detail-rail dd { margin: 0; }
.detail-local pre {
  max-height: 260px;
  overflow: auto;
  margin: var(--space-2) 0 0;
  padding: var(--space-3);
  background: var(--sheet);
  border: 1px solid var(--rule);
  font-family: var(--font-mono);
  font-size: var(--step--1);
  white-space: pre-wrap;
  word-break: break-word;
}
.detail-actions { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.detail-note { color: var(--ink-2); font-size: var(--step--1); max-width: 46ch; }
.detail-status { color: var(--verified); }
```

- [ ] **Step 5: Run the tests**

```bash
cd frontend && npm test -- --run src/lib/csv.test.js \
  src/components/EvidenceDetail.test.jsx
```

Expected: PASS (7 tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/csv.js frontend/src/lib/csv.test.js \
  frontend/src/components/EvidenceDetail.jsx \
  frontend/src/components/EvidenceDetail.test.jsx frontend/src/styles/drift.css
git commit -m "feat(ui): redacted CSV export and local-only evidence detail"
```

---

## Task 11: History loading, polling, and the target index

**Files:**
- Create: `frontend/src/state/useHistory.js`, `useHistory.test.js`
- Create: `frontend/src/components/TargetIndex.jsx`, `TargetIndex.test.jsx`
- Fill: `frontend/src/styles/drift.css` (drift layout and index rules)

**Interfaces:**
- `useHistory(client, targetId, { pollMs = 2000 })` →
  `{ history, loading, error, reload }`.
  - Aborts the previous request when `targetId` changes or the component unmounts.
  - Polls quietly every `pollMs` while any returned scan is `queued` or `running`;
    stops when no scan is pending. `reload()` is a quiet refresh.
- `TargetIndex({ targets, selectedId, onSelect })`; each row is a link to
  `#/drift/{id}`, with a filled/hollow authorisation mark, name, mono address, and last
  scan status/date. The selected row carries `aria-current="page"`.

- [ ] **Step 1: Write the failing hook and index tests**

Create `frontend/src/state/useHistory.test.js`:

```jsx
import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { useHistory } from './useHistory';

const payload = { target: { id: 1 }, scans: [], fingerprints: {} };

describe('useHistory', () => {
  it('loads one history page and clears the loading state', async () => {
    const client = { history: vi.fn().mockResolvedValue(payload) };
    const { result } = renderHook(() => useHistory(client, 1));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(client.history).toHaveBeenCalledWith(1, { signal: expect.any(AbortSignal) });
    expect(result.current.history).toEqual(payload);
  });

  it('aborts the in-flight request when the subject changes', () => {
    const signals = [];
    const client = {
      history: vi.fn().mockImplementation((_id, { signal }) => {
        signals.push(signal);
        return new Promise(() => {});
      }),
    };
    const { rerender } = renderHook(({ id }) => useHistory(client, id), {
      initialProps: { id: 1 },
    });
    rerender({ id: 2 });
    expect(signals[0].aborted).toBe(true);
    expect(client.history).toHaveBeenLastCalledWith(2, { signal: expect.any(AbortSignal) });
  });

  it('exposes a quiet reload', async () => {
    const client = { history: vi.fn().mockResolvedValue(payload) };
    const { result } = renderHook(() => useHistory(client, 1));
    await waitFor(() => expect(result.current.loading).toBe(false));
    await result.current.reload();
    expect(client.history).toHaveBeenCalledTimes(2);
  });
});
```

Create `frontend/src/components/TargetIndex.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TargetIndex } from './TargetIndex';

const targets = [
  {
    id: 1, name: 'eservices-lab', address: 'https://127.0.0.1:8443',
    authorization_status: 'authorized',
    last_scan: { id: 4, status: 'completed', started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z' },
  },
  {
    id: 2, name: 'civic', address: 'https://127.0.0.1:8445',
    authorization_status: 'pending', last_scan: null,
  },
];

describe('TargetIndex', () => {
  it('marks the selected subject and reports the last scan attempt', () => {
    render(<TargetIndex targets={targets} selectedId={1} onSelect={vi.fn()} />);
    const selected = screen.getByRole('link', { name: /eservices-lab/ });
    expect(selected.getAttribute('aria-current')).toBe('page');
    expect(screen.getByText(/Last scan #4 · completed · 12 Nov 2026/)).toBeTruthy();
    expect(screen.getByText('No scans')).toBeTruthy();
  });

  it('selects a target without a page reload', async () => {
    const onSelect = vi.fn();
    render(<TargetIndex targets={targets} selectedId={1} onSelect={onSelect} />);
    await userEvent.setup().click(screen.getByRole('link', { name: /civic/ }));
    expect(onSelect).toHaveBeenCalledWith(2);
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/state/useHistory.test.js \
  src/components/TargetIndex.test.jsx
```

Expected: FAIL, modules not found.

- [ ] **Step 3: Implement the hook and index**

Create `frontend/src/state/useHistory.js`:

```js
import { useCallback, useEffect, useRef, useState } from 'react';

export function useHistory(client, targetId, { pollMs = 2000 } = {}) {
  const [state, setState] = useState({ history: null, loading: true, error: null });
  const controllerRef = useRef(null);
  const timerRef = useRef(null);
  const aliveRef = useRef(false);

  const load = useCallback(async ({ quiet = false } = {}) => {
    if (targetId == null) return null;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    if (!quiet) {
      setState((current) => ({ ...current, loading: true, error: null }));
    }
    try {
      const history = await client.history(targetId, { signal: controller.signal });
      if (!aliveRef.current) return history;
      setState({ history, loading: false, error: null });
      return history;
    } catch (error) {
      if (error.name === 'AbortError' || !aliveRef.current) return null;
      setState((current) => ({
        history: quiet ? current.history : null,
        loading: false,
        error,
      }));
      return null;
    }
  }, [client, targetId]);

  useEffect(() => {
    aliveRef.current = true;
    setState({ history: null, loading: true, error: null });
    load();
    return () => {
      aliveRef.current = false;
      controllerRef.current?.abort();
      clearTimeout(timerRef.current);
    };
  }, [load]);

  useEffect(() => {
    const pending = state.history?.scans?.some(({ scan }) =>
      scan.status === 'queued' || scan.status === 'running');
    clearTimeout(timerRef.current);
    if (!pending) return undefined;
    timerRef.current = setTimeout(() => load({ quiet: true }), pollMs);
    return () => clearTimeout(timerRef.current);
  }, [state.history, load, pollMs]);

  return { ...state, reload: () => load({ quiet: true }) };
}
```

Create `frontend/src/components/TargetIndex.jsx`:

```jsx
import { formatDate } from '../lib/format';

export function TargetIndex({ targets, selectedId, onSelect }) {
  return (
    <nav className="target-index" aria-label="Targets">
      <p className="engraved">TARGETS</p>
      <ul>
        {targets.map((target) => {
          const selected = target.id === selectedId;
          return (
            <li key={target.id}>
              <a
                href={`#/drift/${target.id}`}
                className={selected ? 'is-selected' : undefined}
                aria-current={selected ? 'page' : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  onSelect(target.id);
                }}
              >
                <span
                  className="index-mark"
                  data-authorized={target.authorization_status === 'authorized'}
                  aria-hidden="true"
                />
                <span className="index-name">{target.name}</span>
                <span className="mono index-address">{target.address}</span>
                <span className="index-last">
                  {target.last_scan
                    ? `Last scan #${target.last_scan.id} · ${target.last_scan.status} · ${formatDate(target.last_scan.completed_at ?? target.last_scan.started_at)}`
                    : 'No scans'}
                </span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
```

Add to `frontend/src/styles/drift.css`:

```css
.drift-page {
  display: grid;
  grid-template-columns: var(--index-width) minmax(0, 1fr);
  min-height: calc(100vh - var(--top-height));
}

.target-index {
  padding: var(--space-5) var(--space-3);
  border-right: 1px solid var(--rule);
}
.target-index ul { list-style: none; margin: var(--space-3) 0 0; padding: 0; }
.target-index a {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 2px var(--space-2);
  padding: var(--space-2);
  border-left: 2px solid transparent;
  color: var(--ink);
  text-decoration: none;
}
.target-index a:hover { background: var(--sheet); }
.target-index a.is-selected { background: var(--sheet); border-left-color: var(--signal); }
.index-mark {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border: 1px solid var(--ink);
  border-radius: 50%;
}
.index-mark[data-authorized='true'] { background: var(--ink); }
.index-name { font-weight: 500; overflow-wrap: anywhere; }
.index-address,
.index-last {
  grid-column: 2;
  color: var(--ink-2);
  font-size: 10px;
  overflow-wrap: anywhere;
}

.drift-subject { min-width: 0; padding: var(--space-5); }
.subject {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: var(--space-5);
  padding-bottom: var(--space-3);
  border-bottom: 2px solid var(--ink);
}
.subject h1 { font-size: var(--step-3); margin: var(--space-1) 0; }
.subject-meta { color: var(--ink-2); overflow-wrap: anywhere; }
.subject-actions { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.drift-subject > .stamp { margin: var(--space-4) 0; }
.difference-line { font-size: var(--step-1); margin: var(--space-5) 0 var(--space-3); font-variant-numeric: tabular-nums; }
.detail-prompt {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 2px solid var(--ink);
  color: var(--ink-2);
}
```

- [ ] **Step 4: Run the tests**

```bash
cd frontend && npm test -- --run src/state/useHistory.test.js \
  src/components/TargetIndex.test.jsx
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/state/useHistory.js frontend/src/state/useHistory.test.js \
  frontend/src/components/TargetIndex.jsx frontend/src/components/TargetIndex.test.jsx \
  frontend/src/styles/drift.css
git commit -m "feat(ui): single-history loading, abort on subject switch, and the target index"
```

---

## Task 12: The Drift page

**Files:**
- Create: `frontend/src/pages/Drift.jsx`, `Drift.test.jsx`

**Interfaces:**
- `Drift({ client, targets, targetsLoading, targetsError, targetId, onSelectTarget,
  onOpenTargets, session })`.
- Loads history through `useHistory`; never fetches evidence per scan.
- Renders `TargetIndex` plus subject header, `AuthorisationStamp`, `DifferenceLine`,
  `PendingScanPanel`, `ThreadGrid`, and `EvidenceDetail` for the selected row.
- `Run scan` is disabled with the exact refusal reason when the target is not scannable
  or the role cannot scan. A queued scan reloads the history once, then polling takes
  over.
- No comparable scans: `No observations yet.Run a baseline to start the record.` with a
  scan action. No grid and no invented counts.

- [ ] **Step 1: Write the failing page tests**

Create `frontend/src/pages/Drift.test.jsx`:

```jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { Drift } from './Drift';

const target = {
  id: 1,
  name: 'eservices-lab',
  address: 'https://127.0.0.1:8443',
  target_type: 'web',
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls', 'network'],
  approved_ports: [8443, 8080],
  last_scan: null,
  scannable: true,
  refusal_reasons: [],
};

const history = {
  target,
  scans: [{
    scan: {
      id: 1, target_id: 1, status: 'completed',
      started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z',
      is_baseline: true, label: null, error: null,
    },
    comparable: true,
    evidence: [{
      id: 1, scan_id: 1, fingerprint: 'eservices-lab/TLS/a', category: 'TLS',
      title: 'Legacy TLS', severity: 'High', resource: '127.0.0.1:8443',
      details: { cipher: 'RC4' }, observed_at: '2026-11-12T09:30:00Z',
    }],
    drift: [],
    summary: { state: 'BASELINE', counts: { NEW: 0, PERSISTENT: 0, FIXED: 0, RECURRING: 0 } },
  }],
  fingerprints: {
    'eservices-lab/TLS/a': {
      title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: '127.0.0.1:8443',
    },
  },
};

function renderDrift(overrides = {}) {
  const props = {
    client: {
      history: vi.fn().mockResolvedValue(history),
      runScan: vi.fn().mockResolvedValue({ id: 2, status: 'queued' }),
    },
    targets: [target],
    targetsLoading: false,
    targetsError: null,
    targetId: 1,
    onSelectTarget: vi.fn(),
    onOpenTargets: vi.fn(),
    session: null,
    ...overrides,
  };
  render(<Drift {...props} />);
  return props;
}

describe('Drift', () => {
  it('reads the subject, authorisation, baseline, and thread from stored data', async () => {
    renderDrift();
    expect(await screen.findByRole('heading', { name: 'eservices-lab' })).toBeTruthy();
    expect(screen.getByText('A. Owner')).toBeTruthy();
    expect(screen.getByText('Baseline recorded 12 Nov 2026.')).toBeTruthy();
    expect(screen.getByRole('rowheader', { name: /Legacy TLS/ })).toBeTruthy();
  });

  it('queues a scan and reloads once', async () => {
    const props = renderDrift();
    await screen.findByRole('heading', { name: 'eservices-lab' });

    await userEvent.setup().click(screen.getByRole('button', { name: 'Run scan' }));

    expect(props.client.runScan).toHaveBeenCalledWith(1);
    await waitFor(() => expect(props.client.history).toHaveBeenCalledTimes(2));
    expect(screen.getByRole('status').textContent).toContain('Scan #2 queued');
  });

  it('refuses to scan a pending target and states why', async () => {
    const pending = {
      ...target,
      authorization_status: 'pending',
      authorized_by: null,
      authorized_at: null,
      authorization_basis: null,
      approved_scope: [],
      approved_ports: [],
      scannable: false,
      refusal_reasons: ['target must be active', 'target must be explicitly authorized'],
    };
    const props = renderDrift({
      targetId: 2,
      targets: [pending],
      client: {
        history: vi.fn().mockResolvedValue({ target: pending, scans: [], fingerprints: {} }),
        runScan: vi.fn(),
      },
    });
    await screen.findByRole('heading', { name: 'eservices-lab' });
    const run = screen.getByRole('button', { name: 'Run scan' });
    expect(run.disabled).toBe(true);
    expect(screen.getByText('target must be active target must be explicitly authorized'))
      .toBeTruthy();
    expect(props.client.runScan).not.toHaveBeenCalled();
  });

  it('shows an explicit empty observation state instead of a grid', async () => {
    renderDrift({
      client: {
        history: vi.fn().mockResolvedValue({ target, scans: [], fingerprints: {} }),
        runScan: vi.fn(),
      },
    });
    expect(await screen.findByText('No observations yet.')).toBeTruthy();
    expect(screen.getByText(/Run a baseline to start the record/)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/pages/Drift.test.jsx
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement the page**

Create `frontend/src/pages/Drift.jsx`:

```jsx
import { useEffect, useMemo, useState } from 'react';

import { AuthorisationStamp } from '../components/AuthorisationStamp';
import { DifferenceLine } from '../components/DifferenceLine';
import { EvidenceDetail } from '../components/EvidenceDetail';
import {
  EmptySheet, PendingScanPanel, SheetError, SheetLoading,
} from '../components/StateBlocks';
import { TargetIndex } from '../components/TargetIndex';
import { ThreadGrid } from '../components/ThreadGrid';
import { buildThreadModel } from '../lib/threads';
import { useHistory } from '../state/useHistory';

export function Drift({
  client, targets, targetsLoading, targetsError, targetId, onSelectTarget,
  onOpenTargets, session,
}) {
  const { history, loading, error, reload } = useHistory(client, targetId);
  const [selectedFingerprint, setSelectedFingerprint] = useState(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [scanMessage, setScanMessage] = useState(null);
  const [scanError, setScanError] = useState(null);

  const model = useMemo(() => (history ? buildThreadModel(history) : null), [history]);
  const target = history?.target ?? targets.find((entry) => entry.id === targetId) ?? null;
  const selectedRow = model?.groups
    .flatMap((group) => group.rows)
    .find((row) => row.fingerprint === selectedFingerprint) ?? null;
  const canScan = !session || ['operator', 'admin'].includes(session.role);

  useEffect(() => {
    setSelectedFingerprint(null);
    setScanMessage(null);
    setScanError(null);
  }, [targetId]);

  async function runScan() {
    if (!target) return;
    setScanBusy(true);
    setScanMessage(null);
    setScanError(null);
    try {
      const scan = await client.runScan(target.id);
      setScanMessage(
        `Scan #${scan.id} queued. The column becomes comparable when it completes.`,
      );
      await reload();
    } catch (requestError) {
      setScanError(requestError.message);
    } finally {
      setScanBusy(false);
    }
  }

  if (targetsLoading) return <SheetLoading label="Loading the target register" />;
  if (targetsError) {
    return <SheetError message={targetsError.message} onRetry={() => window.location.reload()} />;
  }
  if (targets.length === 0) {
    return (
      <EmptySheet
        title="No targets registered."
        action={(
          <button type="button" className="primary-button" onClick={onOpenTargets}>
            Register a target
          </button>
        )}
      >
        <p>Nothing has been observed. Register an authorised target to start the record.</p>
      </EmptySheet>
    );
  }
  if (targetId == null || !target) {
    return (
      <EmptySheet
        title={targetId == null ? 'No target selected.' : 'Target not found.'}
        action={(
          <button type="button" className="secondary-button" onClick={onOpenTargets}>
            Open the target register
          </button>
        )}
      >
        <p>Choose a target to read its observation record.</p>
      </EmptySheet>
    );
  }

  const scanDisabled = !target.scannable || !canScan || scanBusy;
  const refusal = !canScan
    ? 'Scanning requires an operator role.'
    : !target.scannable
      ? target.refusal_reasons.join(' ') || 'Scanning is not permitted for this target.'
      : null;

  return (
    <div className="drift-page">
      <TargetIndex targets={targets} selectedId={targetId} onSelect={onSelectTarget} />

      <section className="drift-subject">
        <header className="subject">
          <div>
            <p className="engraved">SUBJECT</p>
            <h1>{target.name}</h1>
            <p className="mono subject-meta">
              {target.address} · {target.target_type}
            </p>
          </div>
          <div className="subject-actions">
            <button type="button" className="secondary-button" onClick={reload}>
              Refresh
            </button>
            <button
              type="button"
              className="primary-button"
              disabled={scanDisabled}
              title={refusal ?? undefined}
              onClick={runScan}
            >
              {scanBusy ? 'Queueing…' : 'Run scan'}
            </button>
          </div>
        </header>

        <AuthorisationStamp target={target} />
        {refusal && <p className="refusal">{refusal}</p>}
        {scanMessage && <p className="detail-status" role="status">{scanMessage}</p>}
        {scanError && <p className="form-error" role="alert">{scanError}</p>}

        {loading && <SheetLoading label="Loading the observation record" />}
        {!loading && error && (
          <SheetError message={error.message} onRetry={reload} />
        )}

        {!loading && !error && model && !model.hasComparable && (
          <>
            <PendingScanPanel scans={model.pendingScans} />
            <EmptySheet
              title="No observations yet."
              action={target.scannable && canScan ? (
                <button
                  type="button"
                  className="primary-button"
                  onClick={runScan}
                  disabled={scanBusy}
                >
                  Run baseline
                </button>
              ) : undefined}
            >
              <p>Run a baseline to start the record. Nothing is inferred from an empty database.</p>
            </EmptySheet>
          </>
        )}

        {!loading && !error && model?.hasComparable && (
          <>
            <DifferenceLine model={model} />
            <PendingScanPanel scans={model.pendingScans} />
            <ThreadGrid
              model={model}
              selected={selectedFingerprint}
              onSelect={setSelectedFingerprint}
            />
            {selectedRow ? (
              <EvidenceDetail
                row={selectedRow}
                scans={model.scans}
                client={client}
                targetName={target.name}
              />
            ) : (
              <p className="detail-prompt">
                Select a thread to inspect its evidence. Hover or focus a row; the rail
                never invents detail.
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Run the tests**

```bash
cd frontend && npm test -- --run src/pages/Drift.test.jsx
```

Expected: PASS (4 tests). The queued-scan test may need `findByRole('status')` because
the status is rendered after the reload promise; use `await screen.findByText(/Scan #2 queued/)`
if the strict role query races.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Drift.jsx frontend/src/pages/Drift.test.jsx
git commit -m "feat(ui): the Drift subject sheet with stored threads and explicit refusals"
```

---

## Task 13: Evaluation page

Accuracy is a separate report, not a console scan summary. The page shows only what
`GET /api/evaluation` returns; when it is unavailable, it shows no numbers at all.

**Files:**
- Create: `frontend/src/pages/Evaluation.jsx`, `Evaluation.test.jsx`
- Fill: `frontend/src/styles/evaluation.css`

**Interfaces:**
- `Evaluation({ client })` fetches `/api/evaluation` once on mount.
  - `available: false` → reason, duplicate labels (if any), and the remediation hint;
    no readouts, no table.
  - `available: true` → two large readouts with numerator/denominator, a ruled per-area
    table (TLS, Network, API first, then any other area), unmeasured labels, and the
    caveat block.
- Percentage text comes from `formatRate`.

- [ ] **Step 1: Write the failing page test**

Create `frontend/src/pages/Evaluation.test.jsx`:

```jsx
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Evaluation } from './Evaluation';

const available = {
  available: true,
  generated_at: '2026-11-24T10:00:00Z',
  overall: {
    detections: 38, present_total: 40, detection_accuracy: 0.95,
    false_positives: 1, absent_total: 45, false_positive_rate: 0.0222,
    unmeasured_scans: 4, down_observations: 2,
  },
  per_area: {
    TLS: {
      detections: 18, present_total: 18, detection_accuracy: 1,
      false_positives: 0, absent_total: 20, false_positive_rate: 0,
      unmeasured_scans: 2, down_observations: 1,
    },
    Network: {
      detections: 12, present_total: 13, detection_accuracy: 0.923,
      false_positives: 1, absent_total: 15, false_positive_rate: 0.0667,
      unmeasured_scans: 1, down_observations: 1,
    },
    API: {
      detections: 8, present_total: 9, detection_accuracy: 0.889,
      false_positives: 0, absent_total: 10, false_positive_rate: 0,
      unmeasured_scans: 1, down_observations: 0,
    },
  },
  per_target: {},
  unmeasured: {
    ground_truth_scans_without_engine_scan: ['S5'],
    engine_scans_without_ground_truth: [],
  },
  scan_labels: ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'],
};

describe('Evaluation', () => {
  it('shows the two readouts with numerator and denominator', async () => {
    const client = { evaluation: vi.fn().mockResolvedValue(available) };
    render(<Evaluation client={client} />);

    await screen.findByText('DETECTION ACCURACY');
    expect(screen.getByText('95.0%')).toBeTruthy();
    expect(screen.getByText(/38\/40/)).toBeTruthy();
    expect(screen.getByText('FALSE-POSITIVE RATE')).toBeTruthy();
    expect(screen.getByText('2.2%')).toBeTruthy();
    expect(screen.getByText(/1\/45/)).toBeTruthy();
  });

  it('lists areas in audited order with counts', async () => {
    const client = { evaluation: vi.fn().mockResolvedValue(available) };
    render(<Evaluation client={client} />);
    await screen.findByText('DETECTION ACCURACY');

    const areas = screen.getAllByRole('rowheader').map((cell) => cell.textContent);
    expect(areas).toEqual(['TLS', 'Network', 'API', 'Overall']);
    expect(screen.getByText(/Scored against the lab's ground truth/)).toBeTruthy();
    expect(screen.getByText(/Console scans are exploratory and are not scored/)).toBeTruthy();
  });

  it('shows no numbers when the report is unavailable', async () => {
    const client = {
      evaluation: vi.fn().mockResolvedValue({
        available: false,
        reason: 'Scan labels S1 and S2 are each recorded twice.',
        duplicates: ['S1', 'S2'],
      }),
    };
    render(<Evaluation client={client} />);

    await screen.findByText(/Scan labels S1 and S2 are each recorded twice/);
    expect(screen.getByText('S1, S2')).toBeTruthy();
    expect(screen.queryByText('95.0%')).toBeNull();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('reports an unreachable evaluation without inventing a score', async () => {
    const client = { evaluation: vi.fn().mockRejectedValue(new Error('API unreachable at 127.0.0.1:8000. Start the backend, then retry.')) };
    render(<Evaluation client={client} />);
    await waitFor(() => expect(screen.getByRole('alert').textContent)
      .toContain('API unreachable'));
    expect(screen.queryByRole('table')).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/Evaluation.test.jsx
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement the page**

Create `frontend/src/pages/Evaluation.jsx`. Required structure:

```jsx
import { useEffect, useState } from 'react';

import { SheetError, SheetLoading } from '../components/StateBlocks';
import { formatRate } from '../lib/format';

const AREA_ORDER = ['TLS', 'Network', 'API'];

const COLUMNS = [
  ['detections', 'Detections'],
  ['misses', 'Misses'],
  ['false_positives', 'False positives'],
  ['unmeasured_scans', 'Unmeasured scans'],
  ['down_observations', 'Down observations'],
];

function Readout({ label, value, numerator, denominator }) {
  return (
    <div className="readout">
      <p className="engraved">{label}</p>
      <p className="readout-value mono">{value}</p>
      <p className="readout-fraction mono">{numerator}/{denominator}</p>
    </div>
  );
}

export function Evaluation({ client }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ data: null, loading: true, error: null });

  useEffect(() => {
    let active = true;
    setState({ data: null, loading: true, error: null });
    client.evaluation()
      .then((data) => active && setState({ data, loading: false, error: null }))
      .catch((error) => active && setState({ data: null, loading: false, error }));
    return () => { active = false; };
  }, [client, refreshKey]);

  const retry = () => setRefreshKey((key) => key + 1);

  if (state.loading) return <SheetLoading label="Scoring against the lab ground truth" />;
  if (state.error) return <SheetError message={state.error.message} onRetry={retry} />;

  const { data } = state;
  // ... render unavailable branch first (no readouts, no table) ...
  // ... render readouts, per-area table, unmeasured labels, caveat ...
}
```

Rendering requirements (implement fully):

- Page header: engraved `ACCURACY REPORT`, `h1` `Evaluation`, generated timestamp as
  `formatDateTime`.
- The per-area table must use `<th scope="row">TLS</th>`, `Network`, `API` (plus any
  other area sorted) and a `<tfoot>` row whose row header reads `Overall`.
- Unavailable branch: `<section className="unavailable">` with the reason verbatim, a
  `Duplicate labels` line when `duplicates.length` (`S1, S2`), the hint
  `Rename the duplicate labels in the lab sequence so each ground-truth scan has one
  engine scan, then regenerate the report.`, and **no** readouts or table.
- Available branch:
  - `<Readout label="DETECTION ACCURACY" value={formatRate(overall.detection_accuracy)} numerator={overall.detections} denominator={overall.present_total} />`
  - `<Readout label="FALSE-POSITIVE RATE" value={formatRate(overall.false_positive_rate)} numerator={overall.false_positives} denominator={overall.absent_total} />`
  - `<table className="area-table">` with caption `Per-area accuracy`; column headers
    `Area` plus `COLUMNS`; row headers `TLS`, `Network`, `API`, then any remaining
    `per_area` keys sorted. Every cell is a plain count (`String(value ?? 0)`).
  - Overall row at the end (`overall`).
  - Unmeasured block when either list is non-empty: `Ground-truth scans without an
    engine scan: S5` and `Engine scans without ground truth: …` (omit empty lines).
  - Caveat block, verbatim: `Scored against the lab's ground truth. A label with no
    engine scan is unmeasured, not correct.` and `Console scans are exploratory and are
    not scored. Accuracy requires the labelled lab sequence (sequence.py).`

Fill `frontend/src/styles/evaluation.css`:

```css
.evaluation-page { max-width: 960px; margin: 0 auto; padding: var(--space-6) var(--space-5); }
.readouts { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: var(--space-5); margin: var(--space-6) 0; }
.readout { border-top: 2px solid var(--ink); padding-top: var(--space-3); }
.readout-value { font-size: var(--step-4); font-weight: 500; margin: var(--space-2) 0 0; }
.readout-fraction { color: var(--ink-2); margin: 0; }
.area-table { width: 100%; border-collapse: collapse; margin-top: var(--space-5); }
.area-table caption { text-align: left; padding-bottom: var(--space-2); font-family: var(--font-mono); font-size: var(--step--1); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-2); }
.area-table th, .area-table td { border-bottom: 1px solid var(--rule); padding: var(--space-2); text-align: right; }
.area-table th:first-child, .area-table td:first-child { text-align: left; }
.area-table thead th { border-bottom: 1px solid var(--ink); font-weight: 500; }
.area-table tfoot td, .area-table tfoot th { border-top: 1px solid var(--ink); border-bottom: 0; }
.caveat { margin-top: var(--space-6); padding: var(--space-4); border-left: 2px solid var(--ink); background: var(--sheet); max-width: 70ch; }
.unavailable { margin-top: var(--space-6); padding: var(--space-5); border-top: 2px solid var(--pending); background: var(--sheet); }
.duplicate-list { font-family: var(--font-mono); }
```

- [ ] **Step 4: Run the tests**

```bash
cd frontend && npm test -- --run src/pages/Evaluation.test.jsx
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Evaluation.jsx frontend/src/pages/Evaluation.test.jsx \
  frontend/src/styles/evaluation.css
git commit -m "feat(ui): accuracy report with explicit unavailable state"
```

---

## Task 14: Settings page

**Files:**
- Modify: `frontend/src/api/client.js` (export `API_BASE`)
- Create: `frontend/src/pages/Settings.jsx`, `Settings.test.jsx`
- Fill: `frontend/src/styles/shell.css` (settings rules)

**Interfaces:**
- `Settings({ client, session, apiBase })` fetches `/api/stats` once (with retry).
- Sections, in order: Connection, Mode, Redaction, Data footprint, Version. No toggles.
- `API_BASE` exported from `client.js` is the resolved base (`VITE_API_URL` or
  `http://127.0.0.1:8000`) and is passed in by `App`.

- [ ] **Step 1: Write the failing page test**

Create `frontend/src/pages/Settings.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Settings } from './Settings';

const stats = {
  targets: 5, scans: 9, evidence: 142, drift_events: 38,
  auth_mode: 'local_research',
  redaction: { enabled: true, token_map: 'local-only' },
};

describe('Settings', () => {
  it('reports connection, mode, redaction, footprint, and version', async () => {
    const client = { stats: vi.fn().mockResolvedValue(stats) };
    render(<Settings client={client} session={null} apiBase="http://127.0.0.1:8000" />);

    await screen.findByText('Connection');
    expect(screen.getByText('http://127.0.0.1:8000')).toBeTruthy();
    expect(screen.getByText('LOCAL RESEARCH')).toBeTruthy();
    expect(screen.getByText(/token map never leaves/)).toBeTruthy();
    expect(screen.getByText('targets')).toBeTruthy();
    expect(screen.getByText('drift events')).toBeTruthy();
    expect(screen.getByText('5')).toBeTruthy();
    expect(screen.getByText('38')).toBeTruthy();
  });

  it('names the signed-in operator in JWT mode', async () => {
    const client = { stats: vi.fn().mockResolvedValue({ ...stats, auth_mode: 'jwt' }) };
    render(<Settings client={client} session={{ username: 'alice', role: 'operator' }} apiBase="http://127.0.0.1:8000" />);

    await screen.findByText('Connection');
    expect(screen.getByText(/JWT/)).toBeTruthy();
    expect(screen.getByText(/alice · operator/)).toBeTruthy();
  });

  it('shows an actionable error instead of empty counts when unreachable', async () => {
    const client = { stats: vi.fn().mockRejectedValue(new Error('API unreachable at 127.0.0.1:8000. Start the backend, then retry.')) };
    render(<Settings client={client} session={null} apiBase="http://127.0.0.1:8000" />);
    expect(await screen.findByRole('alert').textContent)
      .toContain('API unreachable at 127.0.0.1:8000');
    expect(screen.queryByText('drift events')).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/pages/Settings.test.jsx
```

Expected: FAIL, module not found.

- [ ] **Step 3: Implement the page**

1. In `frontend/src/api/client.js`, add `export const API_BASE = DEFAULT_BASE;` next to
   `DEFAULT_BASE`.
2. Create `frontend/src/pages/Settings.jsx`:

```jsx
import { useEffect, useState } from 'react';

import { SheetError, SheetLoading } from '../components/StateBlocks';
import { formatDateTime } from '../lib/format';

const FOOTPRINT = [
  ['targets', 'targets'],
  ['scans', 'scans'],
  ['evidence', 'evidence'],
  ['drift_events', 'drift events'],
];

function Section({ title, children }) {
  return (
    <section className="settings-section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function Settings({ client, session, apiBase }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState({ stats: null, loading: true, error: null });

  useEffect(() => {
    let active = true;
    setState({ stats: null, loading: true, error: null });
    client.stats()
      .then((stats) => active && setState({ stats, loading: false, error: null }))
      .catch((error) => active && setState({ stats: null, loading: false, error }));
    return () => { active = false; };
  }, [client, refreshKey]);

  if (state.loading) return <SheetLoading label="Reading service state" />;
  if (state.error) {
    return <SheetError message={state.error.message} onRetry={() => setRefreshKey((key) => key + 1)} />;
  }

  const { stats } = state;
  const local = stats.auth_mode === 'local_research';
  const version = typeof __APP_VERSION__ === 'string' ? __APP_VERSION__ : '0.0.0';

  return (
    <section className="settings-page">
      <header className="page-head">
        <div>
          <p className="engraved">SERVICE STATE</p>
          <h1>Settings</h1>
        </div>
      </header>

      <Section title="Connection">
        <dl className="settings-list">
          <dt>API base</dt>
          <dd className="mono">{apiBase}</dd>
          <dt>Status</dt>
          <dd>Reachable · responded to <span className="mono">/api/stats</span></dd>
        </dl>
      </Section>

      <Section title="Mode">
        <p className="mono">{local ? 'LOCAL RESEARCH' : 'JWT'}</p>
        {local ? (
          <p>
            No bearer token is required. Requests are attributed to the local-research
            principal on this machine.
          </p>
        ) : (
          <p>
            {session
              ? `Signed in as ${session.username} · ${session.role}.`
              : 'Bearer token required. Sign in to attribute requests.'}
          </p>
        )}
      </Section>

      <Section title="Redaction">
        <p>
          {stats.redaction?.enabled
            ? 'Exports are tokenised before they leave the process.'
            : 'Redaction is disabled on this installation.'}
        </p>
        <p>
          The token map never leaves the backend process. Only the redacted evidence
          endpoint can be shared.
        </p>
      </Section>

      <Section title="Data footprint">
        <dl className="settings-list">
          {FOOTPRINT.map(([key, label]) => (
            <div key={key}>
              <dt>{label}</dt>
              <dd className="mono">{String(stats[key] ?? 0)}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section title="Version">
        <p className="mono">driftguard-ui {version}</p>
        <p className="engraved">RECORD GENERATED {formatDateTime(new Date().toISOString())}</p>
      </Section>
    </section>
  );
}
```

Footprint rows are plain `<dt>/<dd>` pairs (no extra ARIA): the console must stay
semantic, and the test asserts on the visible label and value instead of ARIA
`definition` names.

Fill the settings rules in `frontend/src/styles/shell.css`:

```css
.settings-page { max-width: 860px; margin: 0 auto; padding: var(--space-6) var(--space-5); }
.settings-section { border-top: 1px solid var(--rule); padding: var(--space-4) 0; }
.settings-section:first-of-type { border-top: 2px solid var(--ink); }
.settings-section h2 { font-size: var(--step-1); margin: 0 0 var(--space-2); }
.settings-list { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: var(--space-2) var(--space-4); margin: 0; }
.settings-list dt { font-family: var(--font-mono); font-size: var(--step--1); letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-2); }
.settings-list dd { margin: 0; }
```

- [ ] **Step 4: Run the tests**

```bash
cd frontend && npm test -- --run src/pages/Settings.test.jsx
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.js frontend/src/pages/Settings.jsx \
  frontend/src/pages/Settings.test.jsx frontend/src/styles/shell.css
git commit -m "feat(ui): settings that report connection, mode, redaction, and footprint"
```

---

## Task 15: Responsive behaviour and reduced-motion parity

The spec requires real behaviour changes at breakpoints, not just shrinking: at ≤900px
the index becomes a target selector and the grid becomes stacked fingerprint cards; at
≤600px the top nav collapses to a menu.

**Files:**
- Create: `frontend/src/state/useMediaQuery.js`, `useMediaQuery.test.js`
- Create: `frontend/src/components/ThreadCards.jsx`, `ThreadCards.test.jsx`
- Modify: `frontend/src/components/TargetIndex.jsx` (accept `narrow`), its test
- Modify: `frontend/src/components/AppShell.jsx` (accept `navNarrow`), its test
- Modify: `frontend/src/pages/Drift.jsx` (choose grid or cards)
- Fill: `frontend/src/styles/responsive.css`

**Interfaces:**
- `useMediaQuery(query, { fallback = false })` → boolean; safe when
  `window.matchMedia` is missing (jsdom) or `prefers-reduced-motion` style queries are
  unsupported.
- `TargetIndex({ targets, selectedId, onSelect, narrow })` renders a labelled
  `<select>` when `narrow`.
- `ThreadCards({ model, selected, onSelect })` renders one card per row: title,
  resource, severity, current token, and a compact timeline of cell marks with visually
  hidden text.
- `AppShell({ navNarrow })` collapses the nav behind a `Menu` button with
  `aria-expanded`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/state/useMediaQuery.test.js`:

```jsx
import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useMediaQuery } from './useMediaQuery';

describe('useMediaQuery', () => {
  it('returns the fallback when matchMedia is unavailable', () => {
    const { result } = renderHook(() => useMediaQuery('(max-width: 900px)'));
    expect(result.current).toBe(false);
    const { result: held } = renderHook(() => useMediaQuery('(max-width: 900px)', { fallback: true }));
    expect(held.current).toBe(true);
  });

  it('follows a real media query when one exists', () => {
    const listeners = [];
    window.matchMedia = (query) => ({
      matches: query.includes('900'),
      media: query,
      addEventListener: (_type, fn) => listeners.push(fn),
      removeEventListener: (_type, fn) => listeners.splice(listeners.indexOf(fn), 1),
    });
    const { result, unmount } = renderHook(() => useMediaQuery('(max-width: 900px)'));
    expect(result.current).toBe(true);
    unmount();
    expect(listeners).toHaveLength(0);
    delete window.matchMedia;
  });
});
```

Create `frontend/src/components/ThreadCards.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ThreadCards } from './ThreadCards';

const model = {
  scans: [
    { id: 1, kind: 'baseline', status: 'completed', summary: { state: 'BASELINE' } },
    { id: 3, kind: 'compared', status: 'completed', summary: { state: 'CHANGED' } },
  ],
  groups: [{
    key: 'TLS',
    rows: [{
      fingerprint: 't/TLS/a', title: 'Legacy TLS', resource: 't:8443', severity: 'High',
      cells: [{ kind: 'baseline' }, { kind: 'fixed' }],
      current: { classification: 'FIXED', scanId: 3 },
    }],
  }],
};

describe('ThreadCards', () => {
  it('renders a card with the token and a hidden timeline', async () => {
    const onSelect = vi.fn();
    render(<ThreadCards model={model} selected={null} onSelect={onSelect} />);

    expect(screen.getByRole('heading', { name: 'Legacy TLS' })).toBeTruthy();
    expect(screen.getByText('FIXED')).toBeTruthy();
    expect(screen.getAllByText(/baseline observation/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/— fixed/).length).toBeGreaterThan(0);

    await userEvent.setup().click(screen.getByRole('button', { name: /Legacy TLS/ }));
    expect(onSelect).toHaveBeenCalledWith('t/TLS/a');
  });
});
```

Add to `frontend/src/components/TargetIndex.test.jsx`:

```jsx
it('becomes a target selector on narrow screens', async () => {
  const onSelect = vi.fn();
  render(<TargetIndex targets={targets} selectedId={1} onSelect={onSelect} narrow />);
  const select = screen.getByLabelText('Subject');
  expect(select.value).toBe('1');
  await userEvent.setup().selectOptions(select, '2');
  expect(onSelect).toHaveBeenCalledWith(2);
});
```

Add to `frontend/src/components/AppShell.test.jsx`:

```jsx
it('collapses navigation behind a menu at narrow widths', async () => {
  render(<AppShell route={{ page: 'drift', targetId: 1 }} mode={{ kind: 'local' }} navNarrow>
    <p>body</p>
  </AppShell>);
  const menu = screen.getByRole('button', { name: 'Menu' });
  expect(menu.getAttribute('aria-expanded')).toBe('false');
  await userEvent.setup().click(menu);
  expect(screen.getByRole('button', { name: 'Menu' }).getAttribute('aria-expanded')).toBe('true');
  expect(screen.getByRole('link', { name: 'Drift' })).toBeTruthy();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd frontend && npm test -- --run src/state/useMediaQuery.test.js \
  src/components/ThreadCards.test.jsx src/components/TargetIndex.test.jsx \
  src/components/AppShell.test.jsx
```

Expected: FAIL (new modules missing; the AppShell/TargetIndex additions fail too).

- [ ] **Step 3: Implement**

`frontend/src/state/useMediaQuery.js`:

```js
import { useEffect, useState } from 'react';

export function useMediaQuery(query, { fallback = false } = {}) {
  const [matches, setMatches] = useState(() => {
    if (typeof window !== 'object' || typeof window.matchMedia !== 'function') {
      return fallback;
    }
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window !== 'object' || typeof window.matchMedia !== 'function') return undefined;
    const list = window.matchMedia(query);
    const onChange = (event) => setMatches(event.matches);
    setMatches(list.matches);
    if (typeof list.addEventListener === 'function') {
      list.addEventListener('change', onChange);
      return () => list.removeEventListener('change', onChange);
    }
    return undefined;
  }, [query]);

  return matches;
}
```

`frontend/src/components/ThreadCards.jsx` — structure required:

```jsx
<li className={`thread-card${selected ? ' is-selected' : ''}`}>
  <div className="card-head">
    <h2 className="card-title">
      <button type="button" onClick={() => onSelect(row.fingerprint)}>
        {row.title}
      </button>
    </h2>
    <span className="card-current mono">{row.current.classification}</span>
    {['Critical', 'High'].includes(row.severity) && (
      <span className="severity mono">{row.severity}</span>
    )}
  </div>
  <span className="mono card-resource">{row.resource}</span>
  <ol className="compact-timeline" aria-hidden="true">
    {row.cells.map((cell, index) => (
      <li key={model.scans[index].id} className={`tick kind-${cell.kind}`}>
        <span className={`mark mark-${cell.kind}`} />
      </li>
    ))}
  </ol>
  <div className="visually-hidden">
    {row.cells.map((cell, index) => (
      <span key={model.scans[index].id}>
        {`#${model.scans[index].id} — ${MARK_TEXT[cell.kind]}`}
      </span>
    ))}
  </div>
</li>
```

Reuse the same `MARK_TEXT` map as `ThreadRow`: export it from `ThreadRow.jsx` as
`export const MARK_TEXT = { … }` and import it in `ThreadCards`.

`TargetIndex` changes: add `narrow = false` prop; when narrow, render:

```jsx
<label className="target-select-label">
  <span className="engraved">SUBJECT</span>
  <select
    value={selectedId ?? ''}
    onChange={(event) => onSelect(Number(event.target.value))}
  >
    {targets.map((target) => (
      <option key={target.id} value={target.id}>{target.name}</option>
    ))}
  </select>
</label>
```

`AppShell` changes: add `navNarrow = false` prop; when `navNarrow`, wrap the nav in a
`.nav-menu` container with a `Menu` button (`aria-expanded`, `aria-controls="primary-nav"`)
and add `id="primary-nav"` to the nav; the nav stays in the DOM (no conditional unmount)
so screen readers can reach it when the menu is open.

`Drift` change: add `import { useMediaQuery } from '../state/useMediaQuery';`, then
`const narrow = useMediaQuery('(max-width: 900px)');` and render
`{narrow ? <ThreadCards ... /> : <ThreadGrid ... />}` — the model and selection props are
identical.

- [ ] **Step 4: Fill `frontend/src/styles/responsive.css`**

```css
@media (max-width: 900px) {
  .drift-page { grid-template-columns: minmax(0, 1fr); }
  .target-index { border-right: 0; border-bottom: 1px solid var(--rule); }
  .target-select-label { display: grid; gap: var(--space-1); }
  .target-select-label select { padding: 8px 10px; border: 1px solid var(--ink); background: var(--sheet); }
  .roster-row { grid-template-columns: minmax(0, 1fr); }
  .detail-rail { grid-template-columns: minmax(0, 1fr); }
  .detail-rail {
    position: sticky;
    bottom: 0;
    background: var(--paper);
    border-top: 2px solid var(--ink);
    padding-bottom: var(--space-4);
  }
}

@media (max-width: 600px) {
  .top-strip { flex-wrap: wrap; height: auto; padding: var(--space-3); gap: var(--space-3); }
  .top-nav { width: 100%; flex-direction: column; gap: var(--space-2); }
  .top-nav[hidden] { display: none; }
  .mode { margin-left: 0; }
  .subject { flex-direction: column; }
  .subject-actions { width: 100%; flex-direction: column; }
  .register-actions { flex-direction: column; }
  .readout-value { font-size: 28px; }
}

@media (prefers-reduced-motion: no-preference) {
  .thread-cell.is-drawing {
    animation: thread-draw 480ms ease-out both;
  }
}
@keyframes thread-draw {
  from { opacity: 0; transform: translateX(-6px); }
  to { opacity: 1; transform: none; }
}
```

The thread draw is column-scoped and staggered, per spec: `ThreadGrid` computes the
index of the newest compared scan column (`drawIndex`) and passes `drawIndex` plus the
row index to `ThreadRow`. A cell whose index equals `drawIndex` gets
`className="... is-drawing"` and `style={{ animationDelay: `${Math.min(rowIndex, 8) * 20}ms` }}`
— 480ms once, 20ms per row, capped at 8 rows. `prefers-reduced-motion` (global rule in
`base.css` plus the wrapper above) disables it entirely.

`prefers-reduced-motion` disabling animation is already handled globally in `base.css`;
the `no-preference` wrapper makes the intent explicit for the thread draw.

- [ ] **Step 5: Run the tests**

```bash
cd frontend && npm test -- --run src/state/useMediaQuery.test.js \
  src/components/ThreadCards.test.jsx src/components/TargetIndex.test.jsx \
  src/components/AppShell.test.jsx
npm run build
```

Expected: PASS (all updated suites); build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/state/useMediaQuery.js frontend/src/state/useMediaQuery.test.js \
  frontend/src/components/ThreadCards.jsx frontend/src/components/ThreadCards.test.jsx \
  frontend/src/components/TargetIndex.jsx frontend/src/components/TargetIndex.test.jsx \
  frontend/src/components/AppShell.jsx frontend/src/components/AppShell.test.jsx \
  frontend/src/pages/Drift.jsx frontend/src/styles/responsive.css
git commit -m "feat(ui): breakpoint behaviour for the viva surface"
```

---

## Task 16: App wiring

**Files:**
- Replace: `frontend/src/App.jsx`, create `frontend/src/App.test.jsx`
- Modify: `frontend/src/main.jsx` (wrap in `ErrorBoundary`)

**Interfaces:**
- `App({ makeClient = createApiClient })` — `makeClient` is the only test seam; it
  receives `{ baseUrl, getToken, onUnauthorized }` and must be called **once** (store the
  client in a ref so page renders cannot rebuild it and retrigger `useTargets`).
- Responsibilities:
  - session from `sessionStorage`; sign-in on `needsSignIn`; sign-out clears it.
  - hash route → one of the four pages; default `#/drift` resolves to the newest target
    (first in the list) with `replace: true`, or to `#/targets` when no targets exist.
  - `#/drift/{id}` where the id is not in the register renders `Target not found.`.
  - `Run scan` from Targets navigates to Drift and bumps a refresh key so the Drift
    sheet remounts and reloads (`key={`${targetId}:${scanRefresh}`}`).
  - `navNarrow` comes from `useMediaQuery('(max-width: 600px)')`.
- `main.jsx` renders `<React.StrictMode><ErrorBoundary><App /></ErrorBoundary></React.StrictMode>`.

- [ ] **Step 1: Write the failing wiring test**

Create `frontend/src/App.test.jsx`:

```jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

const target = {
  id: 1,
  name: 'eservices-lab',
  address: 'https://127.0.0.1:8443',
  target_type: 'web',
  authorization_status: 'authorized',
  authorized_by: 'A. Owner',
  authorized_at: '2026-11-12T09:30:00Z',
  authorization_basis: 'written approval',
  approved_scope: ['tls'],
  approved_ports: [8443],
  last_scan: null,
  scannable: true,
  refusal_reasons: [],
};

const history = {
  target,
  scans: [{
    scan: {
      id: 1, target_id: 1, status: 'completed',
      started_at: '2026-11-12T09:30:00Z', completed_at: '2026-11-12T09:31:00Z',
      is_baseline: true, label: null, error: null,
    },
    comparable: true,
    evidence: [{
      id: 1, scan_id: 1, fingerprint: 'eservices-lab/TLS/a', category: 'TLS',
      title: 'Legacy TLS', severity: 'High', resource: '127.0.0.1:8443',
      details: {}, observed_at: '2026-11-12T09:30:00Z',
    }],
    drift: [],
    summary: { state: 'BASELINE', counts: { NEW: 0, PERSISTENT: 0, FIXED: 0, RECURRING: 0 } },
  }],
  fingerprints: {
    'eservices-lab/TLS/a': {
      title: 'Legacy TLS', category: 'TLS', severity: 'High', resource: '127.0.0.1:8443',
    },
  },
};

function makeClient() {
  return {
    targets: vi.fn().mockResolvedValue([target]),
    history: vi.fn().mockResolvedValue(history),
    stats: vi.fn().mockResolvedValue({ targets: 1, scans: 1, evidence: 1, drift_events: 0, auth_mode: 'local_research', redaction: { enabled: true } }),
    evaluation: vi.fn().mockResolvedValue({ available: false, reason: 'no scans' }),
    runScan: vi.fn(),
    createTarget: vi.fn(),
    login: vi.fn(),
    redactedEvidence: vi.fn().mockResolvedValue([]),
  };
}

beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState(null, '', '#/');
});

describe('App', () => {
  it('resolves the default Drift route to the first target', async () => {
    const client = makeClient();
    render(<App makeClient={() => client} />);

    await waitFor(() => expect(window.location.hash).toBe('#/drift/1'));
    expect(await screen.findByRole('heading', { name: 'eservices-lab' })).toBeTruthy();
    expect(client.history).toHaveBeenCalledTimes(1);
  });

  it('sends an empty installation to the target register', async () => {
    const client = makeClient();
    client.targets.mockResolvedValue([]);
    render(<App makeClient={() => client} />);

    await waitFor(() => expect(window.location.hash).toBe('#/targets'));
    expect(await screen.findByText('No targets registered.')).toBeTruthy();
    expect(client.history).not.toHaveBeenCalled();
  });

  it('opens sign-in when the API answers 401 and closes it after a token', async () => {
    const client = makeClient();
    let seam = null;
    const makeClientWithSeam = (options) => {
      seam = options;
      return client;
    };
    render(<App makeClient={makeClientWithSeam} />);
    await screen.findByRole('heading', { name: 'eservices-lab' });

    seam.onUnauthorized();
    expect(await screen.findByRole('dialog')).toBeTruthy();

    client.login.mockResolvedValue({
      access_token: 'jwt', expires_in: 3600, username: 'alice', role: 'admin',
    });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Username'), 'alice');
    await user.type(screen.getByLabelText('Password'), 'hunter2');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(window.sessionStorage.getItem('driftguard.session')).toContain('alice');
    expect(screen.getByText('OPERATOR · alice')).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd frontend && npm test -- --run src/App.test.jsx
```

Expected: FAIL (old `App.jsx` renders the dashboard).

- [ ] **Step 3: Implement `App.jsx`**

Replace `frontend/src/App.jsx` entirely:

```jsx
import { useCallback, useEffect, useRef, useState } from 'react';

import { API_BASE, createApiClient } from './api/client';
import { AppShell } from './components/AppShell';
import { SignIn } from './components/SignIn';
import { Drift } from './pages/Drift';
import { Evaluation } from './pages/Evaluation';
import { Settings } from './pages/Settings';
import { Targets } from './pages/Targets';
import { clearSession, loadSession, saveSession, toSession } from './state/session';
import { useMediaQuery } from './state/useMediaQuery';
import { navigate, useHashRoute } from './state/useHashRoute';
import { useTargets } from './state/useTargets';

export default function App({ makeClient = createApiClient } = {}) {
  const [session, setSession] = useState(() => loadSession());
  const sessionRef = useRef(session);
  useEffect(() => { sessionRef.current = session; }, [session]);

  const [needsSignIn, setNeedsSignIn] = useState(false);
  const [signInError, setSignInError] = useState(null);
  const [signInBusy, setSignInBusy] = useState(false);
  const [scanRefresh, setScanRefresh] = useState(0);

  const getToken = useCallback(() => sessionRef.current?.token ?? null, []);

  const clientRef = useRef(null);
  if (clientRef.current === null) {
    clientRef.current = makeClient({
      baseUrl: API_BASE,
      getToken,
      onUnauthorized: () => {
        // A 401 invalidates whatever token is cached for this session.
        clearSession();
        setSession(null);
        setNeedsSignIn(true);
      },
    });
  }
  const client = clientRef.current;

  const route = useHashRoute();
  const targetsState = useTargets(client);
  const navNarrow = useMediaQuery('(max-width: 600px)');

  useEffect(() => {
    if (route.page !== 'drift' || route.targetId != null) return;
    if (targetsState.loading) return;
    if (targetsState.targets.length === 0) {
      navigate({ page: 'targets' }, { replace: true });
      return;
    }
    navigate({ page: 'drift', targetId: targetsState.targets[0].id }, { replace: true });
  }, [route.page, route.targetId, targetsState.loading, targetsState.targets]);

  async function signIn(username, password) {
    setSignInBusy(true);
    setSignInError(null);
    try {
      const token = await client.login(username, password);
      const next = toSession(token);
      saveSession(next);
      setSession(next);
      setNeedsSignIn(false);
    } catch (error) {
      setSignInError(error.message);
    } finally {
      setSignInBusy(false);
    }
  }

  function signOut() {
    clearSession();
    setSession(null);
    setNeedsSignIn(false);
  }

  const mode = session
    ? { kind: 'operator', username: session.username, role: session.role }
    : { kind: 'local' };

  let page;
  if (route.page === 'targets') {
    page = (
      <Targets
        client={client}
        targets={targetsState.targets}
        loading={targetsState.loading}
        error={targetsState.error}
        onReload={targetsState.reload}
        onOpen={(id) => navigate({ page: 'drift', targetId: id })}
        onScanQueued={(queuedTarget) => {
          navigate({ page: 'drift', targetId: queuedTarget.id });
          setScanRefresh((value) => value + 1);
        }}
        onRegistered={async (registered) => {
          await targetsState.reload();
          navigate({ page: 'drift', targetId: registered.id });
        }}
        session={session}
      />
    );
  } else if (route.page === 'evaluation') {
    page = <Evaluation client={client} />;
  } else if (route.page === 'settings') {
    page = <Settings client={client} session={session} apiBase={API_BASE} />;
  } else {
    page = (
      <Drift
        key={`${route.targetId ?? 'none'}:${scanRefresh}`}
        client={client}
        targets={targetsState.targets}
        targetsLoading={targetsState.loading}
        targetsError={targetsState.error}
        targetId={route.targetId}
        onSelectTarget={(id) => navigate({ page: 'drift', targetId: id })}
        onOpenTargets={() => navigate({ page: 'targets' })}
        session={session}
      />
    );
  }

  return (
    <>
      <AppShell route={route} mode={mode} onSignOut={signOut} navNarrow={navNarrow}>
        {page}
      </AppShell>
      {needsSignIn && (
        <SignIn onSubmit={signIn} error={signInError} busy={signInBusy} />
      )}
    </>
  );
}
```

Update `frontend/src/main.jsx` to wrap `<App />` in `<ErrorBoundary>` imported from
`./components/ErrorBoundary.jsx` (keep the font imports from Task 1).

- [ ] **Step 4: Run the full frontend test suite and build**

```bash
cd frontend && npm test
npm run build
```

Expected: all suites PASS; build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.test.jsx frontend/src/main.jsx
git commit -m "feat(ui): replace the dashboard with the Drift console shell"
```

---

## Task 17: Verification, docs, and handoff

**Files:**
- Modify: `README.md` (frontend row + run instructions), `AGENTS.md` (frontend
  description and test commands), `docs/PROJECT-STATE.md`
- Modify: `docs/superpowers/specs/2026-11-24-drift-console-design.md` (status line)

- [ ] **Step 1: Full test suites**

```bash
cd backend && .venv/bin/python -m unittest discover -s tests   # 127 + new backend tests green
cd frontend && npm test                                        # every suite green
cd frontend && npm run build                                   # production build succeeds
```

- [ ] **Step 2: Manual live check (backend + lab)**

```bash
cd backend && .venv/bin/uvicorn driftguard.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev        # 127.0.0.1:5173
```

Confirm, in the browser, against the running API:

1. `#/targets` lists the register; a pending target's `Run scan` is disabled with its
   refusal reasons.
2. `#/drift/{id}` for `eservices-lab`: baseline column shaded, difference line dated
   `Baseline recorded …`, authorisation stamp shows who/when/why/scope/ports.
3. Switch the lab's `tls-legacy` on (`cd lab && python3 domain.py on eservices-lab
   tls-legacy`), run a scan, and confirm the thread shows `NEW`/`PERSISTENT` rows backed
   by stored `DriftEvent` rows (check `GET /api/targets/{id}/history`).
4. Export the scan as CSV and confirm no raw secret values (the CSV comes from
   `/api/scans/{id}/evidence/redacted`).
5. Force a failure (e.g. point a target at a closed port and run it): the column reads
   `NOT COMPARED`, no `FIXED` marks appear, and the difference line does not move.
6. Reload `#/drift/12` directly — deep link restores the same sheet.
7. Evaluation with no ground truth shows `available: false` and no numbers; Settings
   shows counts, mode, and version; a stopped API shows the unreachable message.
8. Resize to 900px and 600px: selector + cards, then the Menu button. Tab through the
   index, rows, rail, and buttons; the focus ring is visible throughout.

- [ ] **Step 3: Copy and anti-goal audit**

```bash
cd /home/anthonyl/driftguard
grep -rni "comparator" frontend/src README.md AGENTS.md
grep -rni "awaiting assessment\|sparkline\|glow\|gradient" frontend/src
```

Expected: no user-facing “comparator”; no reserved-page language; no decorative
gradients/glows. Fix any hit before merging.

- [ ] **Step 4: Documentation and handoff**

- `README.md`: the `frontend/` row reads “the Drift console — what changed between
  scans”; add frontend run/test lines to the run section
  (`cd frontend && npm run dev`, `npm test`, `npm run build`).
- `AGENTS.md`: update the `frontend/` layout row and the run block with `npm test`.
- `docs/PROJECT-STATE.md`: record that both plans are implemented, which task numbers
  landed, the verification evidence (test counts), and the next steps (live viva
  rehearsal, optional redaction-secret rotation still pending).
- Design doc status line becomes
  `**Status:** approved 2026-11-24 — implemented`.

- [ ] **Step 5: Final commit**

```bash
git add README.md AGENTS.md docs/PROJECT-STATE.md \
  docs/superpowers/specs/2026-11-24-drift-console-design.md
git commit -m "docs(repo): record the Drift console implementation"
git push origin main
```

---

## Notes for the implementer

- Order matters: Tasks 1–5 are pure/tooling, 6–12 are components and pages, 13–15 finish
  the product surface, 16 wires it, 17 verifies. Do not skip a failing test.
- If a test fails because the fixture disagrees with the backend contract, fix the
  fixture; if it fails because the **backend** contract is wrong, stop and record the
  discrepancy in `docs/PROJECT-STATE.md` rather than weakening the frontend test.
- Never add findings, seeds, or sample rows to make a screen look complete. An empty
  state must always be honest.
- The frozen labels and the authorisation contract are not negotiable at the UI layer.














