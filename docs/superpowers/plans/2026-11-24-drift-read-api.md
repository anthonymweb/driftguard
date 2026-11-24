# Drift Read API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the drift-comparison data the console needs — target last-scan/refusal state, per-target history, global stats, and read-only evaluation — and stop incomplete scans from corrupting drift and accuracy.

**Architecture:** Additive FastAPI read endpoints over the existing SQLAlchemy models, with a small presenter for `TargetRead` computed fields and a read-only evaluation service. One correctness change in the engine: only `completed` scans participate in comparison, and drift is recorded only after the final scan status is known.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, SQLite, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-24-drift-console-design.md`

## Global Constraints

- Only `completed` scans are comparable. `completed_with_errors` and `failed` scans are never compared and never write drift events.
- Do not change `drift.classify` semantics or the frozen labels: `BASELINE`, `NO DRIFT`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`.
- `NO DRIFT` is derived: a comparable non-baseline scan with zero drift events.
- Existing response fields and routes must keep working; changes are additive.
- Every new endpoint uses the same `require_role("viewer")` auth dependency as the existing reads.
- `/api/evaluation` is read-only: it must not write to the database or the lab.
- Run the suite from `backend` with `.venv/bin/python -m unittest discover -s tests`.

## Review Focus

- A scan that fails after a prior observation must not write `FIXED` drift.
- A `completed_with_errors` scan must not become the comparison base for the next scan.
- A duplicate scan label must block evaluation rather than produce plausible-looking accuracy numbers.
- History must never return another target's scans or evidence.
- Evaluation must fail honestly when the lab ground truth is unavailable, and must not mutate either side.

## File Structure

- `backend/driftguard/schemas.py` — response models (`TargetRead` additions, history, stats, evaluation).
- `backend/driftguard/presenters.py` — `target_read`, latest-scan lookup.
- `backend/driftguard/scanner/engine.py` — `scannability_reasons`, eligibility rules.
- `backend/driftguard/main.py` — new routes and target responses.
- `backend/driftguard/evaluation_service.py` — read-only evaluation loader and duplicate-label guard.
- `backend/tests/support.py` — shared API test base.
- `backend/tests/test_target_read.py`
- `backend/tests/test_history.py`
- `backend/tests/test_stats.py`
- `backend/tests/test_evaluation_api.py`

---

### Task 1: Target read model, refusal reasons, last scan

**Files:**
- Create: `backend/driftguard/presenters.py`
- Modify: `backend/driftguard/schemas.py`
- Modify: `backend/driftguard/scanner/engine.py:52-71`
- Modify: `backend/driftguard/main.py:194-225`
- Test: `backend/tests/support.py`, `backend/tests/test_target_read.py`

