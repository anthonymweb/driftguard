# DriftGuard — agent handoff

Read this first, then [`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md).

## What this repository is

DriftGuard is a **comparator**, not a scanner product. It observes an explicitly
authorised target with real tools, stores append-only evidence, and classifies the
change between consecutive observations with frozen rules:

`BASELINE` · `NEW` · `PERSISTENT` · `FIXED` · `RECURRING` · `NO DRIFT`

The `lab/` folder is the controlled fixture that supplies ground truth. It makes the
comparator measurable; it is not the product. The product is `backend/` + `frontend/`.

## Non-negotiable rules

- **Evidence only.** The UI, reports, and demo never invent, seed, or simulate findings.
  Every finding shown must come from a completed scan.
- **Frozen classification.** `backend/driftguard/drift.py` defines the rules. Do not
  change their semantics without an approved design document.
- **Authorisation gate.** A scan requires `authorization_status=authorized` plus
  `authorized_by`, `authorized_at`, `authorization_basis`, and approved scope/ports.
  The engine refuses anything else.
- **Scope.** Only TLS, Network, and API. Approved ports and paths only; never a range
  sweep; discovery only when explicitly enabled with a wordlist.
- **Redaction before anything leaves the machine.** The token map never leaves the
  process; the shareable surface is the redacted evidence endpoint.
- **Lab targets bind to 127.0.0.1 only.**
- **Do not change the lab fixture to flatter the system.** The lab is the reference
  measurement, not a demo prop.

## Layout

| Path | What it is |
|---|---|
| `backend/` | FastAPI service, scanning engine, drift classifier, redaction, tests |
| `frontend/` | React + Vite dashboard (currently being redesigned as a comparator console) |
| `lab/` | Five controlled targets, reversible drift scenarios, ground-truth log |
| `docs/superpowers/specs/` | Design documents (source of truth for intent) |
| `docs/superpowers/plans/` | Implementation plans |
| `docs/progress/` | Snapshots of the detailed per-phase work ledgers |
| `docs/development-log.md` | Running development log |

## Run and test

```bash
# Backend tests (127 passing as of 2026-11-24)
cd backend && .venv/bin/python -m unittest discover -s tests

# API
cd backend && .venv/bin/uvicorn driftguard.main:app --host 127.0.0.1 --port 8000

# Frontend (Vite on 127.0.0.1)
cd frontend && npm install && npm run dev
cd frontend && npm run build

# Lab (Docker required; see lab/README.md for the full operator guide)
cd lab && python3 domain.py status
cd lab && python3 domain.py on eservices-lab tls-legacy
cd lab && python3 domain.py verify
```

## Where the work stands

- **[`docs/PROJECT-STATE.md`](docs/PROJECT-STATE.md)** — current focus, completed work,
  next steps, and open decisions. Update this at the end of every work session.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — the active design and plan.
- `docs/progress/` — detailed phase ledgers (portal, scanner engine).

## Working protocol

1. Read `docs/PROJECT-STATE.md` and the active design/plan before changing code.
2. Add tests before implementation for backend changes; keep the suite green.
3. Preserve the frozen contracts pinned by existing tests.
4. At the end of a session, update `docs/PROJECT-STATE.md` with: what changed, what is
   next, and any decisions the next agent must not reopen.
5. Commit and push to `origin/main`. Assume the next agent clones from GitHub and has
   no local context.

## Secrets and local-only state

- `.driftguard_redaction_secret` is **local-only and gitignored**. It was tracked in
  earlier commits; if this repository was ever shared, rotate it by deleting the file
  and letting the backend regenerate it. Rotating changes redaction tokens for old
  evidence, so record that in the project state when you do it.
- `*.db`, `.venv/`, `node_modules/`, lab state files, rendered nginx configs, and the
  damaged-disk recovery folder `lab/democommerce.corrupt-pre-reboot/` are not versioned.
- The SQLite database (`backend/driftguard.db`) is local research data, not code.
