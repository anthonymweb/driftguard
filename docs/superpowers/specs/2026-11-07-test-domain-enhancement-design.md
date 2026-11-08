# DriftGuard Test Domain Enhancement — Design

**Project:** DriftGuard — A Baseline-Aware Security Assessment System for Web Applications and APIs
**Researcher:** Mwebaza Tony (BSIT), case study: NITA-U, semester Sept–Dec 2026
**Status:** ready for approval — builder review complete, all review points recorded in §9
**Scope of this document:** the *test domain only* — the five target applications DriftGuard will assess, and the controller that gives them known ground truth. It does not cover the DriftGuard backend, the simulation, or the UI designs, which are separate deliverables.

---

## 1. Intent

DriftGuard's evaluation depends on knowing, in advance, what the correct answer is for every finding: NEW, PERSISTENT, FIXED, RECURRING or NO DRIFT. That ground truth can only exist if the test targets are **controlled** — their weaknesses must be switchable on and off, on demand, with every change logged.

Today only one of the three custom applications (`eservices-lab`) has that shape. The other two do not, and two established benchmark applications are not deployed at all. This work brings **five targets** up to a common shape so the DriftGuard backend, the live-demo simulation and the UI all have something real and scorable to work against.

**Five targets:**

1. `eservices-lab` — simulated e-government portal + API behind nginx (already complete; not rewritten)
2. `demcommerce` — e-commerce store: FastAPI + React + nginx (exists; needs lab wiring)
3. `civic-services-portal` — civic information portal: React only today (needs an API + controlled host)
4. OWASP Juice Shop — established vulnerable web application benchmark (third-party image)
5. VAmPI — established vulnerable REST API benchmark (third-party image)

---

## 2. Goals

- **G1** Every target exposes all three audited areas at baseline: TLS/SSL configuration, network/service exposure, and API exposure.
- **G2** Every target has at least one reversible scenario in each of the three areas, switchable with a single command.
- **G3** One authoritative ground-truth log covers all five targets, so `truth` prints one combined table.
- **G4** Independent probes confirm the running lab actually matches the recorded ground truth before any DriftGuard scan is trusted.
- **G5** All five classification states (NEW, PERSISTENT, FIXED, RECURRING, NO DRIFT) are producible on every target with a known scan sequence.
- **G6** Nothing already tested and working is broken — `eservices-lab/lab.py` and its five scenarios keep running exactly as they do now.
- **G7** Everything binds to `127.0.0.1` on distinct ports, so the five assets are separately registrable in DriftGuard.

## 3. Non-goals and anti-goals

- **No new audit areas.** HTTP response headers, CORS, cookies, HSTS, rate limiting and every vulnerability class outside TLS, ports/services and API exposure are *not* assessed by DriftGuard. `demcommerce`'s existing `BASELINE / TEST_CHANGE / RESTORED` security-profile mechanism operates on exactly those out-of-scope properties; it is left untouched and is **not** wired into this domain.
- **No modification of third-party benchmark code.** Juice Shop and VAmPI are run from published images. Their source is never edited, because a modified benchmark is no longer a benchmark.
- **No live-system testing.** Nothing in this design contacts any host other than `127.0.0.1`. NITA-U production systems are never scanned.
- **No changes to the classification rules or the redaction rule.** The five states and the token-based redaction boundary are fixed by the project brief and are reproduced here only as they already exist.
- **No DriftGuard product work** in this phase: no scanner modules, no drift engine, no risk engine, no dashboard.
- **No scope creep into malware, social engineering, phishing, or enterprise vulnerability-management replacement.**

## 4. Constraints

| Constraint | Detail |
|---|---|
| Loopback only | All published ports bind `127.0.0.1`. Nothing is exposed to the network. |
| Docker available | Docker v29.9.3 and Compose v5.7.0 are present; internet access for image pulls works. |
| Known environment defect | `docker images` fails with a corrupt-image error caused by an unrelated pre-existing image (`netvision-frontend-1`). Pulls, builds and `docker compose up` are unaffected. **Do not delete or modify that image or any other project's containers** — it belongs to other work on this machine. |
| Controller language | Python 3, standard library only, matching the precedent set by the already-tested `eservices-lab/lab.py`. |
| No DNS | All hostnames resolve to `localhost` / `127.0.0.1`. Certificates carry `DNS:localhost, IP:127.0.0.1`. |
| Time | One semester, shared with the backend, simulation and UI deliverables. The domain must be finished, not gold-plated. |
| Data | Fictional data only, which doubles as the seeded data for the redaction zero-leakage check. |

