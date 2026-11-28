# DriftGuard demo guide (2026-11-27)

This is the single runbook for demonstrating DriftGuard. It explains what the system is,
how it is built, every way to load targets, and exactly what is on screen in the preloaded
demo. Everything shown in the console comes from a **completed real scan** against a live
lab target; nothing is seeded, fabricated, or invented.

---

## 1. What DriftGuard is

DriftGuard is a **drift detector**. Its core operation is comparison over time: it observes
an explicitly authorised target with real tools, stores the evidence append-only, and
classifies **what changed between scans** using frozen rules:

`BASELINE` · `NEW` · `PERSISTENT` · `FIXED` · `RECURRING` · `NO DRIFT`

It is not a generic vulnerability scanner and it does not invent findings. The lab is a
controlled fixture used to measure whether the detector sees real changes; the product is
the backend service plus the Drift console.

Three things make a scan defensible:

1. **Attributable authorisation** — `authorized`, plus who authorised it, when, and on what
   basis. Anything else is refused by the engine.
2. **Scope discipline** — only approved ports and approved areas; no range sweeps, no
   discovery unless explicitly enabled for that target with a wordlist.
3. **Redaction before export** — evidence can only leave the machine through the redacted
   endpoint; the token map stays local to the process.

The three audited areas are **TLS/SSL**, **Network/Service**, and **API**. Deliberately out
of scope: HTTP header grading, CORS, cookies, HSTS, and rate-limit testing.

---

## 2. Architecture and data flow

```
lab/ — five controlled targets, reversible scenarios, ground-truth marks
  │  domain.py on|off|reset|mark <target|label> ; verify
  ▼
nmap · testssl.sh · httpx · gobuster          (real tools, approved ports only)
  │
  ▼
backend/driftguard/scanner/engine.py          (authorisation + scope gate, tool adapters)
  │  Evidence rows (fingerprint = <target>/<area>/<check-id>)
  ▼
backend/driftguard/drift.py                    (frozen classifier — no UI-side interpretation)
  │  DriftEvent rows: NEW / PERSISTENT / FIXED / RECURRING
  ▼
FastAPI main.py  →  SQLite demo-driftguard.db
  │  GET /api/targets · /api/targets/{id}/history · /api/stats · /api/evaluation
  ▼
frontend/ — React Drift console (Drift · Targets · Evaluation · Settings)
```

Read flow: the console loads target history from the API. The metric counts, the difference
line, and every stored-state card come from stored evidence and `DriftEvent` rows. The grid
marks observed presence itself; when no classification is stored for an observation, no
state is invented for it. The backend owns the frozen labels. An empty register or an empty
observation window is shown as such — never as "all clear".

Write flow: a scan is queued through `POST /api/targets/{id}/scans`, assessed in a background
session, and becomes comparable to earlier scans only when it reaches `completed`. A
`completed_with_errors` or `failed` scan emits **no** drift events and is not a comparison
base.

---

## 3. Tech stack

| Layer | What is used |
|---|---|
| API | FastAPI, Uvicorn, Pydantic / pydantic-settings, SlowAPI rate limits, python-jose + bcrypt (optional auth), python-json-logger |
| Data | SQLAlchemy 2.x, SQLite, Alembic migrations |
| Engine | Python 3.12; `nmap`, `testssl.sh`, `httpx`, `gobuster` adapters with bounded timeouts and polite delays |
| Console | React 19, Vite 8, Vitest + Testing Library + jsdom, plain CSS (no UI component library); Material Symbols and fonts via CDN with system fallbacks |
| Lab fixture | Docker Compose; five targets bound to `127.0.0.1` |
| Tests | Backend: `unittest` (145 tests as of this guide). Frontend: Vitest. Lab: 179 tests. |

Everything is local-only: API on `127.0.0.1:8000`, console on `127.0.0.1:5173`, lab targets
on loopback addresses.

---

## 4. Start the system (exact demo commands)

### 4.1 Bring up the lab

