# Guided Demonstration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a repeatable, evidence-backed guided demonstration of DriftGuard that drives the real API and lab through register → BASELINE → NO DRIFT → NEW → PERSISTENT → FIXED → RECURRING → redacted export, with live UI narration and a screen-recording deliverable.

**Architecture:** Three small backend additions (NO DRIFT event persistence in the existing engine, a drift-event read endpoint, and a clearly-labelled demo narration channel) plus a presenter CLI (`demo.py`) that owns a dedicated demo database and backend process. The frontend consumes the narration channel only while a demo is active; otherwise its fetch-once behaviour is unchanged. Every classification shown comes from a real scan of the loopback lab target.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / SQLite / `unittest` + `TestClient` (backend); React 19 / Vite / lucide-react (frontend); stdlib `urllib.request` for the CLI (no new dependency).

**Spec:** `docs/superpowers/specs/2026-11-21-guided-demo-design.md` (read it alongside this plan).

## Global Constraints

- Classification labels stay frozen: `BASELINE`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, `NO DRIFT`. No rule changes in `drift.py` beyond exporting the sentinel constant.
- First scan of a target emits no drift events (BASELINE = silence); a no-change rescan emits exactly one `NO DRIFT` event.
- Redaction rule unchanged: tokenise sensitive values before any AI call; the token map never leaves the local environment. The demo only displays output from `GET /api/scans/{id}/evidence/redacted`.
- Scan only authorised lab targets bound to `127.0.0.1`. Demo target: `eservices-lab`, `https://127.0.0.1:8443`, approved ports `8443, 8080`, scope `tls, network, http_api`.
- No fabricated or seeded findings in the live app. Every UI row comes from a persisted API record.
- Demo database is `demo-driftguard.db` at repo root only. The labelled `S0`–`S9` evaluation database and `lab/sequence.py` marks are never touched by the demo.
- API runs in local-research mode (no `DRIFTGUARD_AUTH_SECRET`) for the demo; role gates still exist and are tested.
- Canonical backend suite command from the RAM workspace: `cd /dev/shm/driftguard/backend && /mnt/data/eservices-lab/backend/.venv/bin/python -m unittest discover -s tests` (baseline: 127 tests OK).
- Workspace is `/dev/shm/driftguard` (RAM-backed, lost on reboot). Commit **and push** to `origin main` at the end of every task.

## Review Focus

These are the spec-implied failure modes no task's happy-path tests naturally exercise. Each is pinned by a test in the owning task.

1. **Two demo runs back-to-back hit the scan rate limit** (six scans per run vs the default `10/minute`) → Task 4 test asserts the demo backend is started with `DRIFTGUARD_SCAN_RATE_LIMIT=60/minute`.
2. **A leftover demo DB makes "NEW" classify as RECURRING** → Task 4 test asserts a plain run refuses an existing demo DB with a `--reset` instruction; `--reset` deletes only the exact `demo-driftguard.db` filename.
3. **An inherited shell `DRIFTGUARD_AUTH_SECRET` silently breaks the unauthenticated demo** → Task 4 test asserts the child environment removes auth variables.
4. **A stale lab flaw leaks into the baseline** → Task 4 test asserts preflight runs `domain.py reset eservices-lab` before the first scan and checks the target answers.
5. **The redacted sample leaks a raw loopback address or the token map** → Task 4 test asserts `safe_redacted_sample()` rejects raw `127.0.0.1`/`localhost` and accepts only endpoint output; the endpoint never returns the token map.

---

### Task 1: Persist the NO DRIFT event in the engine

**Files:**
- Modify: `backend/driftguard/drift.py` (add exported constant only)
- Modify: `backend/driftguard/scanner/engine.py:199-218` (`_record_drift`)
- Test: `backend/tests/test_scanner_engine.py`

**Interfaces:**
- Consumes: `drift.classify(current, previous, earlier) -> dict[str, str]`; existing `models.DriftEvent(target_id, scan_id, evidence_fingerprint, classification)`.
- Produces: `drift.NO_DRIFT_FINGERPRINT = "NO DRIFT"` (documented sentinel, no `/`, no collision with `<target>/<area>/<check-id>`); `_record_drift` writes one event with that fingerprint and `classification="NO DRIFT"` when `classify()` returns `{}` and a previous scan exists. First scan still writes nothing.

