# SDD ledger — Task 14: eServices target portal

Plan: `docs/superpowers/plans/2026-11-08-test-domain.md` (Task 14, appended after the test-domain phase)
Spec: `docs/superpowers/specs/2026-11-07-test-domain-enhancement-design.md` (§6.6 fictional-data conventions)
BASE: `13e3d4a` (main, after the test-domain phase was merged and pushed)
Branch: `main` (this phase continues on `main`; the worktree was removed when the test-domain phase was finished)

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
