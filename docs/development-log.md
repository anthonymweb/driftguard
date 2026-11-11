# Development log — DriftGuard controlled test domain

This is the working log of the build: the decisions taken, the rulings and their
cost-if-wrong, and the defects that only surfaced when the domain was run against
real containers. It is kept as the record of *why* the domain looks the way it does;
the git history is the record of *what* changed.

---


Plan: `/mnt/data/eservices-lab/.worktrees/test-domain/docs/superpowers/plans/2026-11-08-test-domain.md`
Spec: `/mnt/data/eservices-lab/.worktrees/test-domain/docs/superpowers/specs/2026-11-07-test-domain-enhancement-design.md`
BASE: `9651108e3c63000547a3011660b0877679d852a2` (branch `test-domain`, worktree `/mnt/data/eservices-lab/.worktrees/test-domain`)
Spec reachable: yes — the plan cites it by section throughout.

Setup completed before execution (session setup, not plan tasks): `git init` on `main` + `.gitignore` + baseline commits; worktree `test-domain` created from `9651108`; session moved into it; SDD workspace created.

---

## Pre-flight conflict scan

### Task-pair table — every pair sharing a file or an interface

| Tasks | Shared file / interface | Producer → consumer | Finding | Ruling |
|---|---|---|---|---|
| 1 ↔ 2–13 | `.gitignore`, `domain/__init__.py` (`ROOT`), `tests/__init__.py` | T1 → all | T1 Step 1 (`git init`, `.gitignore`) had already been done in session setup; the existing `.gitignore` is a superset of the plan's list | Step 1 rewritten as "verify, do not redo"; implementer adds only missing entries |
| 1 → 2,3,4,5,6,7,8,9–12 | `Scenario`, `Target`, `AREA_LABELS`, `ProbeResult`, `finding_key` | T1 → all | Signatures pinned by T1's test; no conflict found | — |
| 2 → 3 | `classify(history)` | T2 → `truth_matrix` | All four nine-scan histories and expected label lists verified against spec §6.5 character-for-character; the backend cross-check is sound (`drift.py` also treats `earlier` as indices `0..i-2`) | — |
| 3 → 8 | `state.*`, `ScanRecord`, `GroundTruthRow`, `truth_matrix` | T3 → CLI | Plan text said "consumed by Task 9's CLI" — stale task number (CLI is Task 8) | Corrected in the plan |
| 4 → 7,8,9–12 | `probes.*` | T4 → target `probes()`, `verify` | `probe_cert_mismatch(host, port, cafile)` takes **one** CA file, but `lab.py p_cert` loads **both** `good.crt` and `mismatch.crt` precisely to isolate a *hostname* failure (verify_code 62). One file cannot reproduce that, and any other verification error would be misread as `present` | Signature → `cafiles: Sequence[Path]`; `present` only when hostname verification fails; other verification errors → `unknown`. Test renamed and split accordingly |
| 4 → 8 | probes → `status` / `verify` / `mark` | T4 → CLI | The plan never says how DOWN is detected. `probe_port_open` returns `absent` (not `unknown`) on a down host, so "all probes unknown" is not a valid DOWN test, yet spec §6.6 requires `status DOWN`, `verify UNKNOWN`, `mark DOWN` | DOWN := `probe_port_open(host, port(target.base_url)) == "absent"`. Written into T4's interface block and T8's Step 3; added `test_verify_down_target_reports_unknown_without_failing` |
| 5 → 9–12 | `render`, `ensure_certs` | T5 → targets | `ensure_certs` fallback matches `lab.py` lines 59–68 exactly (verified) | — |
| 6 → 9–12 | `compose.up/down/reload_nginx/recreate` | T6 → targets | Compose derives the project name from the compose file's directory: `demcommerce/deploy/` and `civic-services-portal/deploy/` **both** resolve to `deploy`, so their containers, networks and `exec nginx` targets would collide, and one target's `down` would stop the other | Every new compose file sets a top-level `name:` — `democommerce-lab`, `civic-portal-lab`, `juice-shop-lab`, `vampi-lab`. Note added to the File Structure section; `reload_nginx` must pass `-f` (it does) |
| 7 → 8, 9–12 | target module interface | T7 → CLI + targets | **Contradiction inside the plan:** File Structure declared `nginx_config(state) -> str`, while Task 7 requires eservices' `nginx_config` to return `None` (`lab.py` owns that template) | Type is `str \| None`; only tests consume the value, `apply()` owns the side effects. File Structure corrected |
| 7 → 9–12 | `targets/__init__.py` `MODULES` | T7 creates, T9–12 append | Each later target task appends one registration line | Serial execution (never dispatch two implementers in parallel) — no conflict |
| 9 ↔ 9 | `demcommerce/deploy/lab.compose.yaml` | — | `build: ../../backend` resolves from the compose file's directory to `<root>/backend`, which does not exist | Corrected to `../backend` |
| 9, 10 → live verification | `frontend/dist/`, `dist/` | — | **Both are gitignored by the apps' own `.gitignore` files**, so neither exists in this worktree (they exist only in the main checkout, which was never committed with them). nginx would mount an empty directory, `/` would answer 404, and `http-plain` could never return 2xx | Added a build prerequisite to each task (`npm ci && npm run build`; copy from `/mnt/data/eservices-lab/…` as the network fallback). npm registry verified reachable (HTTP 200), node v24.22.2 / npm 11.19.1 present |
| 9 → `probe_http_plain` | `{{HTTP_BLOCK}}` drift value | shared vocabulary → DemoCommerce | The shared drift value proxies `/` to the API, but DemoCommerce's FastAPI app has **no `/` route** → 404 → probe `unknown` → `verify` fails whenever `http-plain` is on. The old test passed anyway because `proxy_pass http://app;` also appears in the literal `location /api/` block | DemoCommerce's drift value is `location / { try_files $uri $uri/ /index.html; }`; the test now isolates the `listen 80` block and asserts `try_files` present, `proxy_pass` absent |
| 10 → live verification | Flask bind address | — | Plan said "loopback in-container", but nginx **and** the published `8084` port both reach the container through its interface — a loopback bind would make every request fail | Bind `0.0.0.0:5000` in-container; host exposure remains loopback-only because only `127.0.0.1:8084` is ever published |
| 6/9–12 → `up()` | persisted state | — | Nothing re-applied state after `up`: a persisted `on` scenario would be recorded as present while the config was still baseline, so `verify` would fail after a restart | Target interface comment now specifies `up()` ends with `apply({}, read_state())` |
| 11 → `up()` | readiness probe | — | Waiting on `/rest/admin/...` returns **403 from nginx at baseline**, i.e. "ready" before Juice Shop has booted | Poll `GET /` (always proxied) until status < 500, ~180 s timeout |
| 12 → `up()` | `/createdb` | — | Unclear where the call goes; the raw container port is not published | Through the controlled host (not blocked at baseline), then poll `GET /` until < 500 |
| 13 → 8 | `sequence.py` drives the frozen CLI | — | Step 5's `S0/S1/S2` short cycle vs spec §6.5's `S1..S9` look contradictory | Different purposes, both correct: S0 must be marked first so S1 classifies as `NEW` rather than `BASELINE`. Documented in the step |
| 13 → protected files | `eservices-lab/README.md` | — | The one permitted edit to a file on the never-modify list | Already the stated exception in Global Constraints |