- [ ] **Step 1: Write the failing tests**

Add to the drift/engine test class (reuse `_DBTestCase`, `_make_target`, and the `@mock.patch` decorator stack around `test_drift_classified_against_previous_scan`; mock `nmap` observations to control fingerprints):

```python
def test_no_change_rescan_records_one_no_drift_event(self): ...
# previous scan has "svc/Network/port-open", current scan has the same;
# assert one event for this scan, fingerprint == NO_DRIFT_FINGERPRINT,
# classification == "NO DRIFT"

def test_no_drift_sentinel_is_not_a_finding_key(self): ...
# assert NO_DRIFT_FINGERPRINT == "NO DRIFT", "/" not in it,
# and "NO DRIFT" in drift.DRIFT_TYPES

def test_rescan_with_changes_does_not_record_no_drift(self): ...
# previous has the fingerprint, current has none;
# assert exactly one "FIXED" event and no sentinel event

def test_repeated_no_change_scans_each_record_their_own_event(self): ...
# three scans with identical evidence; scans 2 and 3 each have one NO DRIFT event
```

Keep `test_no_previous_scan_produces_evidence_but_no_drift_events` and `backend/tests/test_drift.py::test_no_drift_has_no_fingerprint_event` unchanged: `classify()` still returns an empty dict for an empty change set; the caller now persists the already-specified NO DRIFT event.

- [ ] **Step 2: Run the targeted test and verify it fails**

Run: `cd /dev/shm/driftguard/backend && /mnt/data/eservices-lab/backend/.venv/bin/python -m unittest discover -s tests -p 'test_scanner_engine.py' -v`
Expected: FAIL on the new tests (missing import/constant, no event recorded).

- [ ] **Step 3: Implement the minimal change**

In `drift.py` add `NO_DRIFT_FINGERPRINT = "NO DRIFT"` with a one-line docstring explaining it is the caller-level sentinel for the empty change set. In `_record_drift`, after `classified = drift.classify(...)`, if `not classified`, add a single `models.DriftEvent(..., evidence_fingerprint=drift.NO_DRIFT_FINGERPRINT, classification="NO DRIFT")` and return. Do not edit the classification algorithm.

- [ ] **Step 4: Run targeted and full suites**

Run the Step 2 command → PASS. Then run the canonical full suite → 127 + new tests OK.

- [ ] **Step 5: Commit and push**

```bash
git add backend/driftguard/drift.py backend/driftguard/scanner/engine.py backend/tests/test_scanner_engine.py
git commit -m "feat(engine): persist NO DRIFT event on unchanged rescan"
git push origin main
```

---

### Task 2: Drift history read endpoint

**Files:**
- Modify: `backend/driftguard/schemas.py` (add `DriftRead`)
- Modify: `backend/driftguard/main.py` (add route after `list_scans`)
- Create: `backend/tests/test_drift_api.py`

**Interfaces:**
- Consumes: `models.DriftEvent`, `models.Scan`; `require_role("viewer")`, `get_db`, `audit` as used in `main.py`.
- Produces: `GET /api/targets/{target_id}/drift -> list[DriftRead]`, ordered `recorded_at DESC, id DESC`. `DriftRead` fields: `id: int`, `scan_id: int`, `evidence_fingerprint: str`, `classification: str`, `recorded_at: datetime`, `scan_label: str | None`, `scan_status: str`, `observed_at: datetime` (`Scan.completed_at or Scan.started_at`). Returns `[]` for a fresh target; `404` for an unknown target.

- [ ] **Step 1: Write the failing tests**

Create `test_drift_api.py` using the `TestClient` + `dependency_overrides` harness from `test_api.py:14-42`. Seed target/scan/event rows directly through the overridden session factory. Tests:

```python
def test_fresh_target_has_no_drift_events(self): ...
# 200, body == []

def test_events_are_newest_first_with_scan_context(self): ...
# two scans with labels/status/completed_at and one event each;
# assert order, scan_label, scan_status, observed_at, classification

def test_unknown_target_returns_404(self): ...

def test_auth_mode_requires_a_token_and_allows_a_viewer(self): ...
# mirror test_auth.py: set DRIFTGUARD_AUTH_SECRET, reset limiter,
# create viewer via bootstrap + token; GET without token -> 401, with token -> 200
```