**Interfaces:**
- Consumes: `models.Target`, `models.Scan`, `models.Evidence`.
- Produces:
  - `scannability_reasons(target: models.Target) -> list[str]`
  - `ensure_scannable(target: models.Target) -> None` (unchanged behaviour: raises `ScanRefused` with the reasons joined by `"; "`)
  - `ScanSummary` (`id`, `status`, `started_at`, `completed_at`)
  - `TargetRead` gains `last_scan: ScanSummary | None`, `scannable: bool`, `refusal_reasons: list[str]`
  - `presenters.target_read(target: models.Target, last_scan: models.Scan | None) -> TargetRead`
  - `presenters.latest_scan_for(db: Session, target_id: int) -> models.Scan | None`
  - `presenters.latest_scans_for(db: Session, target_ids: list[int]) -> dict[int, models.Scan]`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/support.py` with the same temporary SQLite setup as `test_api.py`:

```python
import unittest
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard import models
from driftguard.database import Base, get_db, get_session_factory
from driftguard.main import app


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        def override_db():
            db = self.factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = lambda: self.factory
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def create_target(self, **overrides):
        payload = {
            "name": "Local lab", "address": "https://localhost:8443", "target_type": "web",
            "approved_scope": ["tls"], "approved_ports": [8443],
        }
        payload.update(overrides)
        response = self.client.post("/api/targets", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()
```

Create `backend/tests/test_target_read.py`:

```python
from datetime import datetime, timezone

from driftguard import models
from tests.support import ApiTestCase


class TargetReadTests(ApiTestCase):
    def test_pending_unscoped_target_reports_every_refusal_reason(self):
        target = self.create_target(approved_scope=[], approved_ports=[])
        body = self.client.get(f"/api/targets/{target['id']}").json()
        self.assertFalse(body["scannable"])
        self.assertIsNone(body["last_scan"])
        self.assertIn("target must be explicitly authorized", body["refusal_reasons"])
        self.assertIn("target has no approved assessment scope", body["refusal_reasons"])

    def test_authorized_scoped_target_is_scannable_with_no_reasons(self):
        target = self.create_target(
            authorization_status="authorized", authorized_by="A. Owner",
            authorized_at="2026-11-12T09:00:00Z", authorization_basis="LAB-2026-01",
        )
        body = self.client.get(f"/api/targets/{target['id']}").json()
        self.assertTrue(body["scannable"])
        self.assertEqual(body["refusal_reasons"], [])

    def test_last_scan_is_the_newest_attempt(self):
        target = self.create_target()
        db = self.factory()
        db.add(models.Scan(target_id=target["id"], status="completed"))
        db.add(models.Scan(target_id=target["id"], status="failed"))
        db.commit()
        body = self.client.get(f"/api/targets/{target['id']}").json()
        self.assertEqual(body["last_scan"]["status"], "failed")
        db.close()

    def test_target_list_includes_last_scan_for_each_target(self):
        first = self.create_target()
        second = self.create_target(name="Second")
        db = self.factory()
        db.add(models.Scan(target_id=first["id"], status="completed"))
        db.commit()
        db.close()
        rows = {row["id"]: row for row in self.client.get("/api/targets").json()}
        self.assertEqual(rows[first["id"]]["last_scan"]["status"], "completed")
        self.assertIsNone(rows[second["id"]]["last_scan"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_target_read.py' -v`
Expected: FAIL because `scannable`, `last_scan`, and `refusal_reasons` are missing.

- [ ] **Step 3: Implement the presenter and reasons helper**

In `schemas.py`, add `ScanSummary` and extend `TargetRead`:

```python
class ScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    started_at: datetime
    completed_at: datetime | None


class TargetRead(BaseModel):
    # ... existing fields unchanged ...
    last_scan: ScanSummary | None = None
    scannable: bool = False
    refusal_reasons: list[str] = Field(default_factory=list)
```

In `engine.py`, split the existing body of `ensure_scannable` into `scannability_reasons(target)` (returns the list, same order and messages) and `ensure_scannable(target)` (raises when the list is non-empty). Do not change any message text.

Create `presenters.py`:

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .scanner.engine import scannability_reasons
from .schemas import ScanSummary, TargetRead


def latest_scan_for(db: Session, target_id: int) -> models.Scan | None:
    return db.scalar(
        select(models.Scan)
        .where(models.Scan.target_id == target_id)
        .order_by(models.Scan.id.desc())
        .limit(1)
    )


def latest_scans_for(db: Session, target_ids: list[int]) -> dict[int, models.Scan]:
    if not target_ids:
        return {}
    newest = (
        select(models.Scan.target_id, func.max(models.Scan.id).label("max_id"))
        .where(models.Scan.target_id.in_(target_ids))
        .group_by(models.Scan.target_id)
        .subquery()
    )
    rows = db.scalars(select(models.Scan).join(newest, models.Scan.id == newest.c.max_id))
    return {row.target_id: row for row in rows}


def target_read(target: models.Target, last_scan: models.Scan | None) -> TargetRead:
    reasons = scannability_reasons(target)
    return TargetRead(
        id=target.id,
        name=target.name,
        address=target.address,
        target_type=target.target_type,
        authorization_status=target.authorization_status,
        authorized_by=target.authorized_by,
        authorized_at=target.authorized_at,
        authorization_basis=target.authorization_basis,
        approved_scope=target.approved_scope,
        approved_ports=target.approved_ports,
        discovery_enabled=target.discovery_enabled,
        discovery_wordlist=target.discovery_wordlist,
        status=target.status,
        created_at=target.created_at,
        last_scan=ScanSummary.model_validate(last_scan) if last_scan else None,
        scannable=not reasons,
        refusal_reasons=reasons,
    )
```

In `main.py`, import the presenter and return `presenters.target_read(...)` from `register_target`, `list_targets`, and `get_target`. `list_targets` uses `latest_scans_for` with all ids. `get_target` uses `latest_scan_for`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_target_read.py' -v`
Expected: PASS.

Then run the whole suite: `cd backend && .venv/bin/python -m unittest discover -s tests`
Expected: PASS (127 existing plus new).

- [ ] **Step 5: Commit**

```bash
git add backend/driftguard/schemas.py backend/driftguard/presenters.py \
  backend/driftguard/scanner/engine.py backend/driftguard/main.py \
  backend/tests/support.py backend/tests/test_target_read.py
git commit -m "feat(api): report scannability and last scan on targets"
```

---

### Task 2: Only completed scans are compared

**Files:**
- Modify: `backend/driftguard/scanner/engine.py:180-220`, `:326-340`
- Test: `backend/tests/test_scanner_engine.py`

**Interfaces:**
- Consumes: `drift.classify`, `models.Scan`, `models.DriftEvent`.
- Produces: the rule that only `status == "completed"` scans are comparison bases and only completed scans write `DriftEvent` rows.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_scanner_engine.py` inside `EngineAssessmentTests` (reuse `_make_target` and the existing mocks):

```python
@mock.patch("driftguard.scanner.engine.time.sleep")
@mock.patch("driftguard.scanner.engine.tools.run_httpx")
@mock.patch("driftguard.scanner.engine.tools.run_testssl")
@mock.patch("driftguard.scanner.engine.tools.run_nmap")
def test_failed_scan_writes_no_fixed_drift(self, m_nmap, m_testssl, m_httpx, m_sleep):
    from driftguard.scanner.tools import ToolError
    db = self.db()
    target = self._make_target(db, approved_scope=["network"], approved_ports=[8443])
    previous = models.Scan(target_id=target.id, status="completed")
    db.add(previous)
    db.flush()
    db.add(models.Evidence(scan_id=previous.id, fingerprint="svc/Network/port-open",
                           category="Network", title="Unexpected open port",
                           severity="High", resource="8081", details={}))
    db.commit()
    m_nmap.side_effect = ToolError("nmap boom")

    scan = assess_target(db, target)

    self.assertEqual(scan.status, "failed")
    events = list(db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id == scan.id)))
    self.assertEqual(events, [])
    db.close()

@mock.patch("driftguard.scanner.engine.time.sleep")
@mock.patch("driftguard.scanner.engine.tools.run_httpx")
@mock.patch("driftguard.scanner.engine.tools.run_testssl")
@mock.patch("driftguard.scanner.engine.tools.run_nmap")
def test_completed_with_errors_writes_no_drift(self, m_nmap, m_testssl, m_httpx, m_sleep):
    from driftguard.scanner.tools import ToolError
    db = self.db()
    target = self._make_target(db, approved_scope=["network", "http_api"], approved_ports=[8443])
    previous = models.Scan(target_id=target.id, status="completed")
    db.add(previous)
    db.flush()
    db.add(models.Evidence(scan_id=previous.id, fingerprint="svc/Network/port-open",
                           category="Network", title="Unexpected open port",
                           severity="High", resource="8081", details={}))
    db.commit()
    m_nmap.side_effect = ToolError("nmap boom")
    m_httpx.return_value = {"status_code": 200, "scheme": "https", "location": None,
                            "final_url": "https://svc.test:8443"}

    scan = assess_target(db, target)

    self.assertEqual(scan.status, "completed_with_errors")
    events = list(db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id == scan.id)))
    self.assertEqual(events, [])
    db.close()