---

## 5. Approaches considered

Two decisions shaped the design. Both were open in the conversation and are recorded here with the alternatives that were rejected.

### Decision 1 — How the controller is organised

| Option | Description | Trade-off |
|---|---|---|
| **1a. One `lab.py` clone per target** | Five independent controllers, each with its own classifier, probes and CSV. | Maximum isolation, but the five-state classifier would exist in five copies. Any rule change would have to be made five times, and `truth` would print five separate tables instead of one. |
| **1b. Single controller, one module per target** | A top-level `domain.py` CLI over a `domain/` package holding shared probes, shared classifier, shared ground truth, and one small module per target. | **Chosen.** One authoritative ground-truth table, one copy of the classification rules, still modular (one module per target = one unit of work per target). Cost: the existing `eservices-lab/lab.py` is *wrapped* rather than refactored, so its own CSV continues to exist alongside the shared one. |
| **1c. Extend `eservices-lab/lab.py` to cover all five** | One file grows to five targets. | Reuses tested code, but rewrites the file that has already been validated against real nginx and Flask (directly violating G6), and mixes the case-study lab with the benchmarks in one file. |

**Chosen: 1b.** The classifier must be byte-identical in behaviour across all five targets or the ground truth is meaningless; that alone justifies a single shared implementation. Wrapping the existing controller rather than rewriting it protects the only part of the domain that has already been tested.

### Decision 2 — How drift is introduced on the benchmark targets

| Option | Description | Trade-off |
|---|---|---|
| **2a. Patch the benchmark source** | Add toggle flags inside Juice Shop / VAmPI. | Gives the most natural in-app scenarios, but destroys benchmark integrity and makes image upgrades painful. Rejected. |
| **2b. Proxy-side and sidecar-only drift** | Every scenario is introduced at the controlled host (re-rendered nginx config) or by publishing/withdrawing an extra loopback port. Benchmark containers stay stock. | **Chosen.** Zero third-party modifications, mirrors exactly how `eservices-lab` already works, and each scenario remains a genuine, externally observable configuration change rather than a synthetic flag. |
| **2c. Use each benchmark's own secure/insecure modes** | VAmPI ships a compose file with a secure instance on 5001 and an insecure one on 5002. | Only toggles *application* configuration — it covers none of the TLS or port scenarios, and VAmPI's switch concerns OWASP API vulnerability classes that are outside DriftGuard's three audit areas. Rejected. |

**Chosen: 2b**, applied uniformly to all five targets so every scenario is introduced the same way.

---

## 6. Chosen design

### 6.1 Target inventory and port allocation

All addresses are `127.0.0.1`. Ports were checked as free on this machine before allocation.

| # | Target | Stack | HTTPS | HTTP | Extra port | Areas covered |
|---|---|---|---|---|---|---|
| 1 | `eservices-lab` | Flask + nginx (existing) | **8443** | **8080** | **8081** (`legacy-admin`, existing) | all three |
| 2 | `demcommerce` | FastAPI + React + nginx (existing) | **8444** | **8082** | — | all three |
| 3 | `civic-services-portal` | new Flask API + nginx serving `dist/` | **8445** | **8083** | **8084** (raw API) | all three |
| 4 | Juice Shop | `bkimminich/juice-shop:latest` + nginx | **8446** | **8085** | — | all three |
| 5 | VAmPI | `erev0s/vampi:latest` + nginx | **8447** | **8086** | **8087** (raw API) | all three |

Each target runs in its own Compose project and its own bridge network. Application containers are **never** published directly on a scenario port; only the controlled host (nginx) is published, except when a `port-open` scenario is active.

Certificates are shared and generated once into `certs/`: `localhost.crt` / `localhost.key` (SAN `DNS:localhost, IP:127.0.0.1`) and `mismatch.crt` / `mismatch.key` (`CN=wrong-host.example`) for the existing `cert-mismatch` scenario. Because TLS certificates do not encode ports, one `localhost` certificate correctly covers all five HTTPS endpoints.

### 6.2 Scenario definitions

Seventeen scenarios in total: the five already implemented on `eservices-lab`, plus three new ones per remaining target.

