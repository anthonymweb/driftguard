# SDD ledger — Phase 3: the DriftGuard scanning engine

Plan: `docs/superpowers/plans/2026-11-08-test-domain.md` (Phase 3, Tasks 15–19)
Spec: `docs/superpowers/specs/2026-11-07-test-domain-enhancement-design.md` (§6.4 the `finding_key` contract, §6.6 the API contract and the fictional-data conventions)
Repo: `https://github.com/anthonymweb/driftguard.git` — `backend/` (the system), `frontend/` (the dashboard), `lab/` (the controlled test domain)

## The restructure (2026-11-11)

The backend and the dashboard were living inside `eservices-lab/`, which made the
product look like one of its own fixtures. They moved to the repository root
(`backend/`, `frontend/`) and the controlled test domain became the `lab/` folder. The
lab's paths are all repository-root relative (`domain.ROOT`), so the move was
transparent to its code — the five targets still resolve, and the lab's 179 tests pass
unchanged from their new home.

Two consequences worth remembering:
- The lab's cross-check test that loads the backend's classifier now finds it as a
  **sibling** (`../backend/driftguard/drift.py`); it skips with a clear message if the
  backend is not present, so the lab stays usable on its own.
- The backend's virtualenv was a **Windows** one (`Lib/site-packages/…`) and had never
  run here. A Linux venv now exists at `backend/.venv` and the backend's 10 tests pass.

## Ruling — the engine assesses authorised targets, not only loopback ones

The plan originally said the engine "may only assess a loopback address". That was
wrong, and it was the user's correction that exposed it: **the lab's "bind to
127.0.0.1" rule is a rule about the lab's vulnerable targets, not about the scanner.**
A drift-detection tool that could only assess 127.0.0.1 would be a toy, and the
system must assess real systems.

**Ruling:** the engine assesses **any explicitly authorised target** — a public
domain, a real API, a host, or the loopback lab. What makes that defensible is not the
address but:

1. **Attributable authorisation** — who authorised the assessment, when, on what basis.
   A scan without that record is refused.
2. **Scope-limited assessment** — only the target's approved ports and paths; never a
   range sweep, never an unapproved port, never a directory brute-force unless that
   module is enabled for that specific target.
3. **Politeness** — rate-limited, bounded timeouts.
4. **Redaction before anything leaves the machine** — real evidence carries real
   hostnames and identifiers.

*Cost if wrong:* an engine that refuses legitimate real-world assessments — which would
make the whole system look like a lab toy.

The backend's data model already supported this: `TargetCreate` accepts any hostname or
IP, and `Target` already carried `authorization_status`, `approved_scope` and
`approved_ports`. Only the plan's wording was wrong.

## Progress

- **Task 15 (tool adapters)** — implemented (`026c2db`), reviewed **Approved**, and
  verified live by the controller against the running lab:
  - `nmap -Pn -sV -p <approved ports> -oX -` → found the five published HTTPS ports
    with service and version; the drift port 8081 correctly absent at baseline.
  - `testssl --jsonfile-pretty … -p -S` → protocols `TLS1_2`/`TLS1_3` offered,
    `SSLv3` not offered, certificate parsed (`commonName: localhost`).
  - `httpx <url> --no-verify -v` → `200`, `https`, no redirect.
  - `gobuster dir -u <url> -w <wordlist> -k -q` → parsed paths.
  Review findings fixed: an empty gobuster result is now distinguished from a parse
  failure (recorded no-hit fixture + test), and the httpx fallback no longer masks the
  primary parse failure (both are now reported).
  Environment notes: Debian installs testssl.sh as **`/usr/bin/testssl`** (no `.sh`); the
  `httpx` on `PATH` is the **Python** httpx CLI, not ProjectDiscovery's (which is not
  installed) — the adapter handles both.
- **Task 16 (the check catalogue)** — next.
- **Task 17 (the engine and the scan endpoint)** — next; carries the authorisation
  audit trail and the scope enforcement.
- **Task 18 (registry sync + evaluation harness)** — next.
- **Task 19 (the redaction layer)** — next; the precondition for assessing real systems.

- **Task 16 (the check catalogue)** — implemented (`2f4c639`), reviewed **Approved**. The
  catalogue is data (a frozen `Check` record per weakness) with a uniform
  `run(observations, context) -> list[EvidenceItem]` signature, and every fingerprint is
  `<target>/<area>/<check-id>` — the frozen key, built from the evidence's own fields.
  Review findings fixed: `cert-mismatch` now matches the hostname against the
  certificate's **CN and SANs only**, with exact and single-label-wildcard rules
  (it previously accepted the hostname appearing anywhere in any field, which could
  hide a mismatch), and `api-debug` no longer treats a **3xx redirect** as exposure — a
  redirect to a sign-in page discloses nothing. 57 backend tests pass.