- [ ] **Step 2: Run targeted tests and verify they fail**

Run: `.../python -m unittest discover -s tests -p 'test_drift_api.py' -v`
Expected: FAIL (404 route not found).

- [ ] **Step 3: Implement schema and endpoint**

Add `DriftRead` to `schemas.py` next to `ScanRead` (`ConfigDict(from_attributes=True)`). In `main.py`, query `select(DriftEvent, Scan).join(Scan, DriftEvent.scan_id == Scan.id).where(DriftEvent.target_id == target_id).order_by(DriftEvent.recorded_at.desc(), DriftEvent.id.desc())`, check the target with `db.get(models.Target, target_id)` first, and build response dicts from each `(event, scan)` pair. Apply `Depends(require_role("viewer"))`.

- [ ] **Step 4: Run targeted and full suites**

Targeted → PASS; canonical full suite → all green.

- [ ] **Step 5: Commit and push**

```bash
git add backend/driftguard/schemas.py backend/driftguard/main.py backend/tests/test_drift_api.py
git commit -m "feat(api): expose per-target drift history"
git push origin main
```

---

### Task 3: Demo narration channel

**Files:**
- Create: `backend/driftguard/demo_channel.py`
- Modify: `backend/driftguard/schemas.py` (add `DemoStep`, `DemoStepUpdate`)
- Modify: `backend/driftguard/main.py` (add GET/POST `/api/demo/step`)
- Create: `backend/tests/test_demo_channel.py`

**Interfaces:**
- Consumes: `require_role`, `Principal`, `ConfigDict` patterns from Tasks 2.
- Produces: `demo_channel.get_step() -> dict`, `set_step(update: dict) -> dict`, `clear_step() -> None` backed by a module-level dict + `threading.Lock`. `POST /api/demo/step` accepts `DemoStepUpdate {step: int | None, total: int, title: str | None, explanation: str | None, page: Literal["dashboard","findings","drift","reports"] | None}` (all fields optional except `total` default `8`) and returns `DemoStep` with `updated_at: datetime | None`; `step: null` clears narration. `GET /api/demo/step` returns the same shape (`step: null` before any post). POST requires `operator`; GET requires `viewer`.

- [ ] **Step 1: Write the failing tests**

In `test_demo_channel.py`, call `demo_channel.clear_step()` in `setUp`/`tearDown`. Tests:

```python
def test_initial_state_has_no_step(self): ...
def test_post_and_clear_roundtrip(self): ...
# post step 3 with title/explanation/page="drift"; GET matches;
# POST with step=None clears; GET step is None

def test_post_requires_operator_and_get_requires_viewer(self): ...
# auth-on harness from test_auth.py; viewer POST -> 403, operator POST -> 200,
# GET without token -> 401, viewer GET -> 200
```

- [ ] **Step 2: Run targeted tests and verify they fail**

Run: `.../python -m unittest discover -s tests -p 'test_demo_channel.py' -v` → FAIL (module/routes missing).

- [ ] **Step 3: Implement channel and endpoints**

`demo_channel.py` stores a plain dict copy of the validated update plus `updated_at = datetime.now(timezone.utc)`; `clear_step()` resets to `{"step": None, "total": 8, "title": None, "explanation": None, "page": None, "updated_at": None}`. Add routes in `main.py` with a comment that this is a presenter channel, not assessment data, and that no finding/classification is written through it. Do not audit narration into the evidence log.

- [ ] **Step 4: Run targeted and full suites**

Targeted → PASS; canonical full suite → all green.

- [ ] **Step 5: Commit and push**

```bash
git add backend/driftguard/demo_channel.py backend/driftguard/schemas.py backend/driftguard/main.py backend/tests/test_demo_channel.py
git commit -m "feat(api): add demo narration channel"
git push origin main
```

---

### Task 4: `demo.py` presenter CLI