@mock.patch("driftguard.scanner.engine.time.sleep")
@mock.patch("driftguard.scanner.engine.tools.run_httpx")
@mock.patch("driftguard.scanner.engine.tools.run_testssl")
@mock.patch("driftguard.scanner.engine.tools.run_nmap")
def test_partial_scan_is_not_a_comparison_base(self, m_nmap, m_testssl, m_httpx, m_sleep):
    db = self.db()
    target = self._make_target(db, approved_scope=["network"], approved_ports=[8443])
    clean = models.Scan(target_id=target.id, status="completed")
    partial = models.Scan(target_id=target.id, status="completed_with_errors")
    db.add_all([clean, partial])
    db.flush()
    db.add(models.Evidence(scan_id=partial.id, fingerprint="svc/Network/port-open",
                           category="Network", title="Unexpected open port",
                           severity="High", resource="8081", details={}))
    db.commit()
    m_nmap.return_value = {"open_ports": []}

    scan = assess_target(db, target)

    # The next completed scan with no evidence must compare against `clean`
    # (empty), not `partial`; otherwise port-open would be reported FIXED.
    self.assertEqual(scan.status, "completed")
    events = list(db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id == scan.id)))
    self.assertEqual(events, [])
    db.close()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_scanner_engine.py' -v`