```bash
cd /home/anthonyl/driftguard/lab
./bootstrap.sh --up           # idempotent
python3 domain.py status      # no target should say DOWN
python3 domain.py verify      # must exit 0
```

If a target is `DOWN`: `python3 domain.py up <target-name>` and re-check.

### 4.2 Start the API **against the preloaded demo database**

Free port 8000 first. A stale API still listening there will make the new process fail
silently (the error goes only to the log) and leave the demo talking to the wrong database.

```bash
lsof -ti tcp:8000 | xargs -r kill
sleep 2
cd /home/anthonyl/driftguard/backend
DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
DRIFTGUARD_SCAN_RATE_LIMIT=60/minute \
nohup .venv/bin/python -m uvicorn driftguard.main:app \
  --host 127.0.0.1 --port 8000 \
  > /tmp/opencode/driftguard-demo-api.log 2>&1 &
```

Four slashes after `sqlite:` means an absolute path.

> **Warning:** without `DRIFTGUARD_DATABASE_URL`, the API opens the repo-root
> `driftguard.db` — the owner's research data (1 target, 3 scans) — and the console will
> look empty. The preloaded dataset lives **only** in `demo-driftguard.db`. Always use the
> env var for a demo.

Confirm the right database is being served:

```bash
curl -sS http://127.0.0.1:8000/api/stats
# expected: targets 5, scans 25, evidence > 0, drift_events > 0,
#           auth_mode local_research, redaction enabled
```

**Abort gate:** do not register targets or run a demo scan unless that response shows
`targets: 5` and `scans: 25`. If it shows anything else, the API is serving the wrong
database — stop and restart it with the env vars above.

### 4.3 Start the console

```bash
cd /home/anthonyl/driftguard/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open <http://127.0.0.1:5173> and hard-refresh (Ctrl+Shift+R). Hash routes:
`#/drift/1` (the labelled subject), `#/targets`, `#/evaluation`, `#/settings`.

---

## 5. Every way to load targets

### 5.1 Register one target (console or API)

In the console: **Targets → Register a target**. The form requires an explicit authorisation
record (`authorized`, `authorized_by`, `authorized_at`, `authorization_basis`) plus an
approved scope and approved ports. A pending target is inventory only — the engine refuses
to scan it and the Targets panel shows the refusal reasons.

Equivalent API call:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/targets \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "my-target",
    "address": "https://127.0.0.1:8443",
    "target_type": "web",
    "authorization_status": "authorized",
    "authorized_by": "A. Owner",
    "authorized_at": "2026-11-27T09:00:00Z",
    "authorization_basis": "written approval",
    "approved_scope": ["tls", "network"],
    "approved_ports": [8443],
    "status": "active"
  }'
```

### 5.2 Bulk-load the five lab targets

```bash
cd /home/anthonyl/driftguard/backend
DRIFTGUARD_DATABASE_URL=sqlite:////home/anthonyl/driftguard/demo-driftguard.db \
.venv/bin/python -m driftguard.sync \
  --authorized-by "A. Owner" \
  --authorization-basis "controlled lab evaluation (demo preload)"
```

This registers `eservices-lab`, `democommerce`, `civic-services-portal`, `juice-shop`, and
`vampi` with authorisation records and approved scope/ports. It does **not** run scans.

### 5.3 Change what the lab shows (drift, not registration)

`lab/domain.py` controls the *targets*, not the backend register:

```bash
cd /home/anthonyl/driftguard/lab
python3 domain.py on  eservices-lab tls-legacy      # introduce a real change
python3 domain.py off eservices-lab tls-legacy      # remove it
python3 domain.py reset eservices-lab               # all scenarios off
python3 domain.py mark DEMO-0                        # record a ground-truth observation
python3 domain.py truth                              # show the truth matrix
python3 domain.py verify                             # confirm live state matches recorded state
```

A toggle changes the fixture's behaviour; it does not create a finding. A finding appears
only after a scan observes it.

---

## 6. What to say at each panel

### Drift — `#/drift/1`

The main answer to "what changed between scans?"