### Per-task self-consistency — one row per task

| Task | Its text vs itself | Finding | Ruling |
|---|---|---|---|
| 1 | files vs steps | Step 1 duplicates setup already done | Rewritten as verify-don't-redo |
| 2 | test vs spec | Histories/labels match §6.5; `test_labels_are_within_the_frozen_set` correctly uses subset (`<=`) | — |
| 3 | interface vs test | 9 CSV columns ↔ 9 `GroundTruthRow` fields, stated explicitly | — |
| 4 | test vs code | The `cafiles` change ripples into the cert-mismatch test | Test renamed + untrusted-CA case added |
| 5 | files vs steps | `tests/test_render.py` and `tests/test_certs.py` both listed and both written | — |
| 6 | files vs steps | `test_conpose.py` typo already corrected to `test_compose.py` | — |
| 7 | test vs interface | `test_nginx_config_is_not_reimplemented` contradicted `-> str` | `str \| None` (see pair table) |
| 8 | test vs code | DOWN semantics unspecified; root `domain.py` shim vs `domain/` package | DOWN rule added; shim/package resolution **empirically verified** earlier (`python domain.py` imports the package, not the module) |
| 9 | paths vs repo | Wrong directory name, wrong build context, missing `dist` | All three corrected (see below) |
| 10 | paths vs repo | Missing `dist`, wrong bind address | Both corrected |
| 11 | paths vs repo | `targets/` does not exist yet (task creates it ✓); readiness check wrong | Readiness corrected |
| 12 | paths vs repo | `targets/` absent (✓); `/createdb` routing unclear | Clarified |
| 13 | steps vs repo | `eservices-lab/README.md` exists and ends with a `## Notes` section | Append is safe |

### Global finding — the directory name was wrong in both documents

Verified byte-precisely from `os.listdir`:

| What | Value |
|---|---|
| Real directory (12 bytes: `d e m o c o m m e r c e`) | **`democommerce`** (prefix `demo`) |
| Real Python package under `backend/` | `demcommerce` |
| Real Dockerfile | `COPY demcommerce ./demcommerce`, `uvicorn demcommerce.main:app` |
| Real README heading | `# DemoCommerce` |
| Plan occurrences of the wrong `demcommerce` | 17 (+1 `Demcommerce`) |
| Spec occurrences of the wrong `demcommerce` | 13 |

**Ruling:** both documents are corrected to `democommerce` — for filesystem paths, the CLI target name, the target module file, and therefore the `finding_key` target segment. This is a factual correction against the repository, not a change to scope, the redaction rule or the classification rules; no artifact consumes the name yet (the ground-truth file and the scanner do not exist), so nothing downstream is frozen. **Cost if wrong:** one rename of a string that only these two documents define, before any row is written.

### Rulings recorded (spec is the authority, the plan is its argument)

1. **Ruling:** correct `demcommerce` → `demcommerce` in plan and spec — it does not exist on disk; the plan's Task 9 would have failed at its first `cd`. — *why:* a path that does not exist is a bug, not a design decision. — *cost if wrong:* one rename, pre-freeze.
2. **Ruling:** `probe_cert_mismatch(host, port, cafiles: Sequence[Path])`, `present` only for a hostname-verification failure — *why:* reproduces `lab.py p_cert` exactly, which is the only behaviour the eservices target has been validated against. — *cost if wrong:* a mis-scored `cert-mismatch` scenario on one target.
3. **Ruling:** DOWN := `probe_port_open(host, port(base_url)) == "absent"`; a DOWN target reports `UNKNOWN` everywhere and never fails `verify`; `mark` records `None` — *why:* spec §6.6 mandates it and no other test distinguishes "stack not up" from "observation inconclusive". — *cost if wrong:* a down target could be scored as `NO DRIFT`, which Review Focus #3 exists to prevent.
4. **Ruling:** every new compose file sets a top-level `name:` — *why:* without it two targets share the project name `deploy`. — *cost if wrong:* none; the names are internal.
5. **Ruling:** build both `dist/` bundles in the worktree (copy from the main checkout only if `npm ci` fails) — *why:* they are gitignored, so the worktree has no UI to serve. — *cost if wrong:* a few minutes of npm time.
6. **Ruling:** DemoCommerce's `{{HTTP_BLOCK}}` drift value serves the static bundle rather than proxying — *why:* the API has no `/` route, so the shared value would break `http-plain`. — *cost if wrong:* none; the shared default still applies to Juice Shop.
7. **Ruling:** the civic API binds `0.0.0.0:5000` in-container — *why:* a loopback bind is unreachable from nginx and from the published port. — *cost if wrong:* none; host exposure is still loopback-only.
8. **Ruling:** `up()` re-applies persisted state — *why:* otherwise ground truth and configuration disagree after a restart. — *cost if wrong:* one extra `apply` call per `up`.
9. **Ruling:** Juice Shop / VAmPI readiness polls `GET /` until status < 500 — *why:* the blocked admin paths answer 403 from nginx regardless of application state. — *cost if wrong:* a slow `up()` or an early return.

### YAGNI watch (known, deliberate — adjudicate, do not silently drop)

- `probe_api_path(..., tls=False)` — no target uses plain HTTP for `api-debug`; kept for interface symmetry.
- `ensure_certs` also creates root `mismatch.crt/.key` — only eservices has a `cert-mismatch` scenario and it uses `eservices-lab/certs/`. Plan-mandated; cheap.
- `Target.scope` — mirrors `lab.py` vocabulary, no consumer yet. Plan-mandated by Task 1's test.
- The four target modules repeat the same placeholder-mapping shape. Structural, with different content per target; a shared base class now would be premature.

