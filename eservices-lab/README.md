# eServices Lab: simulated case-study domain for DriftGuard

## DriftGuard backend foundation

The `backend/` folder starts the DriftGuard application alongside this controlled lab. It
provides a FastAPI service, a SQLite relational schema, target inventory endpoints, and
append-only scan/evidence/drift/remediation records. No external host is configured or
scanned. A target must be registered as `authorized`, active, and have an approved scope
before a scan request can be recorded. At this milestone scan requests are queued only;
the assessment engine is the next implementation step.

From `backend/`, create a virtual environment, install `requirements.txt`, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn driftguard.main:app --host 127.0.0.1 --port 8000
```

The API docs are at `http://127.0.0.1:8000/docs`. `POST /api/targets` registers targets;
`GET /api/targets` lists them; `POST /api/targets/{id}/scans` applies the authorization
gate. The database defaults to `backend/driftguard.db`, which is ignored by Git. Set
`DRIFTGUARD_DATABASE_URL` to change its location. The initial schema is created on startup;
versioned migrations must be added before making schema changes to a deployed database.

Run the backend checks from `backend/` with
`python -m pip install -r requirements-dev.txt` and `python -m unittest discover -s tests -v`.

## DriftGuard dashboard

In a second terminal, from `frontend/`, run `npm install` once and `npm run dev`. Open
`http://127.0.0.1:5173`. The React dashboard reads registered targets, scan requests, and
evidence from the API. The Reports page exports the evidence currently stored by the API
to CSV. Drift history and remediation views explain their current integration status; they
do not show fabricated findings. Set `VITE_API_URL` in `frontend/.env` to point the UI at a
different backend origin. Keep the API bound to loopback during local development.

A small, **fully fictional** e-government environment you own and control: a citizen portal,
a records API and a (normally hidden) admin/debug API, behind an nginx "controlled host".
NITA-U is the case study; this lab is the safe, repeatable stand-in for testing.
All data is fake (`TEST-0001`, `CMTEST...`), so it doubles as the seeded data for the redaction zero-leakage check.

## Run (needs Docker + Python 3.8+)
    python lab.py up        # certs, build, start, wait for health
    python lab.py verify    # probes the live target and confirms it matches expected state

| Asset | Address |
|---|---|
| Portal + API (HTTPS) | https://localhost:8443  (try /api/v1/services) |
| HTTP | http://localhost:8080 (redirects to HTTPS) |
| Records API | /api/v1/records/TEST-0001  (header `X-API-Key: lab-demo-key`) |
| Admin/debug API | /api/v1/admin/debug  (403 at baseline) |
| Legacy admin | localhost:8081 (closed at baseline) |

> **Supported entry point for the whole domain:** run `python3 domain.py` from the
> repository root to bring the domain up, toggle scenarios, mark scans, verify, and
> read ground truth across all targets. The `python lab.py …` commands below remain
> valid for operating this wrapped case-study lab in isolation (and the domain
> controller uses `lab.py` internally for lifecycle and toggles), but `lab.py mark`
> no longer feeds the authoritative log — use `python3 domain.py mark <label>`.

## Drift scenarios (reversible): `python lab.py on|off <name>`
`tls-legacy` (TLS 1.0/1.1 accepted) | `cert-mismatch` | `http-plain` (no HTTPS redirect) |
`port-open` (legacy admin on :8081) | `api-debug` (debug endpoint exposed)

## Ground truth
Run `python lab.py mark <label>` right after each DriftGuard scan, then `python lab.py truth`
prints the expected NEW / FIXED / PERSISTENT / RECURRING per scenario per scan. Every change is also logged to `ground_truth.csv`. The note above clarifies that, for the domain-wide authoritative ground truth, marks must be recorded via `python3 domain.py mark <label>`.

## Tested vs not
Tested (Flask backend + nginx 1.24/OpenSSL 3 on Linux): baseline and all 5 scenarios on/off confirmed by independent
probes; ground-truth engine output; backend responses through the proxy.
**Not tested (no Docker in the build environment):** `docker compose up --build` itself and the Alpine nginx image.
If `verify` shows `tls-legacy` as False after `on`, check `docker compose logs nginx` (config sets `ALL:@SECLEVEL=0`).

## Notes
The baseline uses a self-signed cert, so scanners flag it every scan. It is not a seeded scenario, so it is not in the ground truth.
Everything binds to 127.0.0.1. Never expose this lab to the internet.

**Supported entry point:** use `python3 domain.py` from the repository root to control this domain.
`domain.py` manages bring-up, scenario toggles, marks, verification, and ground truth across all targets.
`lab.py mark` no longer feeds the authoritative log; use `python3 domain.py mark <label>` instead.