**Existing (unchanged) — `eservices-lab`**

| Scenario | Area | Change at the controlled host |
|---|---|---|
| `tls-legacy` | TLS/SSL | nginx accepts TLS 1.0/1.1 (`ALL:@SECLEVEL=0`) |
| `cert-mismatch` | TLS/SSL | `wrong-host.example` certificate served instead of `localhost` |
| `http-plain` | Network/Service | port 80 serves the app instead of 301-redirecting to HTTPS |
| `port-open` | Network/Service | `legacy-admin` container published on 8081 |
| `api-debug` | API | `/api/v1/admin/debug` proxied instead of returning 403 |

**New — `demcommerce`**

| Scenario | Area | Change at the controlled host | Probe (baseline → drift) |
|---|---|---|---|
| `tls-legacy` | TLS/SSL | `ssl_protocols` gains TLSv1/TLSv1.1 + `ALL:@SECLEVEL=0` | legacy handshake fails → succeeds |
| `http-plain` | Network/Service | port 8082 serves the storefront instead of 301 → HTTPS | 3xx → 2xx |
| `api-debug` | API | `/api/internal/security-profile` stops being masked by the exact-match `location` (currently `return 404`) and is proxied to the API | 404 → 204 carrying the `X-Active-Profile` header |

The `api-debug` scenario reuses an endpoint the application already exposes internally (`GET /api/internal/security-profile`). Nothing in `demcommerce/backend` changes; only the nginx template gains a rendered fragment.

**New — `civic-services-portal`**

| Scenario | Area | Change | Probe (baseline → drift) |
|---|---|---|---|
| `tls-legacy` | TLS/SSL | nginx accepts TLS 1.0/1.1 | legacy handshake fails → succeeds |
| `port-open` | Network/Service | the Flask API is additionally published directly on 8084, bypassing the controlled host | connect refused → connect succeeds |
| `api-debug` | API | `/api/v1/admin/debug` changes from 403 to proxied | 403 → 200 returning fake DB string, fake internal IPs and the API key |

**New — Juice Shop**

| Scenario | Area | Change at the controlled host | Probe (baseline → drift) |
|---|---|---|---|
| `tls-legacy` | TLS/SSL | nginx accepts TLS 1.0/1.1 | legacy handshake fails → succeeds |
| `http-plain` | Network/Service | port 8085 serves the app instead of 301 → HTTPS | 3xx → 2xx |
| `api-debug` | API | `location ^~ /rest/admin/ { return 403; }` is removed, so `/rest/admin/application-configuration` and `/rest/admin/application-version` become reachable | 403 → 200 returning the application configuration |

**New — VAmPI**

| Scenario | Area | Change | Probe (baseline → drift) |
|---|---|---|---|
| `tls-legacy` | TLS/SSL | nginx accepts TLS 1.0/1.1 | legacy handshake fails → succeeds |
| `port-open` | Network/Service | VAmPI's own port is additionally published on 8087, bypassing the controlled host | connect refused → connect succeeds |
| `api-debug` | API | `location = /users/v1/_debug { return 403; }` is removed, exposing VAmPI's genuine *Excessive Data Exposure* debug endpoint | 403 → 200 returning all user details |

VAmPI's `/users/v1/_debug` is a real, recognised OWASP API Security issue (API3:2023 Excessive Data Exposure), which makes its scenario the most externally credible of the set.

### 6.3 Controller structure

```
eservices-lab/
├── domain.py                  # top-level CLI: up | down | status | on | off | reset | mark | truth | verify
├── domain/
│   ├── __init__.py
│   ├── config.py              # target registry: addresses, ports, paths, scenario definitions
│   ├── state.py               # per-target state files, scans.json, ground_truth.csv (append-only)
│   ├── probes.py              # five stdlib probes: tls-legacy, cert, http-redirect, port, path
│   ├── classify.py            # the five-state classifier (single copy for all targets)
│   ├── compose.py             # docker compose helpers (up/down/exec/reload), per target
│   └── targets/
│       ├── __init__.py
│       ├── eservices.py       # WRAPS existing eservices-lab/lab.py via subprocess; does not rewrite it
│       ├── demcommerce.py
│       ├── civicportal.py
│       ├── juiceshop.py
│       └── vampi.py
├── certs/                     # shared localhost + mismatch certificates
├── ground_truth.csv           # AUTHORITATIVE: one row per (target, event), with a `target` column
├── scans.json                 # one marked scan records the state of all five targets
└── targets/
    ├── juiceshop/             # compose.yaml + nginx/site.conf.tpl  (no benchmark source)
    └── vampi/                 # compose.yaml + nginx/site.conf.tpl  (no benchmark source)
```