**Files:**
- Create: `demo.py` (repo root)
- Create: `backend/tests/test_demo_script.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `POST /api/targets`, `POST /api/targets/{id}/scans?label=...`, `GET /api/targets/{id}/scans`, `GET /api/targets/{id}/drift`, `GET /api/scans/{id}/evidence/redacted`, `POST /api/demo/step`, `/ready`.
- Produces (importable pure helpers, so tests need no server): `ROOT: Path`, `DB_FILENAME = "demo-driftguard.db"`, `demo_database_url(root: Path = ROOT) -> str`, `build_env(db_url: str) -> dict[str, str]`, `assert_fresh_db(path: Path, allow_existing: bool) -> None`, `preflight_commands() -> list[tuple[str, ...]]`, `narration(step_name: str) -> dict`, `assert_redacted_sample(rows: list[dict]) -> str`, `main(argv: list[str] | None = None) -> int`. `narration()` returns exactly the `DemoStepUpdate` payload fields for the eight step names `register`, `baseline`, `no_drift`, `new`, `persistent`, `fixed`, `recurring`, `redacted_export`.

- [ ] **Step 1: Write failing tests for the pure helpers**

In `test_demo_script.py`, insert `ROOT` into `sys.path` and import `demo`. Tests:

```python
def test_demo_database_url_uses_the_dedicated_filename(self): ...
# ends with "/demo-driftguard.db"; never the repository driftguard.db

def test_build_env_strips_auth_and_raises_scan_limit(self): ...
# seed env with DRIFTGUARD_AUTH_SECRET / _REQUIRED; assert absent in result,
# DRIFTGUARD_DATABASE_URL == supplied URL, DRIFTGUARD_SCAN_RATE_LIMIT == "60/minute"

def test_assert_fresh_db_refuses_leftover_database(self): ...
# existing path without allow_existing -> raises with "--reset" in message;
# allow_existing=True -> no raise; wrong filename e.g. driftguard.db -> always raises

def test_narration_covers_eight_frozen_steps(self): ...
# keys exactly the eight names; total == 8; no_drift explanation mentions
# "no change" and "NO DRIFT"; page values are valid literals

def test_preflight_resets_lab_without_touching_marks(self): ...
# preflight_commands() == [("reset", "eservices-lab")]; no "mark" command

def test_redacted_sample_rejects_raw_loopback_address(self): ...
# row with resource "https://127.0.0.1:8443" -> raises;
# row with "URL_abc123" -> returns a printable line containing the token
```

- [ ] **Step 2: Run targeted tests and verify they fail**

Run: `.../python -m unittest discover -s tests -p 'test_demo_script.py' -v` → FAIL (module missing).

- [ ] **Step 3: Implement the pure helpers**

Use only stdlib (`argparse`, `json`, `os`, `shutil`, `subprocess`, `sys`, `time`, `urllib.request`, `webbrowser`, `datetime`, `pathlib`). Write `ROOT`, `DB_FILENAME`, `demo_database_url()`, `build_env()` (which sets `DRIFTGUARD_DATABASE_URL`, `DRIFTGUARD_SCAN_RATE_LIMIT=60/minute`, and removes auth variables), `assert_fresh_db()` (deletes only the exact demo filename; refuses other databases), `preflight_commands()` (returns `[("reset", "eservices-lab")]`), `narration()` (the eight frozen step payloads), and `assert_redacted_sample()` (rejects raw `127.0.0.1`/`localhost`, returns a printable token line). No network calls in this step. Checkable result: the targeted tests pass.

- [ ] **Step 4: Add the CLI flags and backend lifecycle**

Add `argparse` flags `--reset`, `--no-server`, `--allow-existing-db`, `--api-url` (default `http://127.0.0.1:8000`), `--ui-url` (default `http://127.0.0.1:5173`). Default run refuses an existing demo DB unless `--reset`; `--no-server` additionally requires `--allow-existing-db` because it cannot own the DB lifecycle. Default server: `subprocess.Popen([venv_python, "-m", "uvicorn", "driftguard.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=<repo>/backend, env=build_env(url), start_new_session=True)`; wait for `/ready` (30 s); terminate the process group in `finally`. Checkable result: `python3 demo.py --reset --help` prints the flags and starting the script waits for `/ready`.

