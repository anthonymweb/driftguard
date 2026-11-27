# Demo guide + real-data preload — implementation plan (2026-11-27)

Implements the approved design in
[`docs/superpowers/specs/2026-11-27-demo-guide-design.md`](../specs/2026-11-27-demo-guide-design.md).

## Intent

Give the owner one document (`docs/DEMO_GUIDE.md`) that explains DriftGuard's architecture,
tech stack, and every way to load targets — and hand over a **running Drift console already
loaded with real lab scans**, so he can explain each panel instantly instead of running scans
mid-presentation.

## Global constraints

- **Evidence only.** No synthetic, seeded, or imported findings. Every row in the demo
  database must come from a real completed scan against a live lab target.
- **No product code changes.** No edits under `backend/driftguard/`, `frontend/src/`,
  `lab/domain/`, and no new dependencies. The frozen taxonomy
  (`BASELINE · NEW · PERSISTENT · FIXED · RECURRING · NO DRIFT`) is untouched.
- **Preserve research data.** The existing repo-root `driftguard.db` (1 target, 3 scans)
  must be byte-identical at the end of this plan. All demo data goes to
  `demo-driftguard.db`.
- **127.0.0.1 only.** API on `127.0.0.1:8000`, UI on `127.0.0.1:5173`, lab targets bound
  to `127.0.0.1`.
- The only files this plan creates or edits are:
  `docs/DEMO_GUIDE.md`, `docs/PROJECT-STATE.md`, `docs/development-log.md`, and the two
  superpowers docs (design already written, this plan).

## Review focus (read before executing)

1. **Wrong database.** The API defaults to repo-root `driftguard.db`. If any command runs
   without `DRIFTGUARD_DATABASE_URL`, demo scans land in the research database and the
   design is violated. Every backend command in this plan carries the env var.
2. **Lab or tool failure.** `testssl` (`/usr/local/bin/testssl`), `nmap`, `httpx` must all
   work, and all five lab targets must be UP. A tool error makes a scan
   `completed_with_errors`, which **emits no drift events and is not a comparison base**
   (`backend/driftguard/scanner/engine.py:332-349`) — the panels would render as empty or
   `INCOMPLETE`. Gate on this in Task 5.
3. **Duplicate labels block evaluation.** `backend/driftguard/evaluation_service.py:12-34`
   refuses to build a report when any label is used by **more than one completed scan in
   the database** (it groups by label alone, not by target), or when `lab/scans.json`
   contains duplicate labels. Two consequences:
   - `lab/scans.json` currently holds `S0,S1,S2` **twice** → `/api/evaluation` already
     returns `available:false`. It must be archived (Task 6).
   - **Only one target may carry labels.** Scanning all five targets as `DEMO-1` would
     count five completed scans under one label and block evaluation. The labelled
     sequence therefore belongs to `eservices-lab` alone; the other four targets are
     scanned **without** labels (Task 7).
4. **Rate limit.** `POST /api/targets/{id}/scans` is limited to `10/minute` by default.
   The preload needs `DRIFTGUARD_SCAN_RATE_LIMIT=60/minute`, and scans are issued
   sequentially anyway. A `429` means the env var did not reach the process.
5. **Stale UI.** The Vite dev server proxies nothing; it reads
   `http://127.0.0.1:8000` from `frontend/src/api/client.js`. Restarting the API is enough,
   but a hard refresh (Ctrl+Shift+R) is needed after data lands.

## Corrections to the approved design

Two lines of the design doc are wrong on the facts and are corrected here (the design's
*intent* is unchanged):

- **Archive path.** The design says archive `lab/eservices-lab/scans.json`. That file does
  not exist. The file that blocks evaluation is **`lab/scans.json`** (written by
  `lab/domain/state.py:14`, read by `sync.load_lab_truth`). Task 6 moves the right file.
- **"One real API scan per label per target."** That wording would produce five completed
  scans sharing each `DEMO-n` label, and `_duplicate_completed_labels`
  (`evaluation_service.py:12-19`) groups by label **without** target — so evaluation would
  report `available:false`. The correct reading is **one labelled scan per label**, which
  means one labelled target. Task 7 labels `eservices-lab` only and scans the other four
  unlabelled.

