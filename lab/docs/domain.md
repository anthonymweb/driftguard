# Controlled test domain — operator guide

This repository hosts a **controlled drift-detection test domain** driven by the
`domain.py` CLI. It brings up five intentionally vulnerable/insecure
configurations as reversible scenarios, records ground truth for each scan, and
classifies drift as `NO DRIFT`, `NEW`, `PERSISTENT`, `FIXED`, `RECURRING`, or
`BASELINE` per finding.

All services bind to loopback (`127.0.0.1`) only. **Never expose this lab to the
internet.**

## Targets and addresses

| Target | Base (HTTPS) | HTTP | Approved ports | Drift ports | Scopes |
| --- | --- | --- | --- | --- | --- |
| `eservices-lab` | `https://127.0.0.1:8443` | `http://127.0.0.1:8080` | 8443, 8080 | 8081 | tls, network, http_api |
| `democommerce` | `https://127.0.0.1:8444` | `http://127.0.0.1:8082` | 8444, 8082 | — | tls, network, http_api |
| `civic-services-portal` | `https://127.0.0.1:8445` | `http://127.0.0.1:8083` | 8445, 8083 | 8084 | tls, network, http_api |
| `juice-shop` | `https://127.0.0.1:8446` | `http://127.0.0.1:8085` | 8446, 8085 | — | tls, network, http_api |
| `vampi` | `https://127.0.0.1:8447` | `http://127.0.0.1:8086` | 8447, 8086 | 8087 | tls, network, http_api |

`democommerce` and `juice-shop` do not publish a drift port; `eservices-lab`
uses 8081 and `civic-services-portal`/`vampi` publish 8084/8087 only when the
`port-open` scenario is enabled.

## Scenarios by area (17 total)

Scenarios are grouped into the three frozen audit areas **TLS/SSL**, **Network/Service**,
and **API**. A target supports only a subset; toggling an unsupported scenario is
a no-op in the sequence driver (the CLI rejects unknown scenarios for a target).

| Target | Scenario | Area | Expected finding (probe observable) |
| --- | --- | --- | --- |
| `eservices-lab` | `tls-legacy` | TLS | Legacy TLS 1.0/1.1 accepted |
| `eservices-lab` | `cert-mismatch` | TLS | Certificate does not match hostname |
| `eservices-lab` | `http-plain` | Network | Application served over plain HTTP, no redirect |
| `eservices-lab` | `port-open` | Network | Unexpected legacy admin service on port 8081 |
| `eservices-lab` | `api-debug` | API | Debug endpoint `/api/v1/admin/debug` publicly reachable |
| `democommerce` | `tls-legacy` | TLS | Legacy TLS 1.0/1.1 accepted |
| `democommerce` | `http-plain` | Network | Application served over plain HTTP, no redirect |
| `democommerce` | `api-debug` | API | Internal security-profile endpoint `/api/internal/security-profile` publicly reachable |
| `civic-services-portal` | `tls-legacy` | TLS | Legacy TLS 1.0/1.1 accepted |
| `civic-services-portal` | `port-open` | Network | Unexpected API port 8084 exposed |
| `civic-services-portal` | `api-debug` | API | Debug endpoint `/api/v1/admin/debug` publicly reachable |
| `juice-shop` | `tls-legacy` | TLS | Legacy TLS 1.0/1.1 accepted |
| `juice-shop` | `http-plain` | Network | Application served over plain HTTP, no redirect |
| `juice-shop` | `api-debug` | API | Admin API endpoint `/rest/admin/application-configuration` publicly reachable |
| `vampi` | `tls-legacy` | TLS | Legacy TLS 1.0/1.1 accepted |
| `vampi` | `port-open` | Network | Unexpected API port 8087 exposed |
| `vampi` | `api-debug` | API | Debug endpoint `/users/v1/_debug` publicly reachable |

## Bringing the domain up and down

```bash
python3 domain.py up [target]      # bring up every target, or one
python3 domain.py down [target]    # stop every target, or one
python3 domain.py status [--json]  # current scenario state (or DOWN)
```

`up` with no target starts all five registered targets. After bringing targets
up, wait for them to be ready before scanning (the wrappers perform readiness
checks where required, e.g. Juice Shop and VAmPI).