- Remaining known Minors (deferred): `port-open` reports every discovered port when the
  caller supplies no approved list (the engine must always supply it — Task 17's
  contract), and the `api-debug` check also accepts a `probe.found` observation shape
  alongside `gobuster.found` (a forward-compatible extension, not in the frozen
  contract).

- **Task 17 (the engine and the scan endpoint)** — implemented (`606e44c`), reviewed
  **Needs fixes**, and the findings fixed (`9ddafd2`, `a7cb082`).
  - The review's **Important**: the approved-port boundary was bypassable — the port in
    the target's *address* was preferred over `approved_ports`, so
    `https://example.test:9999` with `approved_ports: [443]` would have had 9999
    scanned. Now an explicit address port outside the approved set makes the target
    **not scannable**, and both derivations select only from the approved set.
  - The controller's **Important**: the `http-plain` check could never fire — the engine
    probed HTTP once, at the *secure* URL, and the check reports only a plain-HTTP
    response. The scenario was undetectable and the check was dead. The engine now
    derives a plain-HTTP URL from the approved ports and probes it into its own
    observation (`httpx_plain`), while `api-debug` keeps reading the secure probe.
  - The review's **Minor**: a tool that ran but produced nothing usable counted as
    succeeded; the outcome now turns on whether observations were actually produced.
  - The controller's correction: the assessment's session factory is now injected as a
    FastAPI dependency, so the background assessment uses the same database as the
    request (the API test could not otherwise be pointed at a test database).
  - The API test that encoded the *old* authorisation contract (a target may claim to be
    authorised without saying who authorised it) was updated to the new contract.
  - **Verified live by the controller**, with the real tools and no mocks: with the lab's
    `tls-legacy` drift on, a scan produced exactly one evidence row,
    `eservices-lab/TLS/tls-legacy` ("Legacy TLS protocol accepted"); with `http-plain`
    on, exactly one row, `eservices-lab/Network/http-plain`; at baseline, **zero** rows.
    A scan of a target whose address port (9999) was outside `approved_ports` was
    refused with **422**: *"Scan refused: target address port 9999 is not in
    approved_ports; the engine may only assess approved ports"*.
  - 86 backend tests pass.

- **Task 18 (the registry sync and the evaluation harness)** — implemented (`4b10793`),
  reviewed **Approved**, and the two Important findings fixed:
  - the sync's default repository root was one level too high (`parents[3]` → `/mnt/data`),
    so it looked for the lab outside the repository;
  - the sync registered targets but never committed them, so they vanished when the
    session closed;
  - the authorisation record was **restamped** on every re-sync — a fresh sync is not a
    fresh authorisation — so the timestamp is now preserved unless the caller passes one
    explicitly;
  - the lab's `domain` package no longer stays installed in `sys.modules` after the
    sync (displaced modules are restored), so a long-lived API process is not left
    resolving `domain` to the lab's package;
  - the evaluator gained the per-target roll-up and now creates the schema when the
    database is fresh.
  - **Verified live**: the lab's five targets were synced; three real scans of
    `eservices-lab` (baseline, `tls-legacy` on, reverted) were evaluated:
    **detection accuracy 1.0, false-positive rate 0.0** (2 detections, 0 misses,
    0 false positives across 26 absent cells).
  - Known limitation (deferred): the engine's scan joins to the ground truth by **label**,
    so re-running the lab's sequence without clearing its scan history leaves duplicate
    labels, and the join becomes ambiguous. The ground truth was cleared before the
    evaluation above.

- **Task 19 (the redaction layer)** — implemented (`6dd421f`), reviewed pending; 104 backend
  tests pass. Hostnames, IPv4/IPv6 (with CIDR), URLs and connection strings (tokenised
  whole), emails, phone numbers, id/reference numbers and API keys are tokenised;
  tokens are HMAC-SHA256 over a per-installation secret stored locally at mode 0600, so
  they are stable across scans and not reversible from the token alone. The map is
  returned in memory only, never by an API endpoint; the shareable boundary is
  `GET /api/scans/{id}/evidence/redacted`.
  - **Verified live**: the eServices debug payload redacted to `KEY_…`, `URL_…`, `IP_…`,
    `ID_…`, `PHONE_…` tokens, and **no** seeded identifier survived anywhere in it.
  - Known gap to close for real targets: a person's **name** (the `name` field) is not
    currently treated as sensitive, because the lab's identifier set does not include
    one. Real targets will need it.

## Focus shift (2026-11-13)

The user asked to concentrate on the DriftGuard system rather than the test domain. The
lab is complete and stable (179 tests, live-verified, the nine-scan matrix reproduced);
it is now the **fixture** the system is measured against. The remaining system work is
the dashboard (`frontend/`, written before the engine existed, so it does not yet show
real findings, the drift classification, the authorisation record or the evaluation
numbers) and the last polish items.