Plus, inside the applications we own:

- `civic-services-portal/api/server.py` — the new Flask API
- `civic-services-portal/deploy/{compose.yaml, nginx/lab.conf.tpl}` — controlled host serving `dist/` and proxying `/api/`
- `demcommerce/deploy/{lab.compose.yaml, nginx/lab.conf.tpl}` — lab-specific stack; the existing `deploy/compose.yaml` and its documented Ubuntu deployment are left untouched

Each `targets/*.py` module implements the same small interface:

```python
SCENARIOS: dict[str, Scenario]     # name -> (area, expected finding, render(state) -> config, probe(state))
def up() -> None                   # build + start the target's compose project
def down() -> None
def state() -> dict[str, bool]     # read this target's current scenario state
def apply(previous, current) -> None
def probes() -> dict[str, Probe]   # independent observation of each scenario
```

`domain.py` loops over the registry for `status`, `on/off`, `verify` and `mark`, so adding a sixth target later means adding one module and one registry entry.

### 6.4 Ground truth and classification

**`ground_truth.csv`** is authoritative and has a `target` column. Columns:
`timestamp_utc, target, event, scenario, action, category, expected_finding, finding_key, state_after`.

**`finding_key` is the matching contract between this file and the scanner.** It is derived, never hand-written:

```
finding_key = "<target>/<area>/<scenario>"
```

for example `eservices-lab/TLS/tls-legacy`, `vampi/API/api-debug`, `juice-shop/Network/http-plain`. The area labels are exactly `TLS`, `Network` and `API` — the same strings used in `category` — and the scenario segment is the scenario's own name, so the key is always reconstructible from the row's `target`, `category` and `scenario` columns. The DriftGuard scanner attaches the same key to any finding it derives from that scenario's probe surface, and the evaluation joins ground truth to findings on that key — no mapping table, no hashing, no dependency on backend internals. `expected_finding` remains free text for a human reading the log.

Scoring falls straight out of the key plus the recorded state:

| `state_after` for the scenario | Expected findings carrying that key |
|---|---|
| issue present (`BASELINE`, `NEW`, `PERSISTENT`, `RECURRING`) | at least one |
| issue absent (`NO DRIFT`, `FIXED`) | none |

That gives detection accuracy and false-positive rate directly, per target and per area, without any interpretation step. The schema is frozen here because the file is append-only and accumulates during the evaluation.

For the `eservices-lab` target the state is read from the existing `eservices-lab/state.json`, so the wrapper never duplicates state. `eservices-lab/ground_truth.csv` keeps existing as the pre-existing per-target log; it is no longer the authoritative record and is documented as such.

**`scans.json`** — one `mark <label>` call snapshots the state of **all five** targets at that instant, so every scan label lines up across the whole domain.

**`classify.py`** reproduces the existing rules exactly, per issue across consecutive scans:

| Condition | Classification |
|---|---|
| first scan, issue present | `BASELINE` |
| present now, absent last scan, present in no earlier scan | `NEW` |
| present now, absent last scan, present in an earlier scan before that | `RECURRING` |
| present in both scans | `PERSISTENT` |
| absent now, present last scan | `FIXED` |
| absent in both scans | `NO DRIFT` (printed where `lab.py` currently prints `-`) |

The rules are not altered; only the display name of the absent/absent case is made explicit so it matches the project brief's five states.

### 6.5 Canonical scan sequence (produces all five states in every audit area)

This sequence is what the live-demo simulation will replay, and what the evaluation table will be built from. It is designed so that **each of the three audited areas experiences every one of the five states at least once across the domain** — a shorter sequence would leave the Network/Service area permanently at `NO DRIFT`, which would make that area unscoreable.

`cert-mismatch` (TLS/SSL, `eservices-lab` only) mirrors the `tls-legacy` schedule exactly, so both TLS-area scenarios on that target exercise all five states. They are deliberately correlated rather than staggered: it keeps the table readable and loses nothing, since the two scenarios are independently observable.

