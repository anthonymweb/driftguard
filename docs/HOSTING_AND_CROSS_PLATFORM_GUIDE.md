# DriftGuard Hosting and Cross-Platform Guide

## Short answer

DriftGuard is not a hosted assessment-tool service. It is a FastAPI application that **hosts the control API and stores assessment results**. When an operator requests a scan, the API starts the DriftGuard assessment engine, and the engine runs approved external security tools against registered targets.

The pieces are:

| Piece | Role | Typical location |
|---|---|---|
| `backend/` (FastAPI + Uvicorn) | Hosts `/health`, `/ready`, authentication, target inventory, scan queueing, evidence, drift history, and export | Server or workstation |
| Assessment engine | Checks authorization and scope, runs tools, normalizes their output, creates evidence, and compares scans | Executed by the backend process |
| External assessment tools | Perform the actual network/TLS/HTTP observations: nmap, testssl.sh, httpx, and optionally gobuster | Installed on the machine running the engine |
| `frontend/` | Browser dashboard for users to view and operate the API | Vite development server or a static web host |
| `lab/` | Controlled, fictional test targets and reversible drift scenarios | Docker Compose host; primarily documented as Linux |
| SQLite database | Stores users, targets, scans, evidence, drift events, and audit data | Backend host by default |

The API is therefore the public-facing service. It is not an HTTP wrapper around separate tool binaries, and it does not itself contain nmap, testssl, or httpx as in-process scanners. It invokes those binaries and converts their output into DriftGuard evidence.

## What happens during a scan

1. An authenticated caller submits `POST /api/targets/{target_id}/scans`.
2. The API verifies that the target is active and explicitly authorized.
3. The API verifies that the caller's role is `operator` or higher and that a target authorization record exists.
4. The engine verifies that the address port and every approved port are in the target's approved scope.
5. The engine runs only the modules enabled in the target's approved scope:
   - `network` -> nmap
   - `tls` -> testssl.sh
   - `http_api` -> httpx and optional gobuster
6. The engine normalizes tool output into evidence fingerprints.
7. It compares evidence with prior completed scans and classifies drift as baseline, new, persistent, fixed, recurring, or no drift.
8. The API exposes the scan status and evidence through its endpoints.

The engine refuses unsupported or unapproved work. Tool failures are recorded in the scan rather than silently ignored, and a scan with no usable observations is marked failed.

## Assessment tools are not hosted APIs

The assessment tools are local executables used by the engine:

- **nmap** checks only the target's approved ports for unexpected open services.
- **testssl.sh** checks TLS protocols, cipher issues, and certificate names on an approved TLS port.
- **httpx** checks secure/plain HTTP behavior, redirects, and HTTP status.
- **gobuster** is optional and disabled by default. It performs discovery only when the target explicitly enables it, supplies a wordlist, and has an approved API scope.

The backend adapter resolves these tools from `PATH`, or from `DRIFTGUARD_NMAP_BIN`, `DRIFTGUARD_TESTSSL_BIN`, and `DRIFTGUARD_HTTPX_BIN` environment variables. The process running Uvicorn must therefore be able to execute these binaries.

This is also the main cross-platform caveat: Python and FastAPI can run on Linux, macOS, and Windows, but the exact external tool installation and executable name can differ. testssl.sh is a shell-based tool, so Windows hosting usually needs WSL, Git Bash, or a container-compatible arrangement. Windows native installations of nmap and httpx may require explicit binary-path settings.

## Can it run on all operating systems?

There are two meanings of “run”:

- **The application and API:** yes, the backend is Python-based and should be portable to Linux, macOS, and Windows. The frontend is a normal Vite/React static application and is also platform-independent.
- **The complete controlled lab:** the lab is officially designed around Linux with Docker and Docker Compose v2. Docker Desktop can provide a Docker host on macOS or Windows, but Windows/macOS users should treat the lab as requiring a Docker Compose-compatible Linux VM or WSL and verify live behavior locally.

The repository does not currently provide a backend Docker image or a complete Docker Compose definition for hosting the API and dashboard together. The lab Compose file hosts only the test target applications; it is not the DriftGuard production deployment.

## Local development

### Backend API

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn driftguard.main:app --host 127.0.0.1 --port 8000
```

On Windows, use the equivalent activation command and `.venv\Scripts\python` rather than `.venv/bin/python`. The default SQLite database is `backend/driftguard.db`.

Useful URLs:

- API documentation: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/health`
- Readiness: `http://127.0.0.1:8000/ready`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard defaults to Vite on `127.0.0.1:5173`. It calls the API separately; CORS must include the frontend origin.

### Controlled lab

```bash
cd lab
./bootstrap.sh
python3 domain.py status
```

The lab deliberately binds all services to `127.0.0.1`. It contains vulnerable or drift-enabled states and must not be exposed to an untrusted network.

## Hosting model