## Design deviations / decisions taken here

The approved design left two things open. These are the choices made; flag them at review if
you disagree.

- **Scenario toggles are applied to `eservices-lab` only.** The design listed the toggle
  steps without naming a target. Toggling every supporting target would be more colourful,
  but the other four targets' scans are unlabelled (constraint 3 above), so any finding on
  them would be scored as a **miss** in `/api/evaluation` — it would drag the measured
  detection rate down for no demo benefit. The four untouched targets stay clean and show
  `BASELINE` then `NO DRIFT`, which is itself a talking point ("a healthy target produces
  no drift").
- **No `api-debug` step.** The approved five-scan path covers the TLS/SSL and
  Network/Service areas. The API area will therefore show zero present findings in
  Evaluation. Adding an `api-debug` toggle would be a change to the approved design and is
  **not** done here. If the owner wants all three areas demonstrated, that is a separate
  approval.
- **`NO DRIFT` comes from the clean targets, not from a sixth scan.** The design's claim
  that the five-scan path produces `NO DRIFT` on the TLS area is not reachable: a repeat
  scan of an unchanged target yields `PERSISTENT` rows (`drift.py:14`), and `NO DRIFT`
  requires a completed scan with **zero** drift events (`main.py:274-275`), which happens
  when both scans found nothing. The four clean targets produce exactly that. No `DEMO-5`
  is needed.

---

## Tasks

### Task 1 — Preflight the environment

- [ ] Confirm the tools exist:
  ```bash
  command -v nmap httpx testssl docker python3
  /usr/local/bin/testssl --version 2>&1 | head -3
  docker info --format '{{.ServerVersion}}'
  ```
- [ ] Record the research database's contents so it can be proven unchanged later:
  ```bash
  python3 - <<'PY'
  import sqlite3
  con = sqlite3.connect('/home/anthonyl/driftguard/driftguard.db')
  for t in ('targets','scans','scan_evidence','drift_events'):
      print(t, con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
  PY
  ```
  Expected today: `targets 1`, `scans 3`, `scan_evidence 0`, `drift_events 0`. Save this
  output — Task 8 re-runs it to prove the research database was never written to.
- [ ] Confirm git is clean apart from this plan and the design doc:
  ```bash
  cd /home/anthonyl/driftguard && git status --short
  ```
  Untracked `stitch_*` folders belong to the owner and are left alone.

Done when: tools resolve, Docker answers, and the research-DB counts are recorded.

### Task 2 — Start the API against the demo database

- [ ] Stop whatever is listening on port 8000 (currently PID 1346581, running on the
  research database):
  ```bash
  lsof -ti tcp:8000 | xargs -r kill
  sleep 2
  ```
- [ ] Start the API on the **demo** database, in the background:
  ```bash
  cd /home/anthonyl/driftguard/backend
  DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
  DRIFTGUARD_SCAN_RATE_LIMIT=60/minute \
  nohup .venv/bin/python -m uvicorn driftguard.main:app \
    --host 127.0.0.1 --port 8000 \
    > /tmp/opencode/driftguard-demo-api.log 2>&1 &
  ```
  Four slashes after `sqlite:` = absolute path. The app's lifespan runs
  `Base.metadata.create_all` (`main.py:55-58`), so the schema is created on first start —
  no Alembic step is needed for a new file.
- [ ] Verify it is on the demo database:
  ```bash
  sleep 3
  curl -sS http://127.0.0.1:8000/api/stats
  ```
  Done when: the process listens on `127.0.0.1:8000`, `/api/stats` returns
  `"targets":0,"scans":0`, and `ls -la /home/anthonyl/driftguard/demo-driftguard.db`
  shows a new file.

### Task 3 — Bring the lab up

- [ ] ```bash
  cd /home/anthonyl/driftguard/lab
  ./bootstrap.sh --up
  ```
  Idempotent; safe before a demonstration.
- [ ] Check every target is reachable:
  ```bash
  python3 domain.py status
  python3 domain.py verify; echo "verify exit=$?"
  ```
  Done when: no target reports `DOWN` (today `civic-services-portal` does) and `verify`
  exits `0`. If a target is down, bring it up explicitly:
  ```bash
  python3 domain.py up civic-services-portal
  ```
  and re-check. Do not proceed with a DOWN target — its scans cannot be clean.

### Task 4 — Sync the five lab targets into the demo database

- [ ] ```bash
  cd /home/anthonyl/driftguard/backend
  DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
  .venv/bin/python -m driftguard.sync \
    --authorized-by "A. Owner" \
    --authorization-basis "controlled lab evaluation (demo preload)"
  ```
- [ ] ```bash
  curl -sS http://127.0.0.1:8000/api/targets | python3 -m json.tool | grep '"name"'
  ```
  Done when: five names are listed — `eservices-lab`, `democommerce`,
  `civic-services-portal`, `juice-shop`, `vampi` — each with
  `authorization_status: authorized`, a populated `approved_scope`, and `scannable: true`.

### Task 5 — Preflight scan of all five targets, then reset the demo database

Purpose: prove every target can produce a **clean** `completed` scan before the real
sequence runs. A `completed_with_errors` scan would silently produce no drift events and
ruin the panels.

- [ ] Write the runner (kept outside the repo; a copy of the recipe also goes in the guide):
  ```bash
  mkdir -p /tmp/opencode/driftguard-demo-preload
  ```
  Create `/tmp/opencode/driftguard-demo-preload/preload.py`:

```python
#!/usr/bin/env python3
"""Preload real lab scans into the DriftGuard demo database. Evidence only."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
LAB = Path("/home/anthonyl/driftguard/lab")
SEQUENCE = [                       # (label, [(action, scenario), ...])
    ("DEMO-0", []),
    ("DEMO-1", [("on", "tls-legacy"), ("on", "cert-mismatch")]),
    ("DEMO-2", [("on", "http-plain")]),
    ("DEMO-3", [("off", "tls-legacy"), ("on", "port-open")]),
    ("DEMO-4", [("on", "tls-legacy")]),
]
LABELLED_TARGET = "eservices-lab"
SCAN_TIMEOUT = 300                  # seconds per scan


def http(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read() or b"{}")


def targets():
    return http("GET", "/api/targets")


def lab(*args):
    proc = subprocess.run([sys.executable, "domain.py", *args],
                          cwd=LAB, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"lab {' '.join(args)} failed:\n{proc.stdout}{proc.stderr}")
    return proc.stdout


# --- scan helpers -------------------------------------------------------
def run_scan(target_id, label=None):
    path = f"/api/targets/{target_id}/scans"
    if label:
        path += "?" + urllib.parse.urlencode({"label": label})
    scan = http("POST", path)
    scan_id = scan["id"]
    deadline = time.time() + SCAN_TIMEOUT
    while time.time() < deadline:
        scans = http("GET", f"/api/targets/{target_id}/scans")
        row = next(s for s in scans if s["id"] == scan_id)
        if row["status"] in ("completed", "completed_with_errors", "failed"):
            return row
        time.sleep(2)
    raise SystemExit(f"target {target_id} scan {scan_id} timed out")


def preflight():
    for t in targets():
        row = run_scan(t["id"])
        print(f"PRE {t['name']:24} {row['status']}"
              + (f" :: {row.get('error')}" if row.get("error") else ""))
        if row["status"] != "completed":
            raise SystemExit(f"PRECONDITION FAILED: {t['name']} is not clean")


def sequence():
    by_name = {t["name"]: t for t in targets()}
    for label, toggles in SEQUENCE:
        if label == "DEMO-0":
            lab("reset")
        for action, scenario in toggles:
            lab(action, LABELLED_TARGET, scenario)
        lab("mark", label)
        print(f"--- {label} marked")
        for name, t in sorted(by_name.items()):
            row = run_scan(t["id"], label if name == LABELLED_TARGET else None)
            tag = label if name == LABELLED_TARGET else "(unlabelled)"
            print(f"    {name:24} {tag:12} {row['status']}"
                  + (f" :: {row.get('error')}" if row.get("error") else ""))
            if row["status"] != "completed":
                print("    WARNING: not a clean scan; drift events will be missing",
                      file=sys.stderr)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "preflight"
    if mode == "preflight":
        preflight()
    elif mode == "sequence":
        sequence()
    else:
        raise SystemExit(f"unknown mode {mode!r}")
```

- [ ] Run the preflight:
  ```bash
  cd /home/anthonyl/driftguard/backend
  DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
    /home/anthonyl/driftguard/backend/.venv/bin/python \
    /tmp/opencode/driftguard-demo-preload/preload.py preflight
  ```
- [ ] **Gate — do not continue unless all five print `PRE <target> completed`.** If one
  prints `completed_with_errors`, read the `::` detail and fix the *environment*, not the
  data:
  - `testssl: ...` → the target's TLS port is not answering; re-check Task 3.
  - `httpx: ...` / `httpx_plain: ...` → the target's HTTP port is down or the approved
    plain port is not listening; re-check `python3 domain.py status`.
  - `nmap: ...` → tool missing or refused; re-check Task 1.
- [ ] Reset the demo database so the official sequence starts from a true baseline
  (preflight runs are discarded trial data, not evidence we present):
  ```bash
  lsof -ti tcp:8000 | xargs -r kill; sleep 2
  rm -f /home/anthonyl/driftguard/demo-driftguard.db
  cd /home/anthonyl/driftguard/backend
  DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
  DRIFTGUARD_SCAN_RATE_LIMIT=60/minute \
  nohup .venv/bin/python -m uvicorn driftguard.main:app \
    --host 127.0.0.1 --port 8000 \
    > /tmp/opencode/driftguard-demo-api.log 2>&1 &
  sleep 3
  ```
- [ ] Re-run Task 4 (sync) so the five targets exist again, and confirm
  `curl -sS http://127.0.0.1:8000/api/stats` shows `targets 5, scans 0`.

Done when: every target has proven it can complete a clean scan, and the demo database is
empty and re-populated with five targets.

### Task 6 — Archive the stale lab scan marks

`lab/scans.json` holds `S0,S1,S2` twice (2026-11-13), which alone makes
`/api/evaluation` return `available:false`.

- [ ] Move it **outside the repository** so `git status` stays clean (the file is
  gitignored anyway, but a `.bak` next to it would not be):
  ```bash
  mkdir -p /tmp/opencode/driftguard-demo-backup
  mv /home/anthonyl/driftguard/lab/scans.json \
     /tmp/opencode/driftguard-demo-backup/scans.json.pre-demo
  ```
- [ ] Do **not** touch `lab/ground_truth.csv`. It is legacy, untracked, and is not read by
  the evaluation path (`evaluation_service.py` builds truth from `lab/scans.json` via
  `sync.load_lab_truth`); the API evaluation never opens it.

Done when: `lab/scans.json` is absent and the backup exists. Note in the session log that
the original can be restored by moving the file back.

### Task 7 — Run the labelled preload sequence

- [ ] ```bash
  cd /home/anthonyl/driftguard/backend
  DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
    .venv/bin/python /tmp/opencode/driftguard-demo-preload/preload.py sequence
  ```
  For each of the five steps this: applies the scenario toggles to `eservices-lab`,
  records the lab mark (`domain.py mark DEMO-n`), then scans all five targets —
  `eservices-lab` with `label=DEMO-n`, the other four **without** a label — waiting for
  each scan to reach a terminal status before starting the next.
- [ ] Watch for `WARNING: not a clean scan`. If `eservices-lab` ever fails to complete
  cleanly, stop and diagnose (Task 5 gate conditions); a non-clean labelled scan has no
  drift events and no comparison value.
- [ ] Expect roughly 10–20 minutes (25 scans, sequential, plus lab container recreation on
  the `port-open` step).

Done when: the runner prints five steps, and `eservices-lab` has five `completed` scans
labelled `DEMO-0`…`DEMO-4` while the other four targets have five `completed` unlabelled
scans each.

### Task 8 — Verify evidence, drift, and evaluation through the API

- [ ] Counts:
  ```bash
  curl -sS http://127.0.0.1:8000/api/stats
  ```
  Done when: `targets 5`, `scans 25`, `evidence > 0`, `drift_events > 0`.
- [ ] Drift history for `eservices-lab` (id 1 after a fresh sync — confirm via
  `/api/targets`):
  ```bash
  curl -sS "http://127.0.0.1:8000/api/targets/1/history?limit=10" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); \
      [print(s["scan"]["label"], s["summary"]["state"], s["summary"]["counts"]) for s in reversed(d["scans"])]'
  ```
  Done when, oldest → newest: `DEMO-0 BASELINE`, `DEMO-1 CHANGED` with `NEW`,
  `DEMO-2 CHANGED` with `NEW`+`PERSISTENT`, `DEMO-3 CHANGED` with `NEW`+`PERSISTENT`+
  `FIXED`, `DEMO-4 CHANGED` with `PERSISTENT`+`RECURRING`.
- [ ] A clean target (e.g. `juice-shop`) must read `BASELINE` then `NO DRIFT` four times.
- [ ] Evaluation:
  ```bash
  curl -sS http://127.0.0.1:8000/api/evaluation | python3 -m json.tool | head -60
  ```
  Done when: `"available": true` (no `duplicates`), `overall.present_total > 0`,
  `overall.detections == overall.present_total`, `overall.false_positives == 0`, and
  `unmeasured` is empty or only lists labels we deliberately skipped.
- [ ] Research database untouched:
  ```bash
  python3 - <<'PY'
  import sqlite3
  con = sqlite3.connect('/home/anthonyl/driftguard/driftguard.db')
  for t in ('targets','scans','scan_evidence','drift_events'):
      print(t, con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
  PY
  ```
  Must still print `targets 1 / scans 3 / scan_evidence 0 / drift_events 0`.

If any check fails, fix the cause and re-run **Task 7 from a fresh demo database**
(Task 5's reset) rather than patching rows by hand.

### Task 9 — Verify the console UI

- [ ] Open `http://127.0.0.1:5173` (Vite should already be running on `127.0.0.1:5173`;
  if not: `cd frontend && npm run dev`). Hard-refresh with Ctrl+Shift+R.
- [ ] Check all four panels render real data with no fatal error boundary:
  - **Drift** — `eservices-lab` shows the labelled arc; the other targets show
    `BASELINE`/`NO DRIFT`; the counts match Task 8.
  - **Targets** — five targets, each with completed scans and an authorisation record.
  - **Evaluation** — measured KPIs, not the "unavailable" state.
  - **Settings** — loads; no fabricated values.
- [ ] Optional screenshots (kept in `/tmp`, never committed). The console is a hash-routed
  SPA (`frontend/src/state/useHashRoute.js`): `#/drift/<id>`, `#/targets`,
  `#/evaluation`, `#/settings`.
  ```bash
  mkdir -p /tmp/opencode/driftguard-ui-shots
  shot () {  # $1 = hash route, $2 = filename
    google-chrome --headless=new --disable-gpu --hide-scrollbars \
      --window-size=1680,1050 --virtual-time-budget=25000 \
      --screenshot="/tmp/opencode/driftguard-ui-shots/$2.png" \
      "http://127.0.0.1:5173/$1" >/dev/null 2>&1
  }
  shot '#/drift/1'   demo-drift
  shot '#/targets'   demo-targets
  shot '#/evaluation' demo-evaluation
  shot '#/settings'  demo-settings
  ```
  Screenshots are for the owner's rehearsal notes only.

Done when: every panel shows real completed-scan data and the owner can read the story off
the Drift panel without running anything.

### Task 10 — Write `docs/DEMO_GUIDE.md`

Single document, in this order:

1. **What DriftGuard is** — a drift detector: it compares consecutive authorised
   observations and classifies what changed. Never "scanner product"; never "comparator"
   in user-facing copy.
2. **Architecture** — text diagram and data flow:
   `lab/ (five targets, reversible drift, ground-truth marks)`
   → `nmap · testssl.sh · httpx · gobuster`
   → `engine (backend/driftguard/scanner/engine.py)`
   → `evidence + frozen classifier (drift.py) → DriftEvent rows`
   → `FastAPI (main.py) → SQLite (demo-driftguard.db)`
   → `React Drift console (frontend/)`.
   State the three audited areas (TLS/SSL, Network/Service, API) and what is deliberately
   out of scope (HTTP headers, CORS, cookies, HSTS, rate limiting).
3. **Tech stack table** — FastAPI, SQLAlchemy, SQLite + Alembic, Pydantic,
   SlowAPI (rate limits), Python 3.12; React 19, Vite 8, Vitest, plain CSS;
   nmap / testssl.sh / httpx / gobuster; Docker Compose for the lab.
4. **How to start it (the exact demo commands)** — the API command *with*
   `DRIFTGUARD_DATABASE_URL` and `DRIFTGUARD_SCAN_RATE_LIMIT`, the Vite command, and a
   prominent warning that running the API without the env var serves the research database
   instead of the preloaded demo data.
5. **Every way to load targets** —
   (a) register one through the console or `POST /api/targets` (authorisation gate:
   `authorization_status=authorized` plus `authorized_by`, `authorized_at`,
   `authorization_basis`, approved scope and ports; pending targets are inventory only);
   (b) bulk-load the five lab targets with `python -m driftguard.sync`; (c) control lab
   drift with `lab/domain.py on|off <target> <scenario>` — note that this changes the
   *target*, it does not register anything with the backend.
6. **Panel-by-panel talking points** — Drift, Targets, Evaluation, Settings: what each
   shows, which real rows to point at, and the sentence to say.
7. **The preloaded demo dataset** — what was loaded (five targets, 25 scans,
   `DEMO-0`…`DEMO-4` on `eservices-lab`, four clean targets), where it lives
   (`demo-driftguard.db` and `lab/scans.json`, both **untracked** — back them up if the
   machine is rebuilt), and how to rebuild it with the preload recipe.
8. **Rehearsal checklist** — 10 minutes before, 1 minute before, and during.
9. **Troubleshooting** — port in use; API serving the wrong database; lab target `DOWN`;
   `testssl` failing; `completed_with_errors` (no drift events); evaluation
   `available:false` with `duplicates` (re-run Task 6); stale UI (hard refresh); `429`
   from the scan rate limit; a **Sign in** overlay meaning auth was enabled
   (`auth_enabled()` in `backend/driftguard/auth.py` — in local research mode the API
   answers as `local-research/admin` with no token, so the overlay should never appear).

Done when: the guide alone lets the owner start the system, load targets three ways, and
rehearse the demo without asking anyone.

### Task 11 — Update project state and development log

- [ ] `docs/PROJECT-STATE.md`: add a session entry — demo guide written, demo database
  created and preloaded with real scans, `lab/scans.json` archived to
  `/tmp/opencode/driftguard-demo-backup/scans.json.pre-demo`, API now expected to be
  started with `DRIFTGUARD_DATABASE_URL` for demos, and the decisions above that the next
  agent must not reopen (labels belong to `eservices-lab` only; toggles are
  `eservices-lab` only; `ground_truth.csv` untouched).
- [ ] `docs/development-log.md`: append today's entry — what changed, why, what was
  learned (the duplicate-label constraint in `evaluation_service.py`; `completed_with_errors`
  producing no drift events), and what remains (per-surface UI approval still outstanding).

### Task 12 — Commit and push

- [ ] ```bash
  cd /home/anthonyl/driftguard
  git add docs/DEMO_GUIDE.md docs/PROJECT-STATE.md docs/development-log.md \
          docs/superpowers/specs/2026-11-27-demo-guide-design.md \
          docs/superpowers/plans/2026-11-27-demo-guide-preload.md
  git status --short     # must show no *.db, no lab state files, no stitch_* folders
  git commit -m "docs: add demo guide; preload real lab scans into the demo database"
  git push origin main
  ```
- [ ] Confirm nothing local-only leaked:
  ```bash
  git show --stat HEAD | grep -E '\.db|scans\.json|ground_truth' || echo "clean"
  ```

Done when: the push is on `origin/main` and `git status` shows only the owner's own
untracked `stitch_*` folders.

---

## Verification summary (evidence before claims)

| Claim | Command that proves it |
|---|---|
| Demo data, not research data | `curl -s localhost:8000/api/stats` → 5 targets / 25 scans; research DB counts unchanged |
| Real completed scans | `/api/targets/{id}/history` → `completed` statuses with evidence and drift rows |
| All six states present | history summary states across the five targets |
| Evaluation measured, not mocked | `/api/evaluation` → `available:true`, `detections == present_total`, `false_positives == 0` |
| Console loads it | four panels render real rows (Task 9) |
| Nothing faked | no product code changed; every row traces to a POSTed scan |