| Scan | `tls-legacy` + `cert-mismatch` | `http-plain` | `port-open` | `api-debug` |
|---|---|---|---|---|
| S1 | off | off | off | off |
| S2 | **ON** | off | off | off |
| S3 | ON | **ON** | off | off |
| S4 | **off** | ON | **ON** | off |
| S5 | **ON** | ON | ON | off |
| S6 | ON | ON | ON | **ON** |
| S7 | ON | **off** | **off** | **off** |
| S8 | ON | **ON** | off | **ON** |
| S9 | ON | ON | **ON** | ON |

State produced per area (bold = the transition that creates it):

| Area / scenario | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 |
|---|---|---|---|---|---|---|---|---|---|
| TLS — `tls-legacy`, `cert-mismatch` | NO DRIFT | **NEW** | PERSISTENT | **FIXED** | **RECURRING** | PERSISTENT | PERSISTENT | PERSISTENT | PERSISTENT |
| Network — `http-plain` | NO DRIFT | NO DRIFT | **NEW** | PERSISTENT | PERSISTENT | PERSISTENT | **FIXED** | **RECURRING** | PERSISTENT |
| Network — `port-open` | NO DRIFT | NO DRIFT | NO DRIFT | **NEW** | PERSISTENT | PERSISTENT | **FIXED** | NO DRIFT | **RECURRING** |
| API — `api-debug` | NO DRIFT | NO DRIFT | NO DRIFT | NO DRIFT | NO DRIFT | **NEW** | **FIXED** | **RECURRING** | PERSISTENT |

Every scenario in every area reaches all five states within nine scans. Because `mark` snapshots all five targets at once, a single run of this sequence demonstrates the complete classification matrix on all five assets.

A shorter five-scan demonstration (S1–S5 only) is retained as the **live-demo quick path**: it yields `NO DRIFT`, `NEW`, `PERSISTENT`, `FIXED` and `RECURRING` for the TLS area and `NEW`/`PERSISTENT` for Network/Service, which is enough to show the concept on stage without the full evaluation run. The full nine scans are what the evaluation table is built from.

### 6.6 Operating contract

Settled during review; these are calls made by this design and are recorded here so the builder does not have to guess.

**Fictional data conventions (for the redaction zero-leakage check).** Every new target's seeded data reuses the identifier conventions already established by `eservices-lab/app/server.py`, so the whole domain has **one known set of fictional identifiers** for the leakage check to look for:

- record / reference IDs: `TEST-0001`, `CMTEST00000001`
- phone numbers: `+256700000001`
- internal hostnames: `*.eservices.test` style names, internal IPs inside `10.20.0.0/24`
- API keys: `lab-demo-key` style values, never a real credential

The civic portal's `/api/v1/admin/debug` response follows exactly this pattern (fake connection string, fake `10.20.0.0/24` addresses, the lab API key, one `TEST-0001` sample record). No real hostname, real IP or personal data is ever seeded anywhere in the domain.

**Target registry and approved ports.** `domain/config.py` holds the canonical registry — one entry per target with `name`, `address`, `base_url`, `approved_ports`, `drift_ports` and `scope` (`tls`, `network`, `http_api`). This file is the single source of truth that the DriftGuard backend's target inventory will consume later.

- `approved_ports` = the **baseline** published ports only (e.g. 8443 and 8080 for `eservices-lab`).
- `drift_ports` (8081, 8084, 8087) are **deliberately excluded from `approved_ports`**. That is what makes `port-open` a genuine finding: the port is closed and unapproved at baseline, and when the scenario is active it becomes an unexpected, unapproved service. Listing a drift port as approved would silently un-score it; listing it while it is closed would manufacture false positives.
- Registering these values into the running DriftGuard API (`POST /api/targets`) is **not** part of this phase; the backend is a separate deliverable that will read this registry.