### 1. Local research deployment

Run Uvicorn locally, run the Vite dashboard locally, and run the lab on the same or a network-reachable Docker host. This is the simplest and safest model.

The local default intentionally allows unauthenticated API access. This is suitable only for an isolated research workstation.

### 2. Workstation/server deployment

Use a reverse proxy or process manager in front of Uvicorn, serve the built frontend as static files, and keep external assessment tools installed on the Uvicorn host. A typical production-style layout is:

```text
Browser
  -> reverse proxy (TLS)
     -> static frontend
     -> /api/* to Uvicorn/FastAPI

Uvicorn process
  -> SQLite or configured SQL database
  -> nmap/testssl/httpx/gobuster executables
  -> explicitly registered and authorized targets
```

The API process must have network access to targets, but should not expose target drift services or the lab ports publicly.

### 3. Container deployment

Containerizing the backend is feasible, but the container must include:

- Python dependencies from `backend/requirements.txt`
- nmap
- testssl.sh
- an httpx executable
- optional gobuster
- network route/DNS access to the targets
- a persistent database volume
- environment variables for authentication and database settings

If the lab runs separately in Docker, containers hosting the engine must reach its loopback addresses from the lab host. Publishing lab ports on `127.0.0.1` means remote containers or machines cannot reach them directly; the hosting network must be designed explicitly.

A separate container for nmap/testssl/httpx/gobuster would introduce process and RPC boundaries that do not exist in the current implementation. They would need to communicate with the assessment engine, share or exchange evidence, and enforce the same authorization and scope controls.

## Environment settings

The main settings found in this repository are:

| Variable | Purpose |
|---|---|
| `DRIFTGUARD_DATABASE_URL` | SQLAlchemy database URL; SQLite is the default |
| `DRIFTGUARD_AUTH_SECRET` | Enables bearer authentication and signing |
| `DRIFTGUARD_AUTH_REQUIRED` | Refuses startup if authentication is enabled as required but no secret is configured |
| `DRIFTGUARD_UI_ORIGINS` | CORS origins allowed to call the API |
| `DRIFTGUARD_LAB_DIR` | Optional location of a separate lab checkout |
| `DRIFTGUARD_NMAP_BIN` | Explicit nmap executable path |
| `DRIFTGUARD_TESTSSL_BIN` | Explicit testssl/testssl.sh executable path |
| `DRIFTGUARD_HTTPX_BIN` | Explicit httpx executable path |
| `DRIFTGUARD_SCAN_RATE_LIMIT` | Queueing rate limit |
| `DRIFTGUARD_LOGIN_RATE_LIMIT` | Login attempt rate limit |
| `DRIFTGUARD_REDACTION_SECRET_PATH` | Optional persistent secret for evidence redaction |

Authentication roles are:

- `viewer`: read targets, scans, evidence, and redacted evidence
- `operator`: register a scan or perform target operations allowed by the API
- `admin`: create users and register targets

For any network deployment, set `DRIFTGUARD_AUTH_REQUIRED=true` and `DRIFTGUARD_AUTH_SECRET` to a strong secret. Do not expose the API or lab to the public internet before authentication, TLS termination, firewall rules, and target authorization are configured.

## Database hosting

SQLite is appropriate for a local, single-process research installation. SQLAlchemy uses `sqlite:///./driftguard.db` by default.

For multi-instance or durable hosted deployments, set `DRIFTGUARD_DATABASE_URL` to another SQLAlchemy-supported database. This is an application-level configuration change, not a no-code deployment feature: confirm that the database driver is installed and run migrations under the selected database URL.

The current repository image/dependencies do not include a PostgreSQL driver, so PostgreSQL support would require adding the appropriate driver package and validating the migrations and concurrency behavior.

## Responsible-hosting limits

- Only assess systems the operator is authorized to test.
- Register a real hostname/IP only with approved ports and attributable authorization metadata.
- Keep the lab and dashboard bound to loopback unless a protected network is intentional.
- Use authentication and role separation outside an isolated workstation.
- Keep gobuster disabled unless discovery is explicitly in scope.
- Back up database and audit data with appropriate retention controls.
- Understand that external-tool output and network scanning can have operational and legal implications.

## Practical recommendation

For this repository, the clearest implementation is:

1. **Develop locally on Linux**: one host runs the FastAPI backend and assessment tools; Docker runs the lab.
2. **Keep the lab private**: bind it to loopback and do not publish it through the internet-facing reverse proxy.
3. **Host the dashboard as static files**: build `frontend/` and serve the output behind the reverse proxy.
4. **Expose only the FastAPI API**: protect it with bearer auth and restrict it to the needed network zone.
5. **Keep the assessment engine on the API host** until scale or isolation requirements justify a separate worker/container boundary.

This architecture gives the project portable application code while preserving one important constraint: actual scans require an OS environment with the approved external executables and network access to the targets.