- [ ] **Step 5: Implement preflight and target registration**

Check `/ready`, that `https://127.0.0.1:8443` answers, and that `nmap`, `httpx` and the testssl binary (`DRIFTGUARD_TESTSSL_BIN` or `shutil.which`) resolve; fail with an explicit message otherwise. Open `<ui-url>/?demo=1` with `webbrowser.open` so the dashboard arms demo narration without any manual click (print the URL when running headless). Execute `preflight_commands()` via `<sys.executable> lab/domain.py ...` before the first scan; never call `domain.py mark`. Register the target once via `POST /api/targets` with `name="eservices-lab"`, `address="https://127.0.0.1:8443"`, `target_type="web"`, `authorization_status="authorized"`, `authorized_by="guided demo (local researcher)"`, `authorized_at=<UTC now ISO>`, `authorization_basis="LAB-DEMO-2026-11"`, `approved_scope=["tls","network","http_api"]`, `approved_ports=[8443,8080]`, `status="active"`. Checkable result: a stopped-lab preflight fails loudly without queueing a scan.

- [ ] **Step 6: Implement the eight-step narration and assertions**

For each step in order: `POST /api/demo/step` using `narration(name)`, print the narration line, then act. Scans use labels `DEMO-0`…`DEMO-5` (never `S0`–`S9`); poll `GET /api/targets/{id}/scans` every 1 s up to 300 s for the queued scan id, failing loudly with `scan.error` on `failed`/`completed_with_errors`. Scenario control: `baseline`/`no_drift` = clean; `new`/`persistent` = `domain.py on eservices-lab tls-legacy` before the scan; `fixed` = `off`; `recurring` = `on`. Assertions use `GET /api/targets/{id}/drift` filtered to that scan: baseline → no events; no_drift → exactly one `NO DRIFT` sentinel event; new/persistent/fixed/recurring → the event with fingerprint `eservices-lab/TLS/tls-legacy` has that classification. Print expected vs actual and exit non-zero on failure. Checkable result: each step prints its assertion outcome before the next line.

- [ ] **Step 7: Implement redacted export, cleanup, and ignores**

Final step: `GET /api/scans/{id}/evidence/redacted`, pass rows through `assert_redacted_sample()`, print up to three tokenised values and the explicit statement that the token map stays local. Never call `redact()` or print a token map. In `finally`, `POST /api/demo/step` with `{"step": None, "total": 8}` so the UI strip disappears, then stop the demo backend. Add `demo-driftguard.db`, `demo-driftguard.db-*`, and `.driftguard_redaction_secret` to `.gitignore`. Checkable result: `git status` does not show demo DB or secret files.

- [ ] **Step 8: Run targeted tests, then full suite**

Targeted → PASS; canonical full suite → all green.

- [ ] **Step 9: Commit and push**

```bash
git add demo.py backend/tests/test_demo_script.py .gitignore
git commit -m "feat(demo): guided demo CLI with isolated database and narration"
git push origin main
```

---

### Task 5: Narration strip, live refresh, and real drift history UI

**Files:**
- Create: `frontend/src/DemoStrip.jsx`, `frontend/src/DriftHistory.jsx`
- Modify: `frontend/src/App.jsx` (state, polling, conditional refetch, route replacement)
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `GET /api/demo/step` (Task 3 shape) and `GET /api/targets/{id}/drift` (Task 2 shape); existing `api()` helper and `TargetRead[]`.
- Produces: `<DemoStrip step={DemoStep | null} />` and `<DriftHistory events={DriftRead[]} targets={TargetRead[]} loading={boolean} />`; `App` holds `demoStep`, `demoArmed` (initialised from `?demo=1` in the URL) and `driftEvents` state. Arming comes from `demo.py` opening the UI at `?demo=1`; a normal URL never arms polling.

- [ ] **Step 1: Invoke the frontend-design skill**

Before writing UI code, run the `frontend-design` skill and apply its guidance to the two new components and the strip/timeline styles. Keep the existing dark practitioner dashboard design system; no templated AI look, no invented statuses.

- [ ] **Step 2: Implement the two components**