---

## Progress

- Task 1: implemented (commit `c77f3e1`), review dispatched.
- Task 1: review returned **Needs fixes** — 1 Important: five stale `demcommerce` spellings inside plan text added *after* the pre-flight rename sweep (plan lines 108, 662, 669, 672, 675 — including the executable `cd demcommerce/frontend` command Task 9 will run). Code deliverables judged fully spec-compliant. Verified independently: `grep -c demc` on the plan = 5; on the spec = 0.
- Task 1: minor (deferred): spec §6.7's tree still roots at `eservices-lab/` with `domain/` beneath it, while the code creates `domain/` at the repo root — align in a later doc pass.
- Task 1: minor (deferred): `Target` frozen-ness, `ProbeResult` literal values and `domain.ROOT` have no direct test coverage (the brief prescribed exactly four tests).
- Task 1: minor (deferred): `Scenario.area` is a plain `str`, so a typo'd area would yield a `finding_key` outside `{TLS, Network, API}` — **carry into Task 3**: the ground-truth row writer is the natural place for that guard, since it freezes the schema before any row is written.
- Task 1: minor (deferred): the two `finding_key` tests repeat an identical `Target(...)` fixture — plan-mandated verbatim transcription; fixture data, not a logic block.
- Task 1: fix round 1/5 (1 addressed, 0 open — five stale directory spellings in plan text; commits `c77f3e1`..`0f09d10`); re-review verdict: all findings addressed, no new Critical/Important breakage.
- Task 1: complete (commits `9651108`..`0f09d10`, review clean).
- Task 1: minor (deferred, from re-review): `docs/superpowers/specs/…design.md` §6.6 still shows bare `python domain.py …` commands (6 hits) — `python` is not on PATH here; fold into the final doc pass.
- Task 2: implemented (commit `a554ad6`), review dispatched (package `review-0f09d10..a554ad6.diff`).
- Task 2: review verdict **Approved / spec-compliant, no Critical or Important** — classifier branch order traced shadow-free against §6.4; cross-check verified as 32 real comparisons against `drift.py` with correct signature and `ROOT` resolution.
- Task 2: minor (deferred): no `classify([]) == []` test (holds by construction only).
- Task 2: minor (deferred, plan-mandated): the four frozen histories appear twice in `tests/test_classify.py` (`HISTORIES` at :10-14 and inline at :20,26,32,38) — fixture duplication, could desynchronize.
- Task 2: minor (deferred): `any(history[:i-1])` re-slices per iteration — O(n²); irrelevant at n≈9.
- Task 2: complete (commits `0f09d10`..`a554ad6`, review clean).
- Task 3: implemented (commit `9ce5594`), review dispatched (package `review-a554ad6..9ce5594.diff`).
- Task 3: review verdict **Approved / spec-compliant, no Critical or Important** — 9-column schema, all 7 mandated tests plus the controller's area guard (`GroundTruthRow.__post_init__` → `ValueError`, exercised by `test_row_writer_rejects_an_unknown_area`) verified; RED `ImportError` judged same root cause as predicted `ModuleNotFoundError`.
- Task 3: ⚠️ adjudicated — down scan contributes `False` to the classify history while its own label is `None`. **Ruling:** keep as-is; plan line 312 mandates exactly this ("calling classify on the boolean history and substituting `None` for any scan where that target was down"), and spec §6.6's only requirement is that the down label is excluded from scoring, which holds. The residual edge (a mid-sequence down gap could turn PERSISTENT into RECURRING at a later live scan) cannot arise in the canonical nine-scan sequence, which spec §6.6 requires to run with all five targets up. Flag for the final review as a known plan behaviour.
- Task 3: carry into Task 8 — `truth_matrix`'s `None` must be treated as "excluded from scoring", never compared as a label (already pinned by plan line 32 and Task 8's tests); verify in Task 8's review.
- Task 3: minor (deferred): comment at `domain/state.py:53-55` overstates the guard ("no `finding_key` can ever leave …") — only `category` is validated; a hand-built `finding_key` with a bad middle segment would pass. Soften the comment or check `finding_key.split("/")[1]`.
- Task 3: minor (deferred): bare `zip(down, labels)` at `state.py:104-105` — `strict=True` would catch future contract drift.
- Task 3: minor (deferred): no test for `truth_matrix` with zero scans (verified safe: `classify([])` → `[]`).
- Task 3: complete (commits `a554ad6`..`9ce5594`, review clean).
- Task 4: implemented (commit `e2063fe`), review dispatched (package `review-9ce5594..e2063fe.diff`).
- Task 4: review verdict **Approved / spec-compliant, no Critical or Important** — all five probe mappings traced branch-by-branch against the pre-flight rulings; every `lab.py` mirror claim verified against source (`p_cert` two-CA + code 62 + `server_hostname="localhost"`); socket/timeout/teardown mechanics checked against CPython `ssl.py`. Implementer's own concern (timeout→absent in `probe_port_open`) dismissed as conforming to the DOWN ruling.
- Task 4: minor (deferred): `probes.py:59-61` — `load_verify_locations` outside the `try`; a missing/corrupt CA raises instead of returning `unknown`.
- Task 4: minor (deferred): `probes.py:35-42` — `minimum_version` set after `create_connection` but before `with`; hypothetical setter raise could leak the fd (verified not to raise on this build).
- Task 4: minor (deferred): `probes.py:26-27` — bare `simplefilter("ignore")` suppresses all warning categories; scope it to `DeprecationWarning`.
- Task 4: minor (deferred): no test exercises `probe_api_path(tls=True)` (the HTTPSConnection default branch) — all api tests pass `tls=False`.
- Task 4: minor (deferred): `_closed_port()` bind-then-release race could cause spurious failure of `test_port_open_refused_is_absent`; keep the socket bound-but-not-listening instead.
- Task 4: complete (commits `9ce5594`..`e2063fe`, review clean).
- Task 5: implemented (commit `45869cb`), review dispatched (package `review-e2063fe..45869cb.diff`).
- Task 5: review verdict **Approved / spec-compliant, no Critical or Important** — `render` raises `ValueError` naming any leftover `{{…}}` (literal `str.replace`, nginx `$host` vars structurally safe); `ensure_certs` mirror of `lab.py gen_certs` verified line-by-line; `{{CERT}}` → `localhost.crt` naming proven end-to-end; cert tests parse real openssl output. Self-flagged extra test judged fair (cheap, read-only, pins the integration surface).
- Task 5: minor (deferred, mirror-mandated): `certs.py:39` — `stderr=DEVNULL` discards openssl diagnostics on failure (`CalledProcessError` still propagates).
- Task 5: minor (deferred, mirror-mandated): `certs.py:29` — skip checks only `.crt`, so a half-written pair is never repaired.
- Task 5: minor (deferred): Docker fallback in `ensure_certs` untested (local openssl always used here).
- Task 5: minor (deferred): default `cert_dir=ROOT/"certs"` exceeds the brief's literal signature — any caller omitting it writes repo-root `certs/`; flag to Tasks 9–12 to always pass their own dir.
- Task 5: minor (deferred): `test_creates_both_certificates` asserts existence only — `mismatch.crt` content never parsed.
- Task 5: complete (commits `e2063fe`..`45869cb`, review clean).
- Task 6: implemented (commit `dbdfeea`), review dispatched (package `review-45869cb..dbdfeea.diff`).
- Task 6: review verdict **Approved / spec-compliant, no Critical or Important**; 2 Minors deferred (three-site argv duplication across `up`/`recreate`/`run`; `reload_nginx`'s `check=False` discards every failure, brief-mandated).
- Task 6: ⚠️ confirmed as a real cross-task gap. `_files` hardcodes `project_dir/"compose.yaml"` (compose.py:16), but Task 9's stack is `demcommerce/deploy/lab.compose.yaml` and the plan forbids reusing `demcommerce/deploy/compose.yaml` (plan:662, spec §6.7). A target module passing `demcommerce/deploy` would silently drive the protected production stack — and `reload_nginx`'s `check=False` would hide the failure. No consumer exists yet (Tasks 9–12 unwritten), so the fix is cheap now.
- **Ruling (spec as authority):** the compose helpers take the compose **file path** explicitly, not a directory — `run(compose_file, *args, check=True)`, `up(compose_file, override=None)`, `down(compose_file)`, `reload_nginx(compose_file)`, `recreate(compose_file, override=None)`. Rationale: `-f` is then always the single source of truth, directory/`compose.yaml` inference disappears entirely, and `lab.compose.yaml` is handled by construction. Spec §6.7 mandates that file name and forbids reusing `deploy/compose.yaml`, so correctness outweighs the plan's original `project_dir` phrasing (plan:473-478 amended to match; consumers are unwritten, so nothing downstream changes). — *cost if wrong:* one signature rename before any target module exists.
- Task 6: fix round 1/5 dispatched (extend `compose.py` + tests + plan Task 6 interface block to the `compose_file` signature; verification: full suite green and argv tests assert an explicit `-f <file>`).
- Task 6: minor (deferred): `_files`/prefix logic — unify `up`/`recreate` onto `run()` once signatures settle.
- Task 6: fix round 1/5 (compose helpers now take an explicit `compose_file: Path`; commits `dbdfeea`..`943687e` incl. plan amendment); re-review verdict: all findings addressed, no new Critical/Important breakage, no pre-existing caller broken.
- Task 6: complete (commits `45869cb`..`943687e`, review clean).
- Task 7: implemented (commit `b3077a2`), review dispatched (package `review-943687e..b3077a2.diff`).
- Task 7: review verdict **Approved / spec-compliant, no Critical or Important** — all seven interface members, registry contract (`TARGETS`/`get`), shell-out delegation to `lab.py` (`python3 eservices-lab/lab.py <subcommand>`), `read_state` missing-file → all False, `nginx_config → None`; certs absence non-blocking (`lab.py` generates them at live runtime).
- Task 7: minor (deferred): `read_state` raises `JSONDecodeError` on corrupt `state.json` (missing-file handled; corrupt not specified).
- Task 7: minor (deferred): `read_state` not tested for the "file missing entirely → all False" path.
- Task 7: minor (deferred): `_lab` shell-out has no `timeout`/`capture_output` (defensive; tests mock it).
- Task 8: implemented (commit `62b00ed`), review dispatched (package `review-b3077a2..62b00ed.diff`).
- Task 8: review verdict **Approved / spec-compliant, no Critical or Important** — root shim exact, all nine subcommands, `--json` valid JSON, exit 0/1/2 discipline, DOWN via `probe_port_open == "absent"` consistently across status/verify/mark, DOWN targets never fail verify and are recorded as `None`.
- Task 8: minor (deferred): `reset` exposed but behavior-untested beyond parser exposure (plan-mandated exposure satisfied).
- Task 8: minor (deferred): `on`/`off` happy-path `apply()` not tested beyond the two rejection cases the brief specified.
- Task 9: starting — DemoCommerce lab stack (`demcommerce/deploy/lab.compose.yaml`, `deploy/nginx/lab.conf.tpl`, `deploy/nginx/conf.d/.gitkeep`, `domain/targets/demcommerce.py`, tests). Prerequisite: build `demcommerce/frontend/dist` (gitignored, absent in worktree; main checkout has it).

### Prep for Tasks 9–13 (controller, read-only checks + gitignored build artifacts)

- **Both front-end bundles built** in this worktree by the controller: `demcommerce/frontend/dist/` and `civic-services-portal/dist/` each contain `assets/` + `index.html`, produced with `npm ci && npm run build` (node v24.22.2 / npm 11.19.1; registry reachable; 0 vulnerabilities). The vite build prints one rollup advisory about a `"use client"` directive in `lucide-react` — a warning, not an error; the build succeeds. Both paths are gitignored, so they are never committed. Task 13's `docs/domain.md` records this route (npm build, not copy).
- **Fictional-data conventions confirmed** against the source of truth `eservices-lab/app/server.py`: `API_KEY = "lab-demo-key"`; ids `TEST-%04d` and `CMTEST%08d`; phones `+256700000%03d`; internal hosts `db-internal.eservices.test` and `10.20.0.5`/`10.20.0.6`; the debug payload shape is `{"db": "postgres://svc_admin:lab-secret@db-internal.eservices.test:5432/records", "internal_hosts": [...], "api_key": ..., "sample_record": RECORDS["TEST-0001"]}`. The civic portal's `/api/v1/admin/debug` must mirror this exactly (spec §6.6).
- **Civic React UI is self-contained**: `civic-services-portal/src/App.jsx` hardcodes its six services and makes **no** API calls (`grep` for `api/|fetch(|axios` in `src/` → no hits). The new Flask API is therefore an independent lab surface; the UI is served statically by nginx from `../dist`. `src/**` stays untouched.
- **Placeholder vocabulary (plan lines 97–105)**: the shared vocabulary is `{{HTTP_BLOCK}}`, `{{DEBUG_LOCATION}}`, `{{SSL_PROTOCOLS}}`, `{{SSL_CIPHERS}}` plus `{{CERT}}`; `render()` (domain/render.py:13-20) replaces only the keys it is given and raises `ValueError` on any leftover `{{`. **Pass all five keys on every target** — extra keys are harmless, a missing one is fatal.
- **Deploy-directory depth is uniform**: `civic-services-portal/deploy/`, `democommerce/deploy/`, `targets/juiceshop/`, `targets/vampi/` are all two levels below the root, so `../../certs` resolves to the root `certs/` from all four (plan:80).
- Task 13's "seventeen scenarios" arithmetic verified: eservices 5 + democommerce 3 + civic 3 + juice-shop 3 + vampi 3 = 17.
- Task 13's toggle sequence verified against the spec §6.5 table (spec:244-254) — the brief's S1–S9 schedule matches character-for-character.
- Task 13's S0-before-S1 requirement confirmed: the first mark of a present scenario is `BASELINE`, not `NEW` (spec:229, plan Task 13 Step 5).
- Deferred minor (final review): spec §6.6 lists `address` among the registry fields, but `Target` (domain/model.py:16-24) has no `address` field — it is derivable from `base_url`. Plan-mandated model; the backend can derive it.

- Task 9: implemented (commit `3edb3ca`), review dispatched (package `review-62b00ed..3edb3ca.diff`).
- Task 9: review verdict **Approved / spec-compliant, no Critical or Important** — three scenarios/ports correct, baseline 404 mask and drift proxy verified, compose file (name / build context / network / env / mounts / loopback-only publishes) checked line-by-line, `apply`→write+reload and `up()`→`apply({}, read_state())` verified, no protected or out-of-scope file touched.
- Task 9: ⚠️ live verification blocked by the **environment**, not the code: `docker images` fails with `children: invalid desc sha256:3323…: invalid character '$'` (a pre-existing corrupt unrelated image on this machine) and `nginx:1.27-alpine` could not be pulled at the time. **Resolved since:** the controller pulled `nginx:1.27-alpine` successfully (rc=0, digest `sha256:65645c7b…`) and `bkimminich/juice-shop:latest` is present. `erev0s/vampi:latest` still pulling. No live result was ever invented.
- Task 9: **Ruling (fix required now, not deferred):** the debug location must be the plan's `{{DEBUG_LOCATION}}` placeholder, not an inlined template line plus a post-render `str.replace`. The plan's shared vocabulary (plan:97–105) lists `{{DEBUG_LOCATION}}` with baseline/drift values and says the vocabulary is *identical across all four new templates*; the eservices reference template uses it too. Task 9 instead inlines `location = /api/internal/security-profile { return 404; }` in `demcommerce/deploy/nginx/lab.conf.tpl` and swaps it after rendering (`domain/targets/democommerce.py:73-74`) — a mechanism that silently no-ops if that text ever drifts. **Why now:** Tasks 10–12 are about to copy this shape; fixing four modules + four templates + four test files afterwards is far costlier than fixing one now. — *cost if wrong:* one template line and one mapping entry per target.
- Task 9: environment note for all later implementers — this worktree's filesystem returns **stale directory listings**: `ls`/`find`/`readdir` on a parent can omit existing subdirectories, while direct path access (`cat`, `head`, `git show`, `test -f`) works, and `git status` stays clean throughout. If a path looks missing, verify with `git show HEAD:<path>` — **never** delete or recreate a tracked file because a listing hid it.
- Task 9: fix round 1/5 dispatched (adopt `{{DEBUG_LOCATION}}`; retry the live bring-up now that the nginx image is available).
- Task 9: fix round 1/5 **addressed** (commit `8efcf51`): template now carries `{{DEBUG_LOCATION}}`, the module passes `DEBUG_LOCATION` in the mapping (baseline 404 / drift proxy), the post-render `cfg.replace(...)` and the unused `_API_BASELINE` constant are gone, rendered output unchanged; re-review verdict: all findings addressed, no new Critical/Important breakage. Scope check passed — only the template and the module changed.
- Task 9: minor (deferred): the rendered debug location is now indented 8 spaces (placeholder indented + value carries its own 4-space prefix), consistent with the plan's `{{HTTP_BLOCK}}` convention; nginx accepts it and the substring assertions still hold.
- Task 9: live verification still blocked by the **host** Docker image store: `docker images` fails with `children: invalid desc sha256:0745…: invalid character '$'` (an orphaned descriptor from the aborted build; `docker rmi` by name cannot reach it, and `netvision-frontend-1` is off-limits). Pulls, `image inspect` and `compose up --build` still work — the api build simply needs longer than the harness foreground timeout. **All three benchmark images now pulled OK** (`nginx:1.27-alpine` `sha256:65645c7b…`, `bkimminich/juice-shop:latest` `sha256:877fc77b…`, `erev0s/vampi:latest` `sha256:0a5a224b…`); `python:3.12-slim` (base for the api builds) pulling.
- Task 9: **process change (controller):** live bring-up and `verify` are run by the controller centrally, in the background with long timeouts, instead of by each implementer in the foreground — the harness timeout was killing long image builds mid-flight, which is what left the orphaned descriptor. Implementers deliver code + unit tests + commit; the controller runs the live pass per task and records the result.
- Task 10: implemented (commit `b462a4e`), review dispatched (package `review-8efcf51..b462a4e.diff`).
- Task 10: review verdict **Approved / spec-compliant, zero findings** — three scenarios, `approved_ports=(8445, 8083)` with 8084 correctly excluded and in `drift_ports`, baseline 403 / drift proxy, override switching both ways via `compose.recreate`, all five placeholders passed, fictional-only debug payload, `0.0.0.0:5000` bind, `src/**` untouched, both brief-specific tests present.
- Task 10: complete (commits `8efcf51`..`b462a4e`, review clean; live verification pending the controller's central pass).

### The "ghost directory" incident — root cause and ruling (controller)

What looked like a corrupted filesystem is now fully explained, and the repository is clean again (`git status` empty, `git add -A -n` empty, index and HEAD agree at 112 entries).

**Root cause:** the worktree root contained **two** directories whose names differ only by one letter — an 11-byte `demcommerce` and the real 12-byte `democommerc`. The 11-byte one was **created by my own `mkdir -p demcommerce/deploy/nginx`** during the first filesystem confusion: the plan still carried the stale 11-byte spelling in two places (the Task 6 "Compose-file ruling" paragraph, which I wrote during the pre-flight sweep, and the Task 9 verification note), so that path never existed on disk and `mkdir` happily created it. Every symptom followed from that one directory:

- `cd demcommerce/frontend` failed — the rogue directory held only `deploy/nginx`.
- `git status` reported `?? demcommerce/` — correct behaviour for an untracked directory.
- `git add -A -n` listed the *tracked* 12-byte tree's files — it was reading them through the newly created tree, not through the index.
- The Task 9 implementer's live bring-up failed with `open …/demcommerce/deploy/lab.compose.yaml: no such file or directory` — **the plan's command used the wrong path**, not a Docker fault.

**What was NOT the cause** (recorded so it is not re-investigated): the Docker image-store errors are real but independent — `docker images` fails with `children: invalid desc sha256:…: invalid character '$'` (an orphaned descriptor from an aborted build), while pulls, `image inspect` and `compose up --build` all work. The `netvision-frontend-1` image was never touched.

**Ruling and repair (done):**
1. Deleted the rogue 11-byte directory after verifying the real 12-byte tree was complete (42 files, `lab.compose.yaml` 1089 B, `lab.conf.tpl` 1004 B, `frontend/dist` present, `node_modules` present).
2. Corrected the plan's last 2 stale-spelling occurrences (the Task 6 ruling paragraph) → commit `cd54ba7`. Both documents now contain **0** occurrences of the stale spelling, verified by a programmatic check that derives both spellings rather than typing them.
3. Regenerated the Task 9 brief (0 stale hits).
4. `git status` is clean and `git add -A -n` reports nothing.

**Rule for every later implementer (and for me):** never type this directory's name from memory — derive it (`os.listdir` + length, or copy from an existing path). Two spellings are one keystroke apart and only one exists. When a path "does not exist", check for a near-duplicate sibling before concluding the filesystem is broken.

### Live verification pass (controller) — five defects found, all fixed

Running the targets for real found defects that no amount of reading the code would have surfaced. All were fixed in fix rounds with unit tests; each fix was then re-verified live.

| # | Defect | Symptom | Root cause | Fix |
|---|---|---|---|---|
| 1 | Target state never persisted | `on tls-legacy` then `on http-plain` then `on api-debug` left only the **last** scenario active; `mark` would have recorded the wrong ground truth | the new modules' `apply()` applied the config but never wrote their state file (`lab.py` persists it for eservices, so only the new targets were affected) | `caf6594` — each module persists `current` via the existing `domain/state.py` `write_state` helper; invariant: **`apply(previous, current)` ⇒ `read_state() == current`** |
| 2 | DemoCommerce plain-HTTP drift returned **500** | `http://127.0.0.1:8082/` → 500 with nginx's `rewrite or internal redirection cycle` | the `listen 80` server block had no `root`/`index`, so `try_files` resolved against nginx's compiled default root (`/etc/nginx/html`, absent) | `0b899d1` — `root /usr/share/nginx/html;` + `index index.html;` in the port-80 block |
| 3 | `apply()` returned before the new config was live | `verify` issued right after the toggles observed the **previous** configuration | `nginx -s reload` is asynchronous — measured **~150 ms** before the new workers took over | `0b899d1` — the CLI now waits (poll the target's probes) until the live behaviour matches the intended state; timeout ⇒ loud stderr + exit 1 |
| 4 | Civic `api-debug` drift never applied | debug endpoint stayed 403; the drift silently did nothing | the rendered drift used `proxy_pass http://api:5000/...` while the template declares `upstream api { … }` — nginx rejects an upstream-group reference carrying a port (`[emerg] upstream "api" may not have port 5000`) | `f84b80a` — the drift proxies to `http://api/...` (no port), matching the sibling target's template |
| 5 | An nginx-rejected configuration failed **silently** | `reload_nginx` uses `check=False` (plan-mandated), so a bad config looked like success | same as above — nginx logs the emerg; the exec still exits 0 | `f84b80a` — `compose.validate_nginx_config()` runs `nginx -t` **before** the reload and raises with nginx's own diagnostics; the config write is also now atomic (`os.replace`), so nginx never sees a partial file |

**Live results after the fixes (all re-run by the controller):**

- DemoCommerce: baseline ⇒ all three probes `absent`, `verify` exit 0; curls 404 / 301 / 200. All drift on ⇒ all three probes `present`, `verify` exit 0; curls **204** (profile endpoint) / **200** (plain HTTP) / **200** (HTTPS).
- Civic portal: baseline ⇒ all three probes `absent`, exit 0; curls **403** (debug endpoint) / **301** / **000** (port 8084 refused) / **200**. All drift on ⇒ all three probes `present`, exit 0; curls **200** (debug endpoint) / **200** (port 8084 published).
- `port-open` mechanics verified end to end: `on` publishes `127.0.0.1:8084`, `off` withdraws it. A container recreation takes **~12 s** (measured), so the settle timeout was raised from 30 s to **60 s** (`5ecb48b`) after the 30 s budget proved flaky right after another recreation.

### Two more live-found defects (Tasks 11–12) and one environment hazard

| # | Defect | Symptom | Root cause | Fix |
|---|---|---|---|---|
| 6 | `up()` waited for readiness **before** applying the configuration (both benchmark targets) | Juice Shop: `did not become ready at https://127.0.0.1:8446/ within 180s: [SSL: UNEXPECTED_EOF_WHILE_READING]`; VAmPI: `/createdb initialization failed … [Errno 104] Connection reset by peer` — and the rendered config was never written at all | the controlled host only serves its configured server blocks once the config is in place; before that nginx runs the stock image config, which has no TLS server | `ec9d602` — `up()` now does `compose.up → apply({}, read_state()) → (init) → readiness wait`, matching the brief's own wording ("nginx answers 502 until then") |
| 7 | Juice Shop proxied to an upstream group **with a port** | the drift silently did nothing — nginx refused the whole configuration with `[emerg] upstream "juice-shop" may not have port 3000` | `upstream juice-shop { server juice-shop:3000; }` plus `proxy_pass http://juice-shop:3000` | `ec9d602` — proxy to the group without a port (`http://juice-shop`), as VAmPI already did |
| 8 | VAmPI's `/createdb` init ran before the application could serve it | the app logged `sqlite3.OperationalError: no such table: users`; the debug scenario returned **500** instead of 200, so `verify` reported `api-debug: unknown (expected present) MISMATCH` | `up()` called `_init_db()` before the app was ready; a single attempt with no retry | `563395e` — `up()` waits for readiness first, and `_init_db()` retries `/createdb` until it succeeds (60 s bound) |

**Hazard — the test suite and `git clean` can corrupt the live domain.** The live state files (`*/state.json`, `*/deploy/lab.state.json`) and the rendered nginx configs (`*/conf.d/default.conf`) are **gitignored**, and the built front-end bundles are too. During the live pass, a `git clean -fdx` from an earlier fix round deleted DemoCommerce's bundle, `node_modules`, state file and rendered config, and a test that reached a real module's `up()` rewrote two live state files with all-False values — so `verify` reported `tls-legacy: present (expected absent) MISMATCH` for a target whose drift was deliberately on. The ground truth is the authoritative record, so this must not be possible.

- **Rule for every implementer:** never run `git clean` (any form) in this worktree; tests must never write the repository's live state or config paths.
- Guard added: `tests/__init__.py` snapshots the live paths and `tests/test_live_path_guard.py` exercises each registered module's `apply()`/`up()` with the paths redirected and the side effects mocked, failing if any live file's existence, size, mtime or bytes change (`3db4bc9`). The rule is documented in `tests/__init__.py` and `tests/README.md`.
- The controller restored the deleted artifacts by rebuilding the bundle (`npm ci && npm run build`) and re-running `domain.py up`.

### Tasks 11–13 and the remaining fix rounds

- **Task 11 (Juice Shop)** — implemented (`1aa2d49`), review dispatched (`review-cd54ba7..81d7069.diff`), verdict **Approved, zero Critical/Important** (2 Minors: the upstream-group form is inconsistent with the other targets — folded into the Defect F fix; a readiness test could raise `StopIteration` instead of a clean failure — deferred).
- **Task 12 (VAmPI)** — implemented (`81d7069`).
- **Task 13 (sequence + docs + README note)** — implemented (`c633617`): the **classification matrix reproduced exactly** against spec §6.5 for all four scenario groups / seventeen scenarios (every one of the five states appears in each of the three areas), and the domain was left up with every scenario off and `verify` exit 0.
- **Defect 9 (VAmPI loses its database on a recreate)** — `port-open` recreates the container and the SQLite database lives inside it, so the tables were gone: the app logged `no such table: users`, `GET /users/v1/_debug` answered **500**, and the unattended `sequence.py` run **stopped at S6**. Fixed by `04adfa6`: `apply()` re-initialises the database after a recreate, **before** the state is persisted (design (a) — no dependency on the image's database path).
- **Task 13's own finding** — the unattended `sequence.py` run is the deliverable's proof; it failed at S6 for the reason above and now passes end to end (verified by the controller).
- Final state of the domain after the whole build: **all five targets up**, `python3 domain.py verify` exits **0** with all seventeen scenarios reporting `absent (expected absent) OK` at baseline.

### Final whole-branch review and the fix wave

- **Final whole-branch review** dispatched over the whole branch (`review-9651108..a891a80.diff`, 28 commits): verdict **Ready to merge: Yes (with fixes optional)**, **no Critical findings**. The reviewer confirmed the frozen contracts are implemented faithfully, the live-found fixes are baked into the design rather than papered over, DOWN semantics and ground-truth integrity are handled carefully, exposure is loopback-only, and the drift ports are excluded from `approved_ports`.
- **Deferred-minor triage (28 items):** the reviewer classified **none** as merge-blocking. Documentation/spec alignment, test-coverage polish, defensive hardening (probe CA loading, cert diagnostics, corrupt-state handling, subprocess timeouts) and two style items may be deferred; three items are **moot** (the compose `project_dir` collision, Task 9's fragile post-render debug swap, and the stale directory spellings) because later fix rounds closed them.
- **Fix wave** (one subagent, complete findings list, per the skill's guidance): `fb68ac1` — (1) the eServices wrapper now converges to the **absolute** intended state (every scenario driven from `current`, so a divergence between `state.json` and the live config can no longer strand a toggle); (2) the ground-truth row guard now binds `finding_key` to `f"{target}/{category}/{scenario}"` and the area to `AREA_LABELS`, so a disagreeing row cannot enter the authoritative log; (3) `sequence.py` refuses to run when any target is DOWN instead of silently producing a misleading matrix; (4) the documentation alignment the reviewer asked for (spec §6.6 `python`→`python3`, the spec's file tree rooted at the repository root, the npm fallback note, and the README's entry-point clarification).
- **Explicitly declined, with a ruling:** the Civic portal's debug handler must **not** be gated behind a flag. The endpoint is deliberately always present and the controlled host is what masks it — that is the scenario's definition in spec §6.6, and it matches `eservices-lab/app/server.py`, where `/api/v1/admin/debug` is likewise unconditional and masked by nginx. The payload is synthetic by the fictional-data convention. *Cost if wrong:* the "accidental exposure" scenario would model a flag rather than a missing proxy rule.
- **Scoped re-review of the fix wave:** all findings ADDRESSED, no new Critical/Important breakage, no out-of-scope observations, no findings left open.
- Final suite: **175 tests, OK**, pristine output. Live `python3 domain.py verify` after the fix wave: exit 0, 17 scenarios OK, 0 mismatches.


1. **Ruling:** the compose helpers take an explicit **compose file path**, not a directory (`up`/`down`/`reload_nginx`/`recreate`/`run`). *Why:* Task 9's stack is `lab.compose.yaml` and the old directory→`compose.yaml` inference would have silently driven the app's protected production compose file, with `reload_nginx`'s `check=False` hiding the failure. *Cost if wrong:* one signature rename, before any target module existed.
2. **Ruling:** the debug location is the plan's `{{DEBUG_LOCATION}}` placeholder, not an inlined template line plus a post-render `str.replace`. *Why:* the plan's vocabulary is identical across the four new templates, and the post-render swap silently no-ops if the text drifts. *Cost if wrong:* one template line and one mapping entry per target — and three targets would have copied the fragile shape.
3. **Ruling:** live bring-up and `verify` are run by the controller centrally, in the background, not by each implementer in the foreground. *Why:* the harness foreground timeout was killing long image builds mid-flight, which is what produced the orphaned Docker descriptor. *Cost if wrong:* none — it changed who runs the commands, not what the commands do.
4. **Ruling:** the settle timeout was raised from 30 s to 60 s. *Why:* a container recreation takes ~12 s (measured), and 30 s proved flaky right after another recreation. *Cost if wrong:* a slower failure report.
5. **Ruling:** the live domain's state files and rendered configs are the authoritative record, so the test suite must never write them — enforced by a guard test. *Why:* a test run silently rewrote two live state files and a `git clean -fdx` deleted a target's built bundle, state file and rendered config. *Cost if wrong:* none — the guard is test-only.
6. **Ruling:** the directory-name ruling stands — the real directory is the 12-byte spelling, and the 11-byte spelling that this session created by accident is gone. *Why:* two spellings one keystroke apart; the plan and spec now contain zero occurrences of the stale one. *Cost if wrong:* one rename of a string only these two documents define, before any row is written.

---

# Phase 2 — the eServices target's portal

## Ruling — the never-modify rule is amended for the eServices target's presentation

**Ruling:** `eservices-lab/app/server.py` and `eservices-lab/app/Dockerfile` may be
changed **for the portal's presentation and its demo data only**. The *contract* is
frozen and is enforced by new tests (`eservices-lab/app/tests/test_server.py`):

- `GET /health` keeps its body.
- `GET /api/v1/services` stays a JSON list whose entries keep `id`, `name`, `dept`.
- `GET /api/v1/records/<rid>` keeps its 401-without-`X-API-Key` and 404-for-unknown
  behaviour and its record fields, because `GET /api/v1/admin/debug` exposes
  `RECORDS["TEST-0001"]`.
- `GET /api/v1/admin/debug` returns a **byte-identical** payload.
- The §6.6 fictional-identifier conventions are unchanged and extended only in the same style.

**Why:** the eServices target is the asset DriftGuard assesses; a visible stub makes the
evaluation unconvincing. The contract is what the measurement depends on; the
presentation is not. *Cost if wrong:* one app can be reverted; the frozen contract is
pinned by tests, so a contract break is caught rather than shipped.

**Still never modified:** `eservices-lab/lab.py`, `eservices-lab/nginx/*`,
`eservices-lab/docker-compose.yml`, `eservices-lab/backend/**` (the DriftGuard backend),
`eservices-lab/frontend/**` (the DriftGuard scanner dashboard), and everything else on
the original list.

## Findings that shaped this phase

- `eservices-lab/frontend/` is the **DriftGuard scanner dashboard** (dark theme,
  `VITE_API_URL`, calls `/api/targets`), not an eServices portal — and
  `eservices-lab/backend/driftguard/` is the **DriftGuard backend**. Both are later-phase
  deliverables that the test-domain plan treated as read-only artifacts. The eServices
  *target* app is `eservices-lab/app/server.py`.
- The scanner dashboard is dark (`--bg:#080f1a`, teal/blue accents); the civic portal is
  light (cream `#f7f7f3`). The new eServices portal must look like a **citizen-facing
  government site** — distinct from both, since one is the asset and the other is the
  tool scanning it.
- The lab app had **no test suite** before this task. Flask's `app.test_client()` covers
  the whole contract without Docker, so the tests need no containers.

## Progress

- Task 14: plan and spec amended (the amended exception recorded in both documents).
- Task 14: implemented (commit `1ac64a2`) — `demo_data.py` (120 deterministic records, 9
  services across 6 departments, applications, notices, departments, FAQ), a Jinja
  template set, a stylesheet and a little JavaScript; `server.py` amended for
  presentation plus additive routes only; `Dockerfile` copies the assets in; a new
  15-test contract suite.
- Task 14: review verdict **Approved, spec-compliant, no Critical** — the byte-identical
  debug payload, the preserved contract surfaces, the additive routes, the deterministic
  dataset and the file boundaries were all verified. One **Important**: the app's test
  suite needs Flask, which cannot be installed system-wide (PEP 668), and the
  implementer used a hand-made virtualenv — so an examiner had no documented way to run
  the contract pin. Two Minors: the `POST /api/v1/applications` body was not validated
  (an unknown `service_id` silently fell back to the first service), and the application
  reference counter is in-process.
- Task 14: fix wave — (1) `eservices-lab/app/requirements-dev.txt` (Flask pinned to the
  range the image resolves to) plus `eservices-lab/app/README.md` documenting the frozen
  contract, the routes and the exact commands to run the tests, and the same commands
  added to the repository README; (2) `POST /api/v1/applications` now returns **400**
  for an unknown `service_id` or an empty applicant instead of silently substituting
  the first service, with two new tests. 17 app tests and the domain's 175 tests pass.
- Task 14: live verification by the controller — the rebuilt image serves the portal
  (200, 8.2 kB, full page structure), `domain.py verify` exits 0 with all five
  eServices probes intact, and `/api/v1/admin/debug` is **byte-identical** to the
  pre-change response (291 bytes, compared byte-for-byte against the previous
  `server.py` executed from `git show HEAD~1`). The nine-scan sequence re-run reproduces
  the §6.5 matrix **exactly as before the redesign**, so the portal work did not perturb
  the measurement.
- Task 14: the in-process application-reference counter and the fixed `submitted` date
  are recorded as a known Minor (the portal is a demonstration artefact; the references
  need not survive a restart).

## A real defect found while resetting the domain after the portal work

The controller's `domain.py reset` left Civic's and VAmPI's `port-open` drift **published
while the recorded state said closed** — and the next reset could not repair it.

**Root cause.** The two compose-based targets decided whether to recreate their
containers by *diffing* `previous` against `current` (`if prev_port != curr_port`). The
recorded state is only a record: if it disagrees with reality — a recreate that was
overtaken by another compose operation, or an external `docker compose` run — a diff can
never repair the disagreement. It was the same defect the final whole-branch review had
raised for the eServices wrapper, and that had been fixed there but not here.

**Ruling:** the published-port state is converged **absolutely**, exactly as the eServices
wrapper now does: if the intended state is "port open", recreate with the override; if
the intended state is "port closed" *and the port is actually published*, recreate
without it. Recreating is idempotent, so this costs nothing when nothing needs to
change, and it repairs a divergence instead of trusting the record.

**Also:** the CLI now re-applies when the live state does not settle within the timeout
(`_apply_and_wait`), so a compose operation that is transiently overtaken converges
instead of failing.

With both in place the divergent state was repaired live — the VAmPI reset withdrew the
published port even though the recorded state already said closed — and the domain
verified clean: **17 scenarios OK, 0 mismatches**.