- Select **eservices-lab**. Its labelled history is `DEMO-0` … `DEMO-4`. Only completed scans
  are comparable; an incomplete scan appears as a `NOT COMPARED` column and carries no drift
  rows. The grid shows one row per finding and one column per comparable observation, and the
  frozen difference line reads the stored `DriftEvent` rows.
- Say: *"The first observation is the baseline. When legacy TLS and the certificate mismatch
  appear, those rows become NEW. On the next observation they are PERSISTENT, because they
  are still there. When legacy TLS is removed it becomes FIXED. When it returns later it is
  RECURRING — not NEW again. Those are frozen backend rules; the UI only reads them."*
- Select a clean target such as **juice-shop**: `BASELINE` followed by four `NO DRIFT`
  observations. Say: *"Nothing changed, so nothing is reported. An empty state means no
  observed change — not that the scan failed."*
- The reference section order is subject → authorisation stamp → difference line → four
  stored-count cards → observation timeline → detail rail. The rail shows only states stored
  for the selected thread; on narrow screens every stored thread stays reachable as a card
  and the first is expanded.
- The authorisation stamp under the subject shows who authorised the target. The redacted
  export is available from the detail rail; it carries redaction tokens, never raw secrets.

### Targets — `#/targets`

- Five lab targets, each with an authorisation record and scope. The register reads one
  stored history per target and shows the newest **stored** drift state as a pill; a target
  with no stored state shows an honest dash. Say: *"A scan is refused unless there is an
  attributable authorisation record and an approved scope. Pending targets can be
  inventoried but cannot be assessed."*
- The page order is TARGET REGISTER head → Registered / Authorized / Refused tiles →
  All / Authorized / Pending / Refused filter tabs and search → vertical roster cards.
- This is also where a new target is registered (§5.1).

### Evaluation — `#/evaluation`

- The report is `available: true` and shows measured KPIs by area (TLS, Network, API):
  detections, misses, false positives, unmeasured scans, down observations.
- Say: *"The lab's ground-truth marks are joined to real completed scans by label. TLS is
  measured exactly; false positives are zero. The Network misses are honest: the demo's
  eservices-lab is assessed on port 8443 only, so the plain-HTTP change on 8080 and a port
  opened on an unscanned port are not observed. The system does not guess them."*
- If this panel instead says "report unavailable" with duplicate labels, see
  Troubleshooting — the lab mark history has been reused.

### Settings — `#/settings`

- Shows local research mode, redaction enabled with a local-only token map, and the
  product footprint. Say: *"Redaction happens before anything leaves the machine; the token
  map never leaves the process."*
- A **Sign in** overlay here means authentication was enabled for the API; in local
  research mode it should not appear.

---

## 7. The preloaded demo dataset

| Item | Value |
|---|---|
| Database | `/home/anthonyl/driftguard/demo-driftguard.db` (untracked) |
| Ground-truth marks | `/home/anthonyl/driftguard/lab/scans.json` (untracked) |
| Targets | 5 lab targets |
| Scans | 25 completed scans (5 per target) |
| Labelled subject | `eservices-lab` only: `DEMO-0` … `DEMO-4` |
| Other four targets | 5 completed **unlabelled** scans each — clean `BASELINE` / `NO DRIFT` |
| Scenario toggles | `eservices-lab` only; final live state has `tls-legacy`, `cert-mismatch`, `http-plain`, `port-open` on |
| Deliberately unshown | API area (`api-debug` never enabled); no present API findings |

Why only one labelled target: the evaluation joins truth to scans **by label alone**. If all
five targets shared `DEMO-0`, the report would be blocked by duplicate labels. The four clean
targets therefore carry no label and still fill their panels with real evidence.

Why `eservices-lab` is assessed on port 8443 only in the demo DB: its plain port 8080 answers
with a `301` to HTTPS and the `httpx` CLI exits non-zero on a redirect, which would mark every
labelled scan `completed_with_errors` (and therefore emit no drift events). A fresh
`driftguard.sync` restores `[8080, 8443]`; reapply `[8443]` after any re-sync:

```bash
python3 - <<'PY'
import sqlite3, json
p = '/home/anthonyl/driftguard/demo-driftguard.db'
con = sqlite3.connect(p)
row = con.execute("SELECT id FROM targets WHERE name='eservices-lab'").fetchone()
con.execute("UPDATE targets SET approved_ports=? WHERE id=?", (json.dumps([8443]), row[0]))
con.commit()
PY
```

Backups of the prior lab mark history live outside the repo in
`/tmp/opencode/driftguard-demo-backup/`:

- `scans.json.pre-demo` — the original file with duplicate `S0,S1,S2` labels.
- `scans.json.bad-preload` — the discarded first preload with misclassified drift.

### Rebuilding the dataset

Use the approved plan and its runner recipe:

- `docs/superpowers/plans/2026-11-27-demo-guide-preload.md` (Tasks 5–7)
- `/tmp/opencode/driftguard-demo-preload/preload.py` (`preflight` and `sequence` modes)

Order matters: stop the API, delete `demo-driftguard.db`, restart it with the env vars,
re-sync targets, reapply the `[8443]` port fix, archive the existing `lab/scans.json`, then
run `preload.py sequence`. Skipping the archive reuses labels and blocks evaluation.

---

## 8. Rehearsal checklist

**Ten minutes before**

- [ ] `python3 domain.py status` → no `DOWN`; `python3 domain.py verify` → exit 0.
- [ ] `curl -sS http://127.0.0.1:8000/api/stats` → 5 targets / 25 scans, *not* the research DB.
- [ ] Console hard-refreshed at `#/drift/1`.

**One minute before**

- [ ] Drift: labelled subject selected; `NEW / PERSISTENT / FIXED / RECURRING` visible.
- [ ] Evaluation says `available: true` (not duplicate labels).
- [ ] Settings shows local research mode and redaction enabled.

**During**

- [ ] Say *"what changed between scans"*; the internal design metaphor stays out of
      user-facing copy.
- [ ] Point at stored rows, not at the tools: the tools are how evidence is collected; the
      frozen classifier is what produces the labels.
- [ ] If demonstrating a live scan, use `POST /api/targets/{id}/scans` and wait for
      `completed`; never narrate a queued scan as a finding.

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Port 8000 already in use | Another service (or a stale API). `lsof -ti tcp:8000 \| xargs -r kill`, then restart with the env vars. |
| Console shows zero targets | API started without `DRIFTGUARD_DATABASE_URL`; it is serving `driftguard.db`. Restart against `demo-driftguard.db`. |
| Lab target `DOWN` | `cd lab && python3 domain.py up <target>`; re-run `verify`. |
| `testssl` error in a scan | TLS port not answering; check `domain.py status` and the target container. |
| `completed_with_errors`, no drift rows | A tool failed. Such scans are not comparable and emit no events. Fix the environment and scan again; do not patch rows. |
| Evaluation `available: false`, `duplicates: [...]` | `lab/scans.json` has reused labels. Archive it outside the repo and regenerate the sequence (§7). |
| API returns `429` | Scan rate limit hit. The demo API must be started with `DRIFTGUARD_SCAN_RATE_LIMIT=60/minute`. |
| Console looks stale | Hard-refresh (Ctrl+Shift+R); the SPA polls history but caches the target list. |
| **Sign in** overlay | Auth was enabled in the API. In local research mode (`auth_enabled()` false) the API answers as `local-research/admin` with no token; restart the API without auth if this appears. |
| `httpx_plain: command failed` on eservices-lab:8080 | The target redirects HTTP→HTTPS with `301` and the CLI exits 1. Use `[8443]` in the demo DB (§7). |

---

## 10. Source documents

- Design: `docs/superpowers/specs/2026-11-27-demo-guide-design.md`
- Plan and preload recipe: `docs/superpowers/plans/2026-11-27-demo-guide-preload.md`
- Project state and decisions: `docs/PROJECT-STATE.md`
- Frozen rules: `backend/driftguard/drift.py`