`DemoStrip` renders nothing when `step === null`; otherwise shows `STEP step/total`, title, one-line explanation, and a subtle progress rule. `DriftHistory` groups real events by target, renders a newest-first timeline with frozen-label badges (including `NO DRIFT`), scan reference (`scan_label` or `#scan_id`), observed time, fingerprint, and a frozen-label legend; a proper empty state when there are no events. Checkable result: both modules export a default component and contain no hard-coded findings.

- [ ] **Step 3: Wire App state, polling, and the drift route**

In `App.jsx`: extend `refresh()` to fetch `/api/targets/{id}/drift` for each target and `setDriftEvents(...)`; replace the drift `CapabilityPage` with `<DriftHistory .../>`. Initialise `demoArmed` from `new URLSearchParams(window.location.search).get('demo') === '1'` and `demoStep` as `null`. Add a `useEffect` that polls `GET /api/demo/step` every 1000 ms **only while `demoArmed`** (a normal URL never polls). On a changed `updated_at`, call `refresh(true)` once and `setPage(step.page)` when `step.page` is provided. Track whether a step has been seen in a ref; when the response has `step === null` after a step was seen, set `demoArmed = false` so polling stops automatically at the end of a run. Show `<DemoStrip>` at the top of `page-wrap` only when a demo step is present. Checkable result: with no `?demo=1`, DevTools shows no `/api/demo/step` requests; with it, one appears per second and data refetches once per step change.

- [ ] **Step 4: Verify the frontend builds**

Run: `cd /dev/shm/driftguard/frontend && npm ci && npm run build`
Expected: Vite build completes with no errors. (No frontend test harness exists; live verification happens in Task 6.)

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/DemoStrip.jsx frontend/src/DriftHistory.jsx frontend/src/App.jsx frontend/src/styles.css
git commit -m "feat(ui): demo narration strip and real drift history timeline"
git push origin main
```

---

### Task 6: Recording procedure and end-to-end verification

**Files:**
- Create: `docs/demo-recording.md`
- Modify: `README.md` (short "Guided demo" quickstart)

**Interfaces:**
- Consumes: Task 4 CLI and Task 5 UI.

- [ ] **Step 1: Write the recording procedure**

Document: clean-take checklist (containers up, `python3 lab/domain.py verify`, `python3 demo.py --reset` first, dashboard open at the `?demo=1` URL the script opens, no terminal clutter, narration strip visible); capture the dashboard/drift pages and console narration with OBS or the GNOME recorder; artefact stored outside git at `/media/anthonyl/4AA46004A45FF0C5/DriftGuard/recordings/` (stage in `/dev/shm` if sda4 is read-only, then copy); verification = the recording plays end-to-end and every asserted classification is visible. Add the README quickstart pointing at `demo.py --reset` and the doc.

- [ ] **Step 2: Run full automated verification**

Run from the RAM workspace:

```bash
cd /dev/shm/driftguard/backend && /mnt/data/eservices-lab/backend/.venv/bin/python -m unittest discover -s tests
cd /dev/shm/driftguard/frontend && npm run build
```

Expected: all backend tests OK; frontend build clean.

- [ ] **Step 3: Run the demo twice consecutively**

```bash
cd /dev/shm/driftguard && python3 demo.py --reset
cd /dev/shm/driftguard && python3 demo.py            # must refuse the leftover DB with a --reset hint
cd /dev/shm/driftguard && python3 demo.py --reset
```

Expected: both `--reset` runs print all eight steps, each assertion passes (including exactly one `NO DRIFT` event), no 429s, and the narration strip disappears at the end; the plain run fails immediately without scanning. Confirm the demo DB exists at repo root and the evaluation DB was not modified.

- [ ] **Step 4: Confirm lab/evaluation reproducibility and capture the recording**

Run `python3 lab/sequence.py` and `python3 backend/evaluate.py` from the repo root, then `python3 lab/domain.py reset`; expected detection accuracy 1.0 / FPR 0.0 as previously recorded. Capture the clean take per the new doc and verify playback. Then commit the docs and push.

```bash
git add docs/demo-recording.md README.md
git commit -m "docs(demo): recording procedure and guided demo quickstart"
git push origin main
```