Expected: FAIL — the failed/partial scans currently write drift, and the partial scan is a comparison base.

- [ ] **Step 3: Implement the eligibility rule**

In `_completed_scans_before`, change the status filter to exactly:

```python
models.Scan.status == "completed",
```

In `assess_target`, move `_record_drift(db, target, scan)` from before the status decision to after it, and guard it:

```python
if scan.status == "completed":
    _record_drift(db, target, scan)
```

Do not change `drift.classify`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_scanner_engine.py' -v`
Expected: PASS.

Run the whole suite: `cd backend && .venv/bin/python -m unittest discover -s tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/driftguard/scanner/engine.py backend/tests/test_scanner_engine.py
git commit -m "fix(scanner): only completed scans are compared"
```

---

### Task 3: Target history endpoint

**Files:**
- Modify: `backend/driftguard/schemas.py`
- Modify: `backend/driftguard/main.py`
- Test: `backend/tests/test_history.py`

**Interfaces:**
- Consumes: `models.Target`, `models.Scan`, `models.Evidence`, `models.DriftEvent`.
- Produces:
  - `DriftEventRead` (`id`, `scan_id`, `evidence_fingerprint`, `classification`, `recorded_at`)
  - `FingerprintMeta` (`title`, `category`, `severity`, `resource`)
  - `DriftCounts` (`NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, all default `0`)
  - `DriftSummary` (`state: Literal["BASELINE", "NO DRIFT", "CHANGED", "INCOMPLETE"]`, `counts: DriftCounts`)
  - `HistoryScan` (`scan: ScanRead`, `comparable: bool`, `evidence: list[EvidenceRead]`, `drift: list[DriftEventRead]`, `summary: DriftSummary`)
  - `TargetHistory` (`target: TargetRead`, `scans: list[HistoryScan]`, `fingerprints: dict[str, FingerprintMeta]`)
  - `GET /api/targets/{target_id}/history?limit=20` (1–100, newest first)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_history.py`:

```python
from datetime import datetime, timezone

from driftguard import models
from tests.support import ApiTestCase


class HistoryTests(ApiTestCase):
    def _seed(self):
        target = self.create_target()
        db = self.factory()
        baseline = models.Scan(target_id=target["id"], status="completed", is_baseline=True)
        changed = models.Scan(target_id=target["id"], status="completed")
        failed = models.Scan(target_id=target["id"], status="failed")
        db.add_all([baseline, changed, failed])
        db.flush()
        fp = "eservices-lab/Network/port-open"
        db.add(models.Evidence(scan_id=baseline.id, fingerprint=fp, category="Network",
                               title="Unexpected open port", severity="High",
                               resource="8081", details={}))
        db.add(models.Evidence(scan_id=changed.id, fingerprint=fp, category="Network",
                               title="Unexpected open port", severity="High",
                               resource="8081", details={}))
        db.add(models.DriftEvent(target_id=target["id"], scan_id=changed.id,
                                 evidence_fingerprint=fp, classification="PERSISTENT"))
        db.commit()
        db.close()
        return target["id"], fp

    def test_history_returns_scans_newest_first_with_summaries(self):
        target_id, fp = self._seed()
        body = self.client.get(f"/api/targets/{target_id}/history").json()
        self.assertEqual([s["scan"]["status"] for s in body["scans"]],
                         ["failed", "completed", "completed"])
        self.assertEqual(body["scans"][0]["summary"]["state"], "INCOMPLETE")
        self.assertFalse(body["scans"][0]["comparable"])
        self.assertEqual(body["scans"][0]["drift"], [])
        self.assertEqual(body["scans"][1]["summary"]["state"], "CHANGED")
        self.assertEqual(body["scans"][1]["summary"]["counts"]["PERSISTENT"], 1)
        self.assertEqual(body["scans"][2]["summary"]["state"], "BASELINE")
        self.assertEqual(body["fingerprints"][fp]["severity"], "High")

    def test_comparable_scan_with_no_change_is_no_drift(self):
        target = self.create_target()
        db = self.factory()
        first = models.Scan(target_id=target["id"], status="completed", is_baseline=True)
        second = models.Scan(target_id=target["id"], status="completed")
        db.add_all([first, second])
        db.commit()
        db.close()
        body = self.client.get(f"/api/targets/{target['id']}/history").json()
        self.assertEqual(body["scans"][0]["summary"]["state"], "NO DRIFT")

    def test_history_is_scoped_to_the_target(self):
        first, _ = self._seed()
        second = self.create_target(name="Other", address="https://other.test:8444")
        body = self.client.get(f"/api/targets/{second['id']}/history").json()
        self.assertEqual(body["scans"], [])

    def test_history_rejects_unknown_target(self):
        self.assertEqual(self.client.get("/api/targets/9999/history").status_code, 404)

    def test_history_limit_is_clamped(self):
        target, _ = self._seed()
        self.assertEqual(self.client.get(f"/api/targets/{target}/history?limit=0").status_code, 422)
        self.assertEqual(self.client.get(f"/api/targets/{target}/history?limit=101").status_code, 422)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_history.py' -v`
Expected: FAIL with 404 for the history route.

- [ ] **Step 3: Implement the schemas and route**

Add these schemas to `schemas.py` (`Literal` is already imported):

```python
class DriftEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scan_id: int
    evidence_fingerprint: str
    classification: str
    recorded_at: datetime


class FingerprintMeta(BaseModel):
    title: str
    category: str
    severity: str
    resource: str


class DriftCounts(BaseModel):
    NEW: int = 0
    PERSISTENT: int = 0
    FIXED: int = 0
    RECURRING: int = 0


class DriftSummary(BaseModel):
    state: Literal["BASELINE", "NO DRIFT", "CHANGED", "INCOMPLETE"]
    counts: DriftCounts = Field(default_factory=DriftCounts)


class HistoryScan(BaseModel):
    scan: ScanRead
    comparable: bool
    evidence: list[EvidenceRead] = Field(default_factory=list)
    drift: list[DriftEventRead] = Field(default_factory=list)
    summary: DriftSummary


class TargetHistory(BaseModel):
    target: TargetRead
    scans: list[HistoryScan] = Field(default_factory=list)
    fingerprints: dict[str, FingerprintMeta] = Field(default_factory=dict)
```

In `main.py` add `Query` to the FastAPI import and implement:

```python
@app.get("/api/targets/{target_id}/history", response_model=TargetHistory)
def target_history(target_id: int, limit: int = Query(20, ge=1, le=100),
                   db: Session = Depends(get_db),
                   principal: Principal = Depends(require_role("viewer"))):
    target = db.get(models.Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    scans = list(db.scalars(
        select(models.Scan).where(models.Scan.target_id == target_id)
        .order_by(models.Scan.id.desc()).limit(limit)))
    scan_ids = [scan.id for scan in scans]
    evidence_by_scan = {scan_id: [] for scan_id in scan_ids}
    drift_by_scan = {scan_id: [] for scan_id in scan_ids}
    if scan_ids:
        for row in db.scalars(select(models.Evidence).where(models.Evidence.scan_id.in_(scan_ids)).order_by(models.Evidence.id)):
            evidence_by_scan[row.scan_id].append(row)
        for row in db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id.in_(scan_ids)).order_by(models.DriftEvent.id)):
            drift_by_scan[row.scan_id].append(row)
    earliest_completed_id = db.scalar(
        select(func.min(models.Scan.id)).where(
            models.Scan.target_id == target_id, models.Scan.status == "completed"
        )
    )
    history_scans = []
    for scan in scans:
        comparable = scan.status == "completed"
        drift_rows = drift_by_scan[scan.id] if comparable else []
        counts = {"NEW": 0, "PERSISTENT": 0, "FIXED": 0, "RECURRING": 0}
        for row in drift_rows:
            if row.classification in counts:
                counts[row.classification] += 1
        if not comparable:
            state = "INCOMPLETE"
        elif scan.is_baseline or scan.id == earliest_completed_id:
            state = "BASELINE"
        elif not drift_rows:
            state = "NO DRIFT"
        else:
            state = "CHANGED"
        history_scans.append(HistoryScan(
            scan=scan,
            comparable=comparable,
            evidence=evidence_by_scan[scan.id],
            drift=drift_rows,
            summary=DriftSummary(state=state, counts=DriftCounts(**counts)),
        ))

    referenced = {ev.fingerprint for rows in evidence_by_scan.values() for ev in rows}
    referenced |= {row.evidence_fingerprint for rows in drift_by_scan.values() for row in rows}
    catalogue: dict[str, FingerprintMeta] = {}
    if referenced:
        for ev in db.scalars(
            select(models.Evidence).where(models.Evidence.fingerprint.in_(referenced))
            .order_by(models.Evidence.id.desc())
        ):
            if ev.fingerprint not in catalogue:
                catalogue[ev.fingerprint] = FingerprintMeta(
                    title=ev.title, category=ev.category,
                    severity=ev.severity, resource=ev.resource,
                )

    return TargetHistory(
        target=presenters.target_read(target, presenters.latest_scan_for(db, target_id)),
        scans=history_scans,
        fingerprints=catalogue,
    )
```

Rules inside the route:
- `comparable = scan.status == "completed"`.
- `drift` is `[]` when not comparable.
- `earliest_completed_id` = `db.scalar(select(func.min(models.Scan.id)).where(target_id, status == "completed"))`.
- `summary.state`: `INCOMPLETE` if not comparable; else `BASELINE` if `scan.is_baseline or scan.id == earliest_completed_id`; else `NO DRIFT` if no drift rows; else `CHANGED`.
- `summary.counts` starts at zero for `NEW`, `PERSISTENT`, `FIXED`, `RECURRING` and increments from the returned drift rows.
- Catalogue: for each fingerprint referenced by the returned evidence or drift, take the newest `Evidence` row with that fingerprint (query by `Evidence.fingerprint.in_(referenced)` ordered by `Evidence.id.desc()`, first row per fingerprint).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_history.py' -v`
Expected: PASS.

Run the whole suite: `cd backend && .venv/bin/python -m unittest discover -s tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/driftguard/schemas.py backend/driftguard/main.py backend/tests/test_history.py
git commit -m "feat(api): add target drift history endpoint"
```

---

### Task 4: Stats endpoint

**Files:**
- Modify: `backend/driftguard/schemas.py`
- Modify: `backend/driftguard/main.py`
- Test: `backend/tests/test_stats.py`

**Interfaces:**
- Consumes: `models.Target`, `models.Scan`, `models.Evidence`, `models.DriftEvent`, `auth.auth_enabled()`.
- Produces: `StatsRead` and `GET /api/stats` returning
  `{targets, scans, evidence, drift_events, auth_mode, redaction: {enabled: true, token_map: "local-only"}}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_stats.py`:

```python
from driftguard import models
from tests.support import ApiTestCase


class StatsTests(ApiTestCase):
    def test_stats_counts_and_mode(self):
        target = self.create_target()
        db = self.factory()
        scan = models.Scan(target_id=target["id"], status="completed")
        db.add(scan)
        db.flush()
        db.add(models.Evidence(scan_id=scan.id, fingerprint="t/TLS/x", category="TLS",
                               title="x", severity="Low", resource="r", details={}))
        db.add(models.DriftEvent(target_id=target["id"], scan_id=scan.id,
                                 evidence_fingerprint="t/TLS/x", classification="NEW"))
        db.commit()
        db.close()
        body = self.client.get("/api/stats").json()
        self.assertEqual(body["targets"], 1)
        self.assertEqual(body["scans"], 1)
        self.assertEqual(body["evidence"], 1)
        self.assertEqual(body["drift_events"], 1)
        self.assertEqual(body["auth_mode"], "local_research")
        self.assertTrue(body["redaction"]["enabled"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_stats.py' -v`
Expected: FAIL with 404 for `/api/stats`.

- [ ] **Step 3: Implement the schema and route**

Add `StatsRead` to `schemas.py` with the fields above (`redaction: dict`). Implement in `main.py`:

```python
@app.get("/api/stats", response_model=StatsRead)
def stats(db: Session = Depends(get_db),
          principal: Principal = Depends(require_role("viewer"))):
    counts = {}
    for name, model in (("targets", models.Target), ("scans", models.Scan),
                        ("evidence", models.Evidence), ("drift_events", models.DriftEvent)):
        counts[name] = db.scalar(select(func.count()).select_from(model)) or 0
    return StatsRead(
        **counts,
        auth_mode="jwt" if auth_enabled() else "local_research",
        redaction={"enabled": True, "token_map": "local-only"},
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_stats.py' -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/driftguard/schemas.py backend/driftguard/main.py backend/tests/test_stats.py
git commit -m "feat(api): add research stats endpoint"
```

---

### Task 5: Read-only evaluation endpoint

**Files:**
- Create: `backend/driftguard/evaluation_service.py`
- Modify: `backend/driftguard/schemas.py`
- Modify: `backend/driftguard/main.py`
- Modify: `backend/evaluate.py:244-258`
- Test: `backend/tests/test_evaluation_api.py`

**Interfaces:**
- Consumes: `driftguard.sync.load_lab_truth`, `evaluate.load_engine_evidence`, `evaluate.planted_from_registry`, `evaluate.evaluate`.
- Produces:
  - `build_evaluation_report(db: Session, repo_root: Path) -> dict` returning either
    `{"available": false, "reason": str}` or
    `{"available": true, "generated_at": iso, "overall": dict, "per_area": dict, "per_target": dict, "unmeasured": dict, "scan_labels": list[str]}`
  - `EvaluationRead` response model with optional fields.
  - `GET /api/evaluation`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_evaluation_api.py`:

```python
from datetime import datetime, timezone
from unittest import mock

from driftguard import models
from tests.support import ApiTestCase


class EvaluationApiTests(ApiTestCase):
    def test_unavailable_ground_truth_is_reported_without_numbers(self):
        with mock.patch("driftguard.evaluation_service.load_lab_truth",
                        side_effect=FileNotFoundError("lab ground truth missing")):
            body = self.client.get("/api/evaluation").json()
        self.assertFalse(body["available"])
        self.assertIn("lab ground truth missing", body["reason"])
        self.assertIsNone(body.get("overall"))

    def test_duplicate_completed_labels_block_evaluation(self):
        target = self.create_target()
        db = self.factory()
        db.add_all([
            models.Scan(target_id=target["id"], status="completed", label="S1"),
            models.Scan(target_id=target["id"], status="completed", label="S1"),
        ])
        db.commit()
        db.close()
        with mock.patch("driftguard.evaluation_service.load_lab_truth") as truth:
            truth.return_value = ([], {}, {})
            body = self.client.get("/api/evaluation").json()
        self.assertFalse(body["available"])
        self.assertIn("S1", body["duplicates"])

    def test_evaluation_is_read_only(self):
        target = self.create_target()
        db = self.factory()
        db.add(models.Scan(target_id=target["id"], status="completed", label="S1"))
        db.commit()
        before = (db.query(models.Scan).count(), db.query(models.Evidence).count(),
                  db.query(models.DriftEvent).count())
        db.close()
        with mock.patch("driftguard.evaluation_service.load_lab_truth",
                        side_effect=FileNotFoundError("missing")):
            self.client.get("/api/evaluation")
        db = self.factory()
        after = (db.query(models.Scan).count(), db.query(models.Evidence).count(),
                 db.query(models.DriftEvent).count())
        db.close()
        self.assertEqual(before, after)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_evaluation_api.py' -v`
Expected: FAIL with 404 for `/api/evaluation`.

- [ ] **Step 3: Implement the service and route**

Create `evaluation_service.py`:

```python
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .sync import load_lab_truth
from evaluate import evaluate, load_engine_evidence, planted_from_registry


def _duplicate_completed_labels(db: Session) -> list[str]:
    rows = db.execute(
        select(models.Scan.label, func.count())
        .where(models.Scan.label.is_not(None), models.Scan.status == "completed")
        .group_by(models.Scan.label)
        .having(func.count() > 1)
    ).all()
    return sorted(label for label, _ in rows)


def build_evaluation_report(db: Session, repo_root: Path) -> dict:
    try:
        scans, truth_matrix, targets = load_lab_truth(repo_root)
    except Exception as exc:  # missing or unreadable lab ground truth
        return {"available": False, "reason": str(exc)}
    scan_labels = [scan.label for scan in scans if scan.label]
    duplicates = sorted({label for label in scan_labels if scan_labels.count(label) > 1})
    duplicates += _duplicate_completed_labels(db)
    duplicates = sorted(set(duplicates))
    if duplicates:
        return {"available": False,
                "reason": "duplicate scan labels make the ground-truth join ambiguous",
                "duplicates": duplicates}
    evidence_by_label, _ = load_engine_evidence(db)
    report = evaluate(truth_matrix, evidence_by_label, scan_labels,
                      planted_from_registry(targets))
    return {"available": True, "generated_at": datetime.now(timezone.utc).isoformat(), **report}
```

In `evaluate.py`, filter `load_engine_evidence` to completed scans:

```python
if scan.status != "completed":
    continue
```

Add `EvaluationRead` to `schemas.py`:

```python
class EvaluationRead(BaseModel):
    available: bool
    reason: str | None = None
    duplicates: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None
    overall: dict | None = None
    per_area: dict | None = None
    per_target: dict | None = None
    unmeasured: dict | None = None
    scan_labels: list[str] | None = None
```

Add the route:

```python
@app.get("/api/evaluation", response_model=EvaluationRead)
def evaluation(db: Session = Depends(get_db),
               principal: Principal = Depends(require_role("viewer"))):
    return build_evaluation_report(db, Path(__file__).resolve().parents[2])
```

Import `Path` and the service in `main.py`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && .venv/bin/python -m unittest discover -s tests -p 'test_evaluation_api.py' -v`
Expected: PASS.

Run the whole suite: `cd backend && .venv/bin/python -m unittest discover -s tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/driftguard/evaluation_service.py backend/driftguard/schemas.py \
  backend/driftguard/main.py backend/evaluate.py backend/tests/test_evaluation_api.py
git commit -m "feat(api): add read-only evaluation endpoint"
```

---

## Self-Review

- Spec coverage: target read state, history, stats, evaluation, eligibility, duplicate-label guard, auth reuse, and read-only evaluation each map to a task.
- Type consistency: `TargetRead.last_scan` uses `ScanSummary`; history uses `ScanRead`/`EvidenceRead`/`DriftEventRead` and `DriftSummary`; `presenters.target_read` is the single constructor. `load_lab_truth` comes from `driftguard.sync`, not `evaluate`.
- Review Focus: each line is pinned by a test in Task 1, 2, 3, or 5.
- Proportion: the plan names signatures and assertions; bodies appear only where the status/summary rules are not inferable.
