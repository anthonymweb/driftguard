# Test Domain Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring all five DriftGuard test targets up to a common shape — three audited areas each, reversible scenarios, and one authoritative ground-truth log — so the backend, simulation and UI have something scorable to assess.

**Architecture:** A single Python-standard-library controller (`domain.py` → `domain/` package) holds shared probes, the five-state classifier, state/ground-truth storage and a per-target module registry. Each target is a Docker Compose stack behind an nginx "controlled host" whose config is re-rendered per scenario; the existing `eservices-lab/lab.py` is wrapped, never rewritten.

**Tech Stack:** Python 3.12 (stdlib only), Docker Compose v5.7, nginx 1.27-alpine, Flask, FastAPI, OpenSSL, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-07-test-domain-enhancement-design.md` — the plan argues from it; executors read both.

## Global Constraints

- All published ports bind `127.0.0.1`. Nothing is exposed to the network.
- Controller code is Python 3 standard library only (Python 3.12.3 present). No pip installs for the controller.
- Docker v29.9.3 / Compose v5.7.0. Never delete or modify unrelated images or containers; `docker images` is known to fail on a corrupt unrelated image (`netvision-frontend-1`) — pulls, builds and `compose up` work regardless.
- Classification labels are exactly `BASELINE`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, `NO DRIFT`. The rules must not change (spec §6.4).
- `finding_key` is exactly `<target>/<area>/<scenario>` with `area` ∈ {`TLS`, `Network`, `API`}. Schema frozen by spec §6.4 before any row is written.
- Fictional identifiers only: `TEST-0001`, `CMTEST00000001`, `+256700000001`, `10.20.0.0/24`, `lab-demo-key`.
- Never modify: `eservices-lab/lab.py`, `eservices-lab/app/server.py`, `eservices-lab/nginx/*`, `eservices-lab/docker-compose.yml`, `democommerce/backend/**`, `democommerce/deploy/compose.yaml`, `democommerce/deploy/nginx/demo.conf.template`, `civic-services-portal/src/**`, or Juice Shop / VAmPI image contents. Sole exception: `eservices-lab/README.md` gains a pointer to `domain.py`.
- CLI contract frozen by spec §6.6: `up [target]`, `down [target]`, `status [--json]`, `on <target> <scenario>`, `off <target> <scenario>`, `reset [target]`, `mark <label>`, `truth [--json]`, `verify [--json]`.
- Test command from repo root: `python -m unittest discover -s tests -v`.
- Commit at the end of every task.

## Review Focus

Five failure modes the spec implies but that no single task naturally exercises. Each is pinned to the task that owns the code.

1. **The legacy-TLS probe reports `absent` while the server really accepts TLS 1.0** (OpenSSL security-level mismatch between client and server). Pinned to Task 4: `test_tls_legacy_handshake_succeeds_is_present` runs a real TLS 1.0 server in-process and asserts `present`; `test_tls_legacy_tls12_only_server_is_absent` asserts `absent` against a TLS 1.2-only server.
2. **`finding_key` drifts from the frozen format**, making the evaluation unscorable. Pinned to Task 1 (`test_finding_key_uses_the_frozen_format` asserts the exact string) and Task 3 (`test_ground_truth_row_writes_finding_key` round-trips it through the CSV).
3. **A target that is down gets scored as `NO DRIFT`**, silently improving the metrics. Pinned to Task 3 (`test_truth_matrix_marks_down_target_as_none`) and Task 8 (`test_mark_records_down_target_as_none`).
4. **A rendered nginx config still contains `{{PLACEHOLDER}}`**, so nginx fails to start and the whole target is unreachable. Pinned to Task 5 (`test_rejects_leftover_placeholder`) and every target's render test in Tasks 9–12.
5. **A drift port is listed in `approved_ports`**, making `port-open` unscorable, or listed while closed, manufacturing false positives. Pinned to Task 7 (`test_registry_never_lists_drift_ports_as_approved`), which iterates every registered target and therefore covers targets added by Tasks 9–12.

---

## File Structure

```
<repo root>                             # worktree root: domain.py, domain/, tests/, targets/ and the three app
                                        # folders live here. eservices-lab/ is one target INSIDE the root
                                        # (it is the folder that contains lab.py), not the root itself.
├── domain.py                           # thin CLI shim → domain.cli.main
├── sequence.py                         # operator script: the nine-scan sequence (Task 13)
├── ground_truth.csv                    # AUTHORITATIVE, generated (gitignored)
├── scans.json                          # generated (gitignored)
├── certs/                              # generated localhost + mismatch certs (gitignored)
├── domain/
│   ├── __init__.py                     # ROOT = Path(__file__).resolve().parent.parent
│   ├── model.py                        # Scenario, Target, AREA_LABELS, ProbeResult
│   ├── classify.py                     # classify(history) -> list[str]
│   ├── state.py                        # state files, scans.json, ground_truth.csv, truth matrix
│   ├── probes.py                       # five stdlib probes
│   ├── render.py                       # {{PLACEHOLDER}} substitution
│   ├── certs.py                        # ensure_certs(cert_dir)
│   ├── compose.py                      # docker compose helpers
│   ├── config.py                       # TARGETS registry built from target modules
│   ├── cli.py                          # argparse + dispatch + --json
│   └── targets/
│       ├── __init__.py                 # MODULES registry
│       ├── eservices.py                # wraps existing lab.py (Task 7)
│       ├── democommerce.py              # Task 9
│       ├── civicportal.py              # Task 10
│       ├── juiceshop.py                # Task 11
│       └── vampi.py                    # Task 12
├── tests/                              # unittest, stdlib only
├── docs/domain.md                      # operator guide (Task 13)
├── civic-services-portal/
│   ├── api/{server.py, Dockerfile}
│   └── deploy/{compose.yaml, nginx/site.conf.tpl, nginx/conf.d/.gitkeep, expose.override.yaml}
├── democommerce/deploy/
│   ├── lab.compose.yaml
│   └── nginx/{lab.conf.tpl, conf.d/.gitkeep}
└── targets/
    ├── juiceshop/{compose.yaml, nginx/site.conf.tpl, nginx/conf.d/.gitkeep}
    └── vampi/{compose.yaml, expose.override.yaml, nginx/site.conf.tpl, nginx/conf.d/.gitkeep}
```

Shared `certs/` sits at the root; every new target mounts it as `../../certs`, which resolves to the root from all four deploy directories.

**Target module interface** — identical in Tasks 7, 9, 10, 11, 12:

```python
NAME: str
TARGET: model.Target
def up() -> None        # compose up, then apply({}, read_state()) so persisted drift is re-applied
def down() -> None
def read_state() -> dict[str, bool]                    # missing file → all False
def apply(previous: dict[str, bool], current: dict[str, bool]) -> None
def nginx_config(state: dict[str, bool]) -> str | None # rendered, placeholders resolved.
                                                       # None only where the target's own controller owns the
                                                       # template (eservices → lab.py); str for every other target.
def probes() -> dict[str, Callable[[], ProbeResult]]   # scenario name → probe
```

**Shared nginx placeholder vocabulary** — identical across all four new templates:

| Placeholder | Baseline value | Drift value |
|---|---|---|
| `{{HTTP_BLOCK}}` | `    return 301 https://$host:<https_port>$request_uri;` | `    location / { proxy_pass http://app; proxy_set_header Host $host; }` — **except DemoCommerce**, where `/` is a static bundle the API does not serve, so its drift value is `    location / { try_files $uri $uri/ /index.html; }` |
| `{{DEBUG_LOCATION}}` | `    location = <path> { return 403; }` (democommerce: `return 404;`) | proxied block for `<path>` |
| `{{SSL_PROTOCOLS}}` | `TLSv1.2 TLSv1.3` | `TLSv1 TLSv1.1 TLSv1.2 TLSv1.3` |
| `{{SSL_CIPHERS}}` | *(empty string)* | `    ssl_ciphers ALL:@SECLEVEL=0;` |

Each template also contains a literal `upstream app { server <container>:<port>; }` and its own literal static/API locations. Pass all four placeholders on every target, even where a value is constant, so the render path is uniform.

**Compose project names.** Every new `compose.yaml` sets a top-level `name:` — `democommerce-lab`, `civic-portal-lab`, `juice-shop-lab`, `vampi-lab`. Without it, Compose derives the project name from the compose file's directory, and both `democommerce/deploy/` and `civic-services-portal/deploy/` would resolve to `deploy`, so their containers, networks and `exec nginx` targets would collide.

---

## Task 1: Model types

**Files:**
- Create: `domain/__init__.py`, `domain/model.py`
- Create: `tests/__init__.py`, `tests/test_model.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `Scenario`, `Target`, `AREA_LABELS`, `ProbeResult`, `domain.ROOT` — consumed by every later task.

- [ ] **Step 1: Initialise the repository and ignore generated files**

**Already satisfied during session setup** — the repository was bootstrapped on `main` and the worktree created on branch `test-domain` before execution began. Verify rather than redo: `.gitignore` must contain `__pycache__/`, `*.pyc`, `.venv/`, `node_modules/`, `*.db`, `.env`, `certs/`, `ground_truth.csv`, `scans.json`, `state.json`, `nginx/conf.d/*.conf` (the existing file is a superset of this list — that is correct, leave the extra entries alone). Add only what is missing; do not run `git init`.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_model.py
import dataclasses
import unittest

from domain.model import AREA_LABELS, Scenario, Target


class ModelTests(unittest.TestCase):
    def test_area_labels_cover_exactly_the_three_audit_areas(self):
        self.assertEqual(AREA_LABELS, {"TLS": "TLS/SSL", "Network": "Network/Service", "API": "API"})

    def test_scenario_is_frozen(self):
        s = Scenario(name="tls-legacy", area="TLS", expected_finding="Legacy TLS 1.0/1.1 accepted")
        self.assertRaises(dataclasses.FrozenInstanceError, setattr, s, "name", "other")

    def test_finding_key_uses_the_frozen_format(self):
        t = Target(name="eservices-lab", base_url="https://127.0.0.1:8443",
                   http_base_url="http://127.0.0.1:8080", approved_ports=(8443, 8080),
                   drift_ports=(8081,), scope=("tls", "network", "http_api"),
                   scenarios=(Scenario(name="tls-legacy", area="TLS", expected_finding="x"),))
        self.assertEqual(t.finding_key("tls-legacy"), "eservices-lab/TLS/tls-legacy")

    def test_finding_key_rejects_unknown_scenario(self):
        t = Target(name="eservices-lab", base_url="https://127.0.0.1:8443",
                   http_base_url="http://127.0.0.1:8080", approved_ports=(8443, 8080),
                   drift_ports=(8081,), scope=("tls", "network", "http_api"),
                   scenarios=(Scenario(name="tls-legacy", area="TLS", expected_finding="x"),))
        self.assertRaises(KeyError, t.finding_key, "nope")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain'`

- [ ] **Step 4: Implement `domain/model.py`**

`ProbeResult = Literal["present", "absent", "unknown"]`. Two frozen dataclasses, `AREA_LABELS` as above, and `Target.finding_key(scenario_name: str) -> str` returning `f"{self.name}/{scenario.area}/{scenario_name}"`, raising `KeyError` when the scenario name is not in `self.scenarios`.

`domain/__init__.py` contains only `from pathlib import Path` and `ROOT = Path(__file__).resolve().parent.parent`.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(domain): model types and repository setup"
```

---

## Task 2: Five-state classifier

**Files:**
- Create: `domain/classify.py`
- Create: `tests/test_classify.py`

**Interfaces:**
- Produces: `classify.classify(history: Sequence[bool]) -> list[str]` — consumed by `domain/state.py` (Task 3).

- [ ] **Step 1: Write the failing test**

The nine-scan histories are taken straight from spec §6.5. One test per audit area, plus the cross-check.

```python
# tests/test_classify.py
class ClassifyTests(unittest.TestCase):
    def test_tls_area_nine_scan_sequence(self):
        history = [False, True, True, False, True, True, True, True, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NEW", "PERSISTENT", "FIXED", "RECURRING",
            "PERSISTENT", "PERSISTENT", "PERSISTENT", "PERSISTENT"])

    def test_http_plain_nine_scan_sequence(self):
        history = [False, False, True, True, True, True, False, True, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NO DRIFT", "NEW", "PERSISTENT", "PERSISTENT",
            "PERSISTENT", "FIXED", "RECURRING", "PERSISTENT"])

    def test_port_open_nine_scan_sequence(self):
        history = [False, False, False, True, True, True, False, False, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NO DRIFT", "NO DRIFT", "NEW", "PERSISTENT",
            "PERSISTENT", "FIXED", "NO DRIFT", "RECURRING"])

    def test_api_debug_nine_scan_sequence(self):
        history = [False, False, False, False, False, True, False, True, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NO DRIFT", "NO DRIFT", "NO DRIFT", "NO DRIFT",
            "NEW", "FIXED", "RECURRING", "PERSISTENT"])

    def test_first_scan_present_is_baseline(self):
        self.assertEqual(classify([True]), ["BASELINE"])

    def test_labels_are_within_the_frozen_set(self):
        labels = set(classify([False, True, True, False, True, True, False, True, True]))
        self.assertTrue(labels <= {"BASELINE", "NEW", "PERSISTENT", "FIXED", "RECURRING", "NO DRIFT"})

    def test_agrees_with_driftguard_backend_classifier(self):
        """The evaluation compares ground truth (this module) against the
        backend's evidence classifier. They must not disagree."""
        # Load eservices-lab/backend/driftguard/drift.py by path (stdlib imports only),
        # then for every index i >= 1 compare:
        #   domain label  vs  backend.classify(current, previous, earlier).get(F, "NO DRIFT")
        # where current/previous/earlier are {F} or set() built from the history.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_classify -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.classify'`

- [ ] **Step 3: Implement `classify(history: Sequence[bool]) -> list[str]` in `domain/classify.py`**

Rules, in order, exactly as spec §6.4: index 0 → `BASELINE` if present else `NO DRIFT`; present & absent-last → `RECURRING` if present in any earlier index else `NEW`; present & present-last → `PERSISTENT`; absent & present-last → `FIXED`; absent & absent-last → `NO DRIFT`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(domain): five-state drift classifier"
```

---

## Task 3: State, scans and ground-truth storage

**Files:**
- Create: `domain/state.py`
- Create: `tests/test_state.py`

**Interfaces:**
- Consumes: `domain.model.Scenario`, `domain.classify.classify`, `domain.ROOT`
- Produces (consumed by Task 8's CLI):

```python
def read_state(path: Path, scenario_names: Sequence[str]) -> dict[str, bool]
def write_state(path: Path, state: dict[str, bool]) -> None
def record_scan(label: str, states: dict[str, dict[str, bool] | None]) -> None   # None = target down
def read_scans() -> list[ScanRecord]
def append_ground_truth(row: GroundTruthRow) -> None
def truth_matrix(targets: dict[str, Target], scans: Sequence[ScanRecord]) -> dict[str, dict[str, list[str | None]]]
GROUND_TRUTH_PATH: Path      # ROOT / "ground_truth.csv"
SCANS_PATH: Path             # ROOT / "scans.json"
GROUND_TRUTH_COLUMNS = ["timestamp_utc", "target", "event", "scenario", "action",
                        "category", "expected_finding", "finding_key", "state_after"]
```

`ScanRecord` is a frozen dataclass `label: str`, `timestamp_utc: str`, `states: dict[str, dict[str, bool] | None]`.
`GroundTruthRow` is a frozen dataclass with one field per column in `GROUND_TRUTH_COLUMNS`.

- [ ] **Step 1: Write the failing test**

```python
class StateTests(unittest.TestCase):
    def test_read_state_missing_file_returns_all_false(self): ...
    def test_write_then_read_roundtrips(self): ...
    def test_ground_truth_header_is_written_once_with_finding_key_column(self): ...
    def test_ground_truth_row_writes_finding_key(self):
        # append one row, read the CSV back, assert the finding_key cell
        # equals "eservices-lab/TLS/tls-legacy"
    def test_record_scan_persists_down_target_as_none(self): ...
    def test_truth_matrix_marks_down_target_as_none(self):
        # target down at scan 2 → that label position is None, not "NO DRIFT"
    def test_truth_matrix_matches_classify_for_a_live_target(self): ...
```

Each test writes to a `tempfile.TemporaryDirectory` — patch `state.GROUND_TRUTH_PATH` / `state.SCANS_PATH` for that test rather than touching the repo files.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_state -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `domain/state.py`**

`record_scan` appends to `scans.json` (create `[]` when absent). `append_ground_truth` writes the header only when the file does not exist, exactly as `lab.py` does. `truth_matrix` walks each target's scenarios across scans, calling `classify` on the boolean history and substituting `None` for any scan where that target was down.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(domain): ground truth and scan storage"
```

---

## Task 4: Probes

**Files:**
- Create: `domain/probes.py`
- Create: `tests/test_probes.py`

**Interfaces:**
- Consumes: `model.ProbeResult`
- Produces (consumed by every target module):

```python
def probe_tls_legacy(host: str, port: int) -> ProbeResult      # present = TLS 1.0/1.1 handshake succeeds
def probe_cert_mismatch(host: str, port: int, cafiles: Sequence[Path]) -> ProbeResult
    # present = hostname verification fails against the served cert (verify_code 62 / "hostname" in the
    # message) — the same two-CA setup lab.py uses; any other verification error, or an unreachable
    # target, → unknown
def probe_http_plain(host: str, port: int) -> ProbeResult      # present = plain HTTP answers 2xx instead of redirecting
def probe_port_open(host: str, port: int) -> ProbeResult       # present = TCP connect succeeds (refused → absent)
def probe_api_path(host: str, port: int, path: str, *, tls: bool = True) -> ProbeResult
    # 2xx → present; 401/403/404 → absent; connection failure → unknown; 5xx/other → unknown

# DOWN detection (used by status, verify and mark): a target is DOWN exactly when
#   probe_port_open(host, port_of(target.base_url)) == "absent".
# A DOWN target reports every probe as unknown, is shown as DOWN by `status`, and is recorded as
# None (not "NO DRIFT") by `mark`.
```

Every probe returns `unknown` when the target cannot be reached in a way that makes the observation meaningless (except `probe_port_open`, where refusal *is* the observation). Suppress the `ssl.TLSVersion.TLSv1` deprecation warning inside `probe_tls_legacy` with `warnings.catch_warnings()`.

- [ ] **Step 1: Write the failing test**

```python
class ProbeTests(unittest.TestCase):
    def test_api_path_2xx_is_present(self): ...          # local http.server returning 200
    def test_api_path_403_is_absent(self): ...           # local handler returning 403
    def test_api_path_404_is_absent(self): ...
    def test_api_path_refused_is_unknown(self): ...      # closed port
    def test_http_plain_2xx_is_present(self): ...
    def test_http_plain_301_is_absent(self): ...
    def test_port_open_refused_is_absent(self): ...
    def test_port_open_listening_is_present(self): ...
    def test_tls_legacy_handshake_succeeds_is_present(self):
        # in-process TLS 1.0 server (PROTOCOL_TLS_SERVER, minimum_version=TLSv1,
        # set_ciphers("ALL:@SECLEVEL=0")), self-signed cert generated in setUpClass
        # skipUnless(ssl.HAS_TLSv1)
    def test_tls_legacy_tls12_only_server_is_absent(self): ...
    def test_cert_mismatch_hostname_failure_is_present(self):
        # server presents mismatch.crt while the client trusts BOTH good.crt and mismatch.crt
        # (the lab.py two-CA setup) → hostname verification fails → present
    def test_cert_mismatch_untrusted_cert_is_unknown(self):
        # client trusts only good.crt, server presents mismatch.crt → unknown CA, not a hostname
        # failure → unknown
```

Use `http.server.HTTPServer` on `("127.0.0.1", 0)` in a daemon thread for the HTTP cases, and a raw `socket.socket()` listener for the port cases. Generate test certificates with `openssl req -x509` into a temp dir in `setUpClass`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_probes -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `domain/probes.py`**

Legacy handshake: build an `ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)` with `check_hostname=False`, `verify_mode=ssl.CERT_NONE`, ciphers `ALL:@SECLEVEL=0`, and `minimum_version = maximum_version = TLSVersion.TLSv1`, then retry with `TLSVersion.TLSv1_1`; `present` if either succeeds.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS — confirm the two TLS tests actually ran rather than skipping.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(domain): deterministic probes for the three audit areas"
```

---

## Task 5: Template rendering and certificates

**Files:**
- Create: `domain/render.py`, `domain/certs.py`
- Create: `tests/test_render.py`, `tests/test_certs.py`

**Interfaces:**
- Produces (consumed by every target module):

```python
# render.py
def render(template: str, mapping: dict[str, str]) -> str
    # replaces {{KEY}} for every key; raises ValueError if any "{{" remains

# certs.py
def ensure_certs(cert_dir: Path) -> None
    # creates localhost.crt/.key (SAN DNS:localhost,IP:127.0.0.1)
    # and mismatch.crt/.key (CN=wrong-host.example) when absent; no-op when present
```

- [ ] **Step 1: Write the failing tests**

```python
class RenderTests(unittest.TestCase):
    def test_substitutes_all_placeholders(self): ...
    def test_rejects_leftover_placeholder(self):
        with self.assertRaises(ValueError): render("{{A}} {{B}}", {"A": "1"})
    def test_leaves_nginx_variables_untouched(self):
        self.assertIn("$host", render("return 301 https://$host$request_uri;", {}))

class CertTests(unittest.TestCase):
    def test_creates_both_certificates(self): ...      # tempfile, then assert the four files exist
    def test_is_idempotent(self): ...                  # call twice, mtimes unchanged
    def test_localhost_cert_has_expected_san(self): ... # openssl x509 -text, assert "DNS:localhost"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_render tests.test_certs -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `domain/render.py` and `domain/certs.py`**

`ensure_certs` calls `openssl req -x509 -newkey rsa:2048 -nodes -days 365` using `shutil.which("openssl")`, falling back to `docker run --rm -v <dir>:/certs alpine/openssl` exactly as `lab.py` does.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(domain): nginx template rendering and lab certificates"
```

---

## Task 6: Compose helpers

**Files:**
- Create: `domain/compose.py`
- Create: `tests/test_compose.py`

**Interfaces:**
- Produces (consumed by every target module):

```python
def run(project_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess
def up(project_dir: Path, override: Path | None = None) -> None
    # ["docker","compose"] + (["-f", str(project_dir/"compose.yaml")] + ["-f", str(override)] if override else []) + ["up","-d"]
def down(project_dir: Path) -> None
def reload_nginx(project_dir: Path) -> None     # exec -T nginx nginx -s reload, check=False
def recreate(project_dir: Path, override: Path | None = None) -> None   # up -d --force-recreate
```

- [ ] **Step 1: Write the failing test**

```python
from unittest import mock
class ComposeTests(unittest.TestCase):
    @mock.patch("domain.compose.subprocess.run")
    def test_up_without_override_builds_expected_command(self, run): ...
        # assert called with ["docker","compose","-f",".../compose.yaml","up","-d"]
    @mock.patch("domain.compose.subprocess.run")
    def test_up_with_override_includes_both_files(self, run): ...
    @mock.patch("domain.compose.subprocess.run")
    def test_reload_nginx_does_not_raise_when_container_absent(self, run):
        # run.return_value.returncode = 1 → assert no exception
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `domain/compose.py`**
- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest discover -s tests -v` → PASS

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(domain): docker compose helpers"
```

---

## Task 7: eServices target wrapper and registry

**Files:**
- Create: `domain/targets/__init__.py`, `domain/targets/eservices.py`, `domain/config.py`
- Create: `tests/test_targets_eservices.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: Tasks 1–6
- Produces: `config.TARGETS: dict[str, Target]`, `config.get(name: str) -> Target`, and the target module interface used by Tasks 8–12.

- [ ] **Step 1: Write the failing test**

```python
class EservicesTargetTests(unittest.TestCase):
    def test_declares_the_five_existing_scenarios(self): ...   # names match lab.py's SCEN keys
    def test_state_is_read_from_the_existing_state_json(self): ...
    def test_apply_delegates_to_lab_py(self): ...              # mock subprocess, assert lab.py args
    def test_nginx_config_is_not_reimplemented(self): ...     # module returns None; lab.py owns it

class RegistryTests(unittest.TestCase):
    def test_eservices_is_registered(self): ...
    def test_registry_never_lists_drift_ports_as_approved(self):
        for target in config.TARGETS.values():
            self.assertEqual(set(target.drift_ports) & set(target.approved_ports), set())
    def test_every_registered_target_has_all_three_areas(self):
        for target in config.TARGETS.values():
            self.assertEqual({s.area for s in target.scenarios}, {"TLS", "Network", "API"})
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement the three files**

`targets/__init__.py` holds an explicit `MODULES: dict[str, ModuleType]` with one import per target — add an entry here in every later target task. `config.py` builds `TARGETS` from `MODULES` and exposes `get()`.

`targets/eservices.py` shells out to `python eservices-lab/lab.py <subcommand>` for `up`, `down`, `on`, `off` and `verify`, and reads `eservices-lab/state.json` for `read_state`. Its `nginx_config` returns `None` because `lab.py` owns that template. It must not import or modify `lab.py`.

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat(domain): eservices wrapper and target registry"
```

---

## Task 8: CLI

**Files:**
- Create: `domain.py` (root shim), `domain/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `config.TARGETS`, `state.*`, target module interface
- Produces: the frozen CLI contract from spec §6.6 — the simulation's interface.

- [ ] **Step 1: Write the failing test**

```python
class CliTests(unittest.TestCase):
    def test_build_parser_exposes_every_contract_subcommand(self): ...
    def test_status_json_shape_has_targets_and_states(self): ...
    def test_truth_json_is_target_scenario_scan_label(self): ...
    def test_verify_returns_zero_when_all_probes_match(self): ...
    def test_verify_returns_nonzero_on_mismatch(self): ...
    def test_on_rejects_unknown_scenario(self): ...      # exit code 2
    def test_on_rejects_unknown_target(self): ...        # exit code 2
    def test_mark_records_every_registered_target(self): ...
    def test_mark_records_down_target_as_none(self): ...
    def test_verify_down_target_reports_unknown_without_failing(self): ...
    def test_up_without_target_brings_up_every_registered_target(self): ...
    def test_up_with_target_brings_up_only_that_target(self): ...
```

Patch `domain.cli.config.TARGETS` and the target module functions with `mock.patch` so no container is needed.

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `domain/cli.py` and the root `domain.py` shim**

Root `domain.py` is exactly:

```python
from domain.cli import main
if __name__ == "__main__":
    raise SystemExit(main())
```

`main(argv: list[str] | None = None) -> int` builds the parser, dispatches, and returns 0/1/2. `--json` prints a single JSON object to stdout on `status`, `truth` and `verify`; human output is the table form.

**DOWN semantics (spec §6.6), decided at pre-flight.** Determine DOWN with `probe_port_open(host, port_of(target.base_url)) == "absent"` — never by "all probes unknown", because `probe_port_open` on a down host returns `absent`, not `unknown`. Then:

- `status` prints `DOWN` for that target instead of its states.
- `verify` prints that target's probes as `UNKNOWN` and does **not** fail the run for them; exit 1 only when a target that is UP has a probe whose observation disagrees with its recorded state. A fully UP domain with every probe agreeing exits 0.
- `mark` records `None` for that target (never `"NO DRIFT"`).

`verify` compares each probe against the recorded state: state `True` expects `present`, state `False` expects `absent`, and `unknown` while the target is UP is a mismatch (exit 1) — the same rule `lab.py verify` applies.

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Smoke-test the real entry point**

Run: `python domain.py status --json`
Expected: a JSON object listing `eservices-lab` with its five scenarios; no exception. This also confirms the root-script-plus-package import resolution.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(domain): CLI with frozen subcommands and --json output"
```

---

## Task 9: DemoCommerce lab stack

**Files:**
- Create: `democommerce/deploy/lab.compose.yaml`, `democommerce/deploy/nginx/lab.conf.tpl`, `democommerce/deploy/nginx/conf.d/.gitkeep`
- Create: `domain/targets/democommerce.py`
- Create: `tests/test_targets_democommerce.py`
- Modify: `domain/targets/__init__.py` (register `democommerce`)

**Interfaces:**
- Produces: scenarios `tls-legacy` (TLS), `http-plain` (Network), `api-debug` (API); approved ports `8444`, `8082`; `TARGET` with `base_url="https://127.0.0.1:8444"` and `http_base_url="http://127.0.0.1:8082"`; no drift ports.

- [ ] **Step 1: Write the failing test**

```python
class DemocommerceRenderTests(unittest.TestCase):
    def test_baseline_blocks_legacy_tls(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", cfg)
        self.assertNotIn("TLSv1 ", cfg)
    def test_tls_legacy_enables_legacy_protocols_and_seclevel_zero(self): ...
    def test_baseline_redirects_http(self):
        self.assertIn("return 301 https://$host:8444$request_uri;", cfg)
    def test_http_plain_serves_the_store_instead(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "http-plain": True})
        port80 = cfg.split("server {")[1]          # the listen-80 server block is first in the template
        self.assertNotIn("return 301", port80)
        # `/` must be served as the static bundle: the API has no route for `/`, so proxying it
        # would answer 404, `probe_http_plain` would return unknown, and verify would fail
        self.assertIn("try_files $uri $uri/ /index.html;", port80)
        self.assertNotIn("proxy_pass", port80)
    def test_baseline_masks_the_internal_profile_endpoint(self):
        self.assertIn("location = /api/internal/security-profile { return 404; }", cfg)
    def test_api_debug_proxies_the_internal_profile_endpoint(self): ...
    def test_no_placeholder_survives_rendering(self):
        self.assertNotIn("{{", cfg)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `nginx/lab.conf.tpl` and `targets/democommerce.py`**

Template contains a literal `upstream app { server api:8000; }`, a `location /api/ { proxy_pass ... }` block, and `location / { try_files $uri $uri/ /index.html; }` serving `../frontend/dist`. The module builds the four placeholder values from state, writes the rendered config to `nginx/conf.d/default.conf`, and calls `compose.reload_nginx`.

`lab.compose.yaml` opens with `name: democommerce-lab` (see the Compose project-name note above). Services: `api` (**build `../backend`** — relative to `democommerce/deploy/`, so `../../backend` would resolve outside the app and fail), `DEMO_DATABASE_URL=sqlite:////data/democommerce.db` with a named volume mounted at `/data` (the app's `lifespan` runs `create_all` and seeds the catalogue, so no manual init), `DEMO_CORS_ORIGINS=https://127.0.0.1:8444`, `DEMO_SESSION_COOKIE_SECURE=1`, `DEMO_TEST_PROFILES_ENABLED=0`, `DEMO_TRUSTED_PROXY_IPS=172.30.50.2`, `DEMO_LOCAL_PROXY_CLIENTS=127.0.0.1`; and `nginx` (`nginx:1.27-alpine`, ports `127.0.0.1:8444:443` and `127.0.0.1:8082:80`, mounting `./nginx/conf.d`, `../../certs`, `../frontend/dist`, on a fixed `172.30.50.0/24` network with `ipv4_address: 172.30.50.2` so the trusted-proxy value above matches the proxy's address). Do **not** reuse `deploy/compose.yaml`.

The `{{HTTP_BLOCK}}` drift value for this target is `    location / { try_files $uri $uri/ /index.html; }`, not the shared `proxy_pass` default — DemoCommerce's `/` is the static bundle and the FastAPI app has no route for it.

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Bring the target up and verify it live**

**Prerequisite — build the store bundle.** `democommerce/frontend/dist/` is gitignored by the app's own `.gitignore`, so it does **not** exist in this worktree. Build it once:

```bash
cd democommerce/frontend && npm ci && npm run build && cd ../..
```

(Node v24.22.2 / npm 11.19.1 are present and the npm registry is reachable.) If `npm ci` fails for network reasons, copy `/mnt/data/eservices-lab/democommerce/frontend/dist` instead — same source at the same commit. Without a bundle nginx mounts an empty directory, `/` answers 404, and `http-plain` can never return 2xx. Record whichever route you used in `docs/domain.md` (Task 13).

```bash
python domain.py up democommerce
python domain.py verify
```
Expected: `verify` reports all three democommerce probes `PASS`. If `api-debug` does not return 204, check `docker compose -f democommerce/deploy/lab.compose.yaml logs api`.

- [ ] **Step 6: Confirm the baseline is clean**

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1:8444/api/internal/security-profile   # expect 404
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8082/                                # expect 301
```

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(domain): democommerce lab stack and target module"
```

---

## Task 10: Civic Services Portal API and stack

**Files:**
- Create: `civic-services-portal/api/server.py`, `civic-services-portal/api/Dockerfile`
- Create: `civic-services-portal/deploy/compose.yaml`, `.../nginx/site.conf.tpl`, `.../nginx/conf.d/.gitkeep`, `.../expose.override.yaml`
- Create: `domain/targets/civicportal.py`, `tests/test_targets_civicportal.py`
- Modify: `domain/targets/__init__.py`

**Interfaces:**
- Produces: scenarios `tls-legacy` (TLS), `port-open` (Network), `api-debug` (API); approved ports `8445`, `8083`; drift port `8084`.

- [ ] **Step 1: Write the failing render test**

Same shape as Task 9, plus:

```python
    def test_port_open_override_publishes_the_raw_api_port(self):
        # read expose.override.yaml as text; assert it maps 127.0.0.1:8084
    def test_baseline_blocks_the_debug_endpoint(self):
        self.assertIn("location = /api/v1/admin/debug { return 403; }", cfg)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement the Flask API**

`civic-services-portal/api/server.py` — Flask **bound to `0.0.0.0:5000` inside the container** (not loopback: nginx and the published `8084` port both reach the container via its interface, so a loopback bind would make every request fail. Host exposure is controlled solely by whether `127.0.0.1:8084` is published, so the all-interfaces bind does not widen anything). Endpoints:

| Route | Behaviour |
|---|---|
| `GET /health` | `{"status":"ok","service":"civic-portal-api"}` |
| `GET /api/v1/services` | fictional service catalogue (3–6 entries, `SVC-01` style IDs) |
| `GET /api/v1/admin/debug` | fake connection string, fake `10.20.0.0/24` addresses, `lab-demo-key`, one `TEST-0001` / `CMTEST00000001` / `+256700000001` record |

Content follows the fictional-data conventions in spec §6.6. **Do not modify `civic-services-portal/src/**`** — the React application itself is untouched. Note that `dist/` is gitignored by the app's own `.gitignore` and therefore **absent from this worktree** (the copy that exists in `/mnt/data/eservices-lab/civic-services-portal/dist` was never committed); see the prerequisite in Step 6.

`Dockerfile`: `python:3.12-slim`, `pip install flask`, `CMD ["python","server.py"]`, no port published except through nginx.

- [ ] **Step 4: Implement the compose stack and target module**

`deploy/compose.yaml` opens with `name: civic-portal-lab` (see the Compose project-name note). Services: `api` (build `../api`) and `nginx` (`nginx:1.27-alpine`, ports `127.0.0.1:8445:443`, `127.0.0.1:8083:80`, mounting `./nginx/conf.d`, `../../certs`, `../dist`). `expose.override.yaml` adds `ports: ["127.0.0.1:8084:5000"]` to `api`; `apply()` switches to it when `port-open` is on and back when off, using `compose.recreate`.

- [ ] **Step 5: Run test to verify it passes**
- [ ] **Step 6: Bring the target up and verify it live**

**Prerequisite — build the portal bundle.** `civic-services-portal/dist/` is gitignored and absent from this worktree. Build it once:

```bash
cd civic-services-portal && npm ci && npm run build && cd ..
```

(Node v24.22.2 / npm 11.19.1 are present and the npm registry is reachable.) If `npm ci` fails for network reasons, copy `/mnt/data/eservices-lab/civic-services-portal/dist` instead — same source at the same commit. `src/` must not change either way. Record which route you used in `docs/domain.md` (Task 13).

```bash
python domain.py up civic-services-portal
python domain.py verify
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1:8445/api/v1/admin/debug   # expect 403
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8084/health                 # expect connection refused
python domain.py on civic-services-portal port-open
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8084/health                 # expect 200
python domain.py off civic-services-portal port-open
```

Also confirm the existing UI still loads: `curl -sk https://127.0.0.1:8445/ | head -5` must return the portal HTML.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(domain): civic portal API, controlled host and port-open scenario"
```

---

## Task 11: OWASP Juice Shop stack

**Files:**
- Create: `targets/juiceshop/compose.yaml`, `targets/juiceshop/nginx/site.conf.tpl`, `targets/juiceshop/nginx/conf.d/.gitkeep`
- Create: `domain/targets/juiceshop.py`, `tests/test_targets_juiceshop.py`
- Modify: `domain/targets/__init__.py`

**Interfaces:**
- Produces: scenarios `tls-legacy` (TLS), `http-plain` (Network), `api-debug` (API); approved ports `8446`, `8085`; no drift ports.

- [ ] **Step 1: Write the failing render test**

```python
    def test_baseline_blocks_the_admin_api(self):
        self.assertIn("location ^~ /rest/admin/ { return 403; }", cfg)
    def test_api_debug_proxies_the_admin_api(self): ...
    def test_upstream_points_at_the_benchmark_container(self):
        self.assertIn("server juice-shop:3000;", cfg)
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement the compose stack and target module**

Image `bkimminich/juice-shop:latest`, container port 3000, **no source modification**. `nginx:1.27-alpine` publishes `127.0.0.1:8446:443` and `127.0.0.1:8085:80`; the compose file opens with `name: juice-shop-lab`. `up()` polls `GET https://127.0.0.1:8446/` until it answers with a status below 500 (Juice Shop takes tens of seconds to boot; nginx answers 502 until then), with a generous timeout (~180 s) and a clear failure message. Do **not** use `/rest/admin/...` as the readiness check: nginx returns 403 for it at baseline, which would report "ready" before the application has started.

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Pull, bring up, and verify the API surface assumption**

```bash
docker pull bkimminich/juice-shop:latest
python domain.py up juice-shop
python domain.py verify
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1:8446/rest/admin/application-configuration   # expect 403
python domain.py on juice-shop api-debug
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1:8446/rest/admin/application-configuration   # expect 200
python domain.py off juice-shop api-debug
```

If the path does not return 200 when unblocked, substitute another observable unauthenticated Juice Shop API path, keep the scenario name and area unchanged, and record the substitution in `docs/domain.md` (spec §7 risk).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(domain): juice shop controlled host and api-debug scenario"
```

---

## Task 12: VAmPI stack

**Files:**
- Create: `targets/vampi/compose.yaml`, `targets/vampi/expose.override.yaml`, `targets/vampi/nginx/site.conf.tpl`, `targets/vampi/nginx/conf.d/.gitkeep`
- Create: `domain/targets/vampi.py`, `tests/test_targets_vampi.py`
- Modify: `domain/targets/__init__.py`

**Interfaces:**
- Produces: scenarios `tls-legacy` (TLS), `port-open` (Network), `api-debug` (API); approved ports `8447`, `8086`; drift port `8087`.

- [ ] **Step 1: Write the failing render test**

```python
    def test_baseline_blocks_the_debug_endpoint(self):
        self.assertIn("location = /users/v1/_debug { return 403; }", cfg)
    def test_api_debug_proxies_the_debug_endpoint(self): ...
    def test_upstream_points_at_vampi(self):
        self.assertIn("server vampi:5000;", cfg)
    def test_expose_override_maps_8087(self): ...
```

- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement the compose stack and target module**

Image `erev0s/vampi:latest`, container port 5000, no source modification; the compose file opens with `name: vampi-lab`. `up()` calls `GET /createdb` once (through the controlled host — it is not blocked at baseline, and the raw container port is not published) so `/users/v1/_debug` has data to leak, then polls `GET /` until it answers with a status below 500. `expose.override.yaml` maps `127.0.0.1:8087:5000`; `apply()` recreates with or without it.

- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Pull, bring up, and verify live**

```bash
docker pull erev0s/vampi:latest
python domain.py up vampi
python domain.py verify
curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1:8447/users/v1/_debug      # expect 403
python domain.py on vampi api-debug
curl -sk -w '\n%{http_code}\n' https://127.0.0.1:8447/users/v1/_debug                 # expect 200 with user data
python domain.py off vampi api-debug
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat(domain): vampi controlled host with genuine excessive-data-exposure scenario"
```

---

## Task 13: Nine-scan sequence, operator guide and README note

**Files:**
- Create: `sequence.py`, `docs/domain.md`
- Modify: `eservices-lab/README.md` (append a short "Use `domain.py`" note — the one permitted edit)

**Interfaces:**
- Consumes: the frozen CLI from Task 8.

- [ ] **Step 1: Write `sequence.py`**

A stdlib script that drives the frozen CLI in subprocesses through the nine scans of spec §6.5, calling `python domain.py mark S<n>` after each step and printing `python domain.py truth` at the end. Scenario toggles per scan are copied exactly from the §6.5 table:

```
S1 all off | S2 tls-legacy+cert-mismatch on | S3 +http-plain | S4 tls off, port-open on
S5 tls on | S6 +api-debug | S7 http-plain off, port-open off, api-debug off
S8 http-plain on, api-debug on | S9 port-open on
```

Targets without a given scenario simply skip that toggle.

- [ ] **Step 2: Write `docs/domain.md`**

Cover: the five targets and their addresses, the seventeen scenarios by area, bringing the domain up and down, running `verify` before trusting any scan, the nine-scan sequence, reading `truth`, the `finding_key` contract (spec §6.4), the fictional-data conventions (§6.6), and the Juice Shop substitution note if Task 11 needed one.

- [ ] **Step 3: Run the full suite**

Run: `python -m unittest discover -s tests -v`
Expected: PASS, zero failures, zero skips other than a justified `HAS_TLSv1` skip.

- [ ] **Step 4: End-to-end verification with all five targets up**

```bash
python domain.py up
python domain.py verify
python domain.py status --json
```
Expected: `verify` exit code 0 for every probe on all five targets; `status --json` lists five targets, seventeen scenarios.

- [ ] **Step 5: Run one short classification cycle and read `truth`**

```bash
python domain.py mark S0
python domain.py on eservices-lab tls-legacy
python domain.py mark S1
python domain.py off eservices-lab tls-legacy
python domain.py mark S2
python domain.py truth
```
Expected: the `eservices-lab / TLS / tls-legacy` row reads `NO DRIFT`, `NEW`, `FIXED` across `S0`, `S1`, `S2`; every other row reads `NO DRIFT` throughout. (`S0` must be marked first — with no prior scan, a scenario present at the first mark is `BASELINE`, not `NEW`.)

- [ ] **Step 6: Append the README note**

Three lines at the end of `eservices-lab/README.md` pointing at `domain.py` as the supported entry point and noting that `lab.py mark` no longer feeds the authoritative log.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat(domain): nine-scan sequence, operator guide and entry-point note"
```