## Verify before trusting a scan

Always confirm live behaviour matches recorded state before taking a scan you
intend to score:

```bash
python3 domain.py verify [--json]
```

`verify` compares each scenario's live probe observation against the recorded
state and exits **1** on any mismatch (with details on stderr/stdout). A target
that is DOWN is reported as `unknown`/expected `None` and does not fail the run
by itself. Do not trust `mark`/`truth` results taken while `verify` fails.

## Toggling scenarios and resetting

```bash
python3 domain.py on <target> <scenario>
python3 domain.py off <target> <scenario>
python3 domain.py reset [target]   # turn every scenario off
```

`on`/`off` apply the change and wait (up to 60 s) until live behaviour matches;
a timeout is reported on stderr and the command exits 1. `reset` returns every
scenario on the named target (or all targets) to off.

## The nine-scan sequence

`sequence.py` drives the canonical classification sequence (spec §6.5) through
the frozen CLI in subprocesses. Run it from the repository root:

```bash
python3 sequence.py
```

It locates `domain.py` relative to its own directory and runs with the invoking
Python interpreter from the repository root. The script resets the domain to a
known baseline, records **`S0`** with everything off (so the first observed
drift is classified `NEW`, not `BASELINE`), then applies S1–S9 and records a
mark after each step, finally printing `python3 domain.py truth`. It is safe to
run more than once and fails loudly (non-zero) if any CLI step fails.

Scenario toggles per scan:

| Scan | Toggles (applied to targets that support the scenario) |
| --- | --- |
| S1 | all off |
| S2 | `tls-legacy` on, `cert-mismatch` on |
| S3 | +`http-plain` on |
| S4 | `tls-legacy` off, `port-open` on |
| S5 | `tls-legacy` on |
| S6 | +`api-debug` on |
| S7 | `http-plain` off, `port-open` off, `api-debug` off |
| S8 | `http-plain` on, `api-debug` on |
| S9 | `port-open` on |

## Recording scans and reading truth

```bash
python3 domain.py mark <label>  # record one scan row for every registered target
python3 domain.py truth [--json]
```

`mark` records the current state of **every** registered target. A target that is
DOWN is recorded as `None` for that scan and is **excluded from scoring** (it is
never classified `NO DRIFT` merely for being down; it counts as absent while
classifying neighbouring scans).

`truth` prints the ground-truth matrix: `target → scenario → [label per scan in
order]`. Read each row left-to-right across the scan labels to see how that
finding evolved (e.g. `NO DRIFT, NEW, PERSISTENT, FIXED, RECURRING`).

## `finding_key` contract

Each scenario is identified by the stable key

```
<target>/<area>/<scenario>
```

where `area` is one of the three audit areas: `TLS`, `Network`, or `API` (for
example `eservices-lab/TLS/tls-legacy`, `juice-shop/API/api-debug`). Ground-truth
rows and scenario definitions are constrained to these areas so finding keys
never leave `{TLS, Network, API}`.

## Fictional-data conventions

The domain uses **fully fictional** data and identities (e.g. test identifiers
such as `TEST-0001` and synthetic records/keys). It is a stand-in for testing
and safe redaction checks — no real persons, organisations, or production
secrets are represented. Baseline self-signed certificates are generated
locally under `certs/` for the lab hosts.

## Build and observable notes

- **DemoCommerce and Civic Services Portal front-end bundles are built, not
  copied.** Their deployable assets are produced by the target build pipelines
  in `democommerce/` and `civic-services-portal/` (built artifacts under their
  respective `dist/`/deploy outputs) rather than vendored as static copies.
  Copying the prebuilt bundle from the main checkout is the accepted fallback
  when npm is unavailable.
- **Juice Shop `api-debug` observable:** the admin API path used for the
  `api-debug` scenario is `GET /rest/admin/application-configuration` (served on
  the controlled host at `https://127.0.0.1:8446`). Baseline returns 403 via the
  nginx block; enabling `api-debug` proxies the `/rest/admin/` prefix to the
  application so the endpoint becomes publicly reachable. This is the verified
  observable for that scenario.