**CLI surface (the simulation's interface).** The live-demo simulation drives the domain by shelling out to `domain.py`; it does not import the package. The subcommand shapes are fixed now so the two deliverables cannot diverge:

```
python domain.py up [target] | down [target] | status [--json]
python domain.py on <target> <scenario> | off <target> <scenario>
python domain.py reset [target]
python domain.py mark <label>            # snapshots ALL five targets in one scan record
python domain.py truth [--json]
python domain.py verify [--json]         # exit code 0 only if every probe matches
```

`--json` is available on `status`, `truth` and `verify` so the simulation and the evaluation script parse output instead of scraping tables. `mark` is invoked by whoever runs the scan — the operator during manual runs, the simulation during the demo.

**Subset operation.** All five targets may run at once (that is the normal and the evaluation configuration), but every command accepts an optional target so a single target can be developed in isolation. When a target is down, `status` shows it as `DOWN`, `verify` reports its probes as `UNKNOWN` rather than failing the whole run, and `mark` records `DOWN` for that target in the scan row so it is excluded from scoring instead of silently counted as `NO DRIFT`. The canonical nine-scan sequence requires all five up.

**Superseding `lab.py`.** `domain.py` becomes the supported entry point for the whole domain. `eservices-lab/lab.py` keeps working and is still used internally by the wrapper for `up`, `down`, `on`, `off` and `verify`, but its `mark` no longer feeds the authoritative log — `domain.py mark` reads live state from `eservices-lab/state.json` instead, so even a direct `lab.py on <scenario>` is captured correctly in `ground_truth.csv`. Only `lab.py mark` is superseded. `eservices-lab/README.md` gains a short note pointing at `domain.py` (the README is added to the modified-files list for that reason).

### 6.7 Artifacts to create

| Path | Purpose |
|---|---|
| `domain.py` | top-level controller CLI |
| `domain/*.py` (6 modules) | config, state, probes, classify, compose, package init |
| `domain/targets/*.py` (5 modules) | one per target |
| `targets/juiceshop/{compose.yaml,nginx/site.conf.tpl}` | Juice Shop controlled host |
| `targets/vampi/{compose.yaml,nginx/site.conf.tpl}` | VAmPI controlled host |
| `civic-services-portal/api/server.py` | new Flask API for the civic portal |
| `civic-services-portal/deploy/{compose.yaml,nginx/lab.conf.tpl}` | civic portal controlled host |
| `demcommerce/deploy/{lab.compose.yaml,nginx/lab.conf.tpl}` | demcommerce lab stack |
| `certs/` (generated) | shared localhost + mismatch certificates |
| `ground_truth.csv`, `scans.json` | authoritative domain ground truth |
| `docs/domain.md` | operator guide: bringing the domain up, running the scan sequence, reading `truth` |

**Files explicitly not modified:** `eservices-lab/lab.py`, `eservices-lab/app/server.py`, `eservices-lab/nginx/*`, `eservices-lab/docker-compose.yml`, `demcommerce/backend/**`, `demcommerce/deploy/compose.yaml`, `demcommerce/deploy/nginx/demo.conf.template`, `civic-services-portal/src/**`, and all Juice Shop / VAmPI image contents. The single exception is `eservices-lab/README.md`, which gains a short pointer to `domain.py` as the supported entry point.

### 6.8 Verification

`domain.py verify` runs every probe against every target and prints a table of `expected` vs `observed`, exiting non-zero on any mismatch — the same contract `lab.py verify` already provides. A DriftGuard scan is only meaningful once `verify` passes.

Additionally, `domain.py status` shows all five targets' scenario states in one screen, and `domain.py truth` prints the five-state classification matrix for every target × scenario × scan label.

---

## 7. Risks

| Risk | Mitigation |
|---|---|
| Ground truth cannot be matched to scanner findings later | Resolved: the `finding_key` contract in §6.4 is frozen in this document, before any row is written. |
| The corrupt pre-existing image breaks a Docker operation | Pulls and `compose up` were verified working. Never run `docker rmi` on unrelated images; if a specific command fails, work around it rather than cleaning the store. |
| Juice Shop's `/rest/admin/*` behaves differently than expected behind a proxy | Verify by running the image during implementation; if the paths do not respond as designed, substitute another observable, authenticated-free Juice Shop API surface and record the substitution in `docs/domain.md`. The scenario *name* and *area* do not change. |
| Port collisions with other work on this machine | Ports were checked as free before allocation (8080–8087, 8443–8447). All bind loopback only. |
| `demcommerce` lab stack requires env vars (`DEMO_HOSTNAME`, `DEMO_CORS_ORIGINS`) and certificates that do not exist yet | The lab compose file supplies them explicitly and `domain.py` generates `certs/` before first `up`. |
| The civic portal currently has no backend; adding one could disturb a working UI | The React source is untouched. The API is a separate service; nginx serves the existing `dist/` build. |
| Scenario state drifting out of sync with the containers | `verify` after every `on`/`off`, exactly as the existing lab does. |

---

## 8. What is left to the builder

- Concrete nginx template contents for each new target (rendered fragments for `tls-legacy`, `http-plain`, `api-debug`), following the `{{PLACEHOLDER}}` substitution pattern already used by `eservices-lab/nginx/site.conf.tpl`.
- The exact Flask endpoint set for `civic-services-portal/api/server.py` (the response *content* is constrained by §6.6's fictional-data conventions; the remaining shapes are free).
- A Dockerfile, if one is needed, for serving `civic-services-portal/dist/` through nginx.
- Image pull, build and first-boot verification on this machine.
- Test coverage for `classify.py`, `probes.py` and `state.py`.
- The operator guide `docs/domain.md`, including the nine-scan sequence as a runnable script.

## 9. Review record — decisions taken

A reviewer read this design before it was handed over. Seven points were raised; six were settled as calls made by this design, one was put to the researcher. All seven are recorded here so nothing is hidden in a conversation.

| # | Point raised | Outcome |
|---|---|---|
| 1 | Nothing stated how a ground-truth row would be matched to a scanner finding, so the evaluation could not be scored later. | **Put to the researcher.** Decided: a stable `finding_key` column (`<target>/<area>/<scenario>`) added to the schema in §6.4, with the scanner attaching the same key. Frozen before the first scan. |
| 2 | No stated convention for the fictional data seeded into the new endpoints, risking a re-seed when the redaction zero-leakage check is written. | **Settled here (§6.6).** All new targets reuse the identifier conventions already established by `eservices-lab/app/server.py`, giving the leakage check one known set of identifiers to look for. |
| 3 | The DriftGuard target inventory is empty; per-target registration values were unspecified. | **Settled here (§6.6).** `domain/config.py` becomes the canonical registry. `approved_ports` holds baseline ports only, with drift ports deliberately excluded so `port-open` is scoreable. Actually registering targets in the backend is out of this phase. |
| 4 | The original five-scan sequence only ever moved the TLS and API scenarios, leaving Network/Service permanently at `NO DRIFT` — that area would have been unscoreable. | **Settled here (§6.5).** Sequence extended to nine scans so every scenario in every area reaches all five states. A five-scan quick path is kept for the live demo. |
| 5 | The simulation's interface to the domain was unspecified, risking the two deliverables diverging. | **Settled here (§6.6).** The simulation shells out to `domain.py`; subcommand shapes and `--json` output are fixed in this document. |
| 6 | It was unclear whether all five targets must run simultaneously, and what happens when one is down. | **Settled here (§6.6).** Every command accepts an optional target; a down target is recorded as `DOWN` and excluded from scoring rather than counted as `NO DRIFT`. |
| 7 | Direct use of `lab.py mark` after `domain.py` exists would silently miss rows in the authoritative log. | **Settled here (§6.6) and §6.7.** `domain.py mark` reads live state from `state.json`, so direct `lab.py on/off` is still captured; only `lab.py mark` is superseded. `eservices-lab/README.md` is updated to say so. |

---

## 10. Post-approval note — Gobuster is not part of this phase

Raised after approval. Gobuster is a **content-discovery tool**, not a target application, so there is no place for it in the test domain: the domain is made of things DriftGuard *assesses*, and Gobuster is something a scanner *runs*.

If it is wanted later, it belongs to the DriftGuard scanner deliverable, not here, and only in the API-exposure area — it does nothing for TLS/SSL configuration or network/service exposure. Three reasons it is kept out of this phase:

1. **It cannot be scored against ground truth.** The evaluation matches scanner findings to seeded `finding_key` values. Gobuster's whole purpose is finding paths that were *not* seeded, and an unscored finding is indistinguishable from a false positive in the metrics that O5 measures.
2. **It is not deterministic.** Results vary with wordlist, thread count, timing and target response behaviour, whereas this project's position is that deterministic scanners are the source of truth.
3. **It changes the character of the assessment** from configuration audit to active brute-force discovery. That is a defensible choice, but it is a methodology statement to be made deliberately, not adopted quietly.

**If it is adopted later:** add it as an optional, off-by-default scanner module in the backend phase; score its findings only where they map to a seeded `finding_key`; report everything else as informational and exclude it from detection-accuracy and false-positive-rate calculations.
