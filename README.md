# DriftGuard — Controlled Test Domain

A **controlled test domain** for DriftGuard, a drift-detection research project.

Five target applications are stood up behind a controlled nginx host. Each can have
reversible security drift switched on and off, and every switch is recorded in an
authoritative ground-truth log. A later scanner is scored against that log, so the
correct answer for every finding is known in advance.

This repository contains the **test domain only** — the scanner/backend and the UI are
separate deliverables.

---

## The three audited areas

DriftGuard assesses exactly three areas, and nothing else. HTTP headers, CORS, cookies,
HSTS and rate limiting are deliberately **out of scope**.

| Area | Scenario | What the drift does |
|---|---|---|
| **TLS/SSL** | `tls-legacy` | the controlled host accepts TLS 1.0/1.1 |
| | `cert-mismatch` | the served certificate does not match the hostname |
| **Network/Service** | `http-plain` | the application is served over plain HTTP with no redirect |
| | `port-open` | an unexpected legacy admin port is published |
| **API exposure** | `api-debug` | an internal admin/debug endpoint becomes publicly reachable |

Every scenario is switchable in both directions and is verified by a live probe before
it is recorded.

## The five targets

| Target | App | HTTPS | HTTP | Scenarios |
|---|---|---|---|---|
| `eservices-lab` | Flask portal (pre-existing lab) | 8443 | 8080 | all five (incl. `cert-mismatch`) |
| `democommerc` | FastAPI + React store | 8444 | 8082 | `tls-legacy`, `http-plain`, `api-debug` |
| `civic-services-portal` | Flask API + React portal | 8445 | 8083 | `tls-legacy`, `port-open`, `api-debug` |
| `juice-shop` | OWASP Juice Shop (unmodified image) | 8446 | 8085 | `tls-legacy`, `http-plain`, `api-debug` |
| `vampi` | OWASP VAmPI (unmodified image) | 8447 | 8086 | `tls-legacy`, `port-open`, `api-debug` |

Seventeen scenarios in total: five on `eservices-lab` and three on each other target.

## Quick start

```bash
./bootstrap.sh          # pull images, build the front-end bundles, start the domain, verify it
```

`bootstrap.sh` is idempotent — re-run it any time to repair or refresh the environment.

Then drive the drift:

```bash
python3 domain.py status                  # the five targets and their seventeen scenarios
python3 domain.py on eservices-lab tls-legacy    # switch a scenario on
python3 domain.py off eservices-lab tls-legacy   # and back off again
python3 domain.py verify                  # probe every target against its recorded state
python3 domain.py truth                   # the ground-truth classification matrix
```

To run the full nine-scan sequence that produces every classification state in every
audit area:

```bash
python3 sequence.py
```

### Requirements

- Linux with **Docker** and **Docker Compose v2**
- **Python 3.12+** (standard library only — there is nothing to `pip install`)
- **Node.js 18+** with npm, to build the two front-end bundles

## The CLI

```
python3 domain.py up [target] | down [target] | status [--json]
python3 domain.py on <target> <scenario> | off <target> <scenario>
python3 domain.py reset [target] | mark <label> | truth [--json] | verify [--json]
```

`on`/`off` wait until the target's live behaviour actually matches the request, so a
`mark` taken straight afterwards records the truth. `verify` compares the live probes
against the recorded state and exits non-zero on any disagreement.

## The ground-truth contract

- **Classification** — exactly six labels: `BASELINE`, `NEW`, `PERSISTENT`, `FIXED`,
  `RECURRING`, `NO DRIFT`. The rules are frozen and do not change.
- **`finding_key`** — `<target>/<area>/<scenario>`, where `<area>` is exactly one of
  `TLS`, `Network`, `API`. The key is reconstructible from the row's own columns, so
  the scanner's findings and the ground truth join on it without a mapping table.
- **Ground-truth log** — `ground_truth.csv`, nine columns, one row per scenario per
  scan.
- **Down targets** — a target that is not running is recorded as `None` and excluded
  from scoring. It is never silently counted as `NO DRIFT`.

## Safety

- **Everything binds to `127.0.0.1`.** Never expose this lab to the internet. The
  drift scenarios deliberately open a debug dump, an admin API and a legacy admin port.
- **All data is fictional.** The seeded identifiers (`TEST-0001`, `CMTEST00000001`,
  `+256700000001`, `10.20.0.0/24`, `lab-demo-key`, `*.eservices.test`) are the one
  known set the later redaction check looks for. No real hostname, real IP or personal
  data is seeded anywhere.
- The Juice Shop and VAmPI images are used unmodified.

## Repository layout

```
domain/              the controller package
  model.py           frozen Target/Scenario types, the area labels, probe results
  classify.py        the five-state classifier
  state.py           scan + ground-truth storage, the nine-column schema
  probes.py          the live network probes
  render.py          nginx template substitution
  certs.py           certificate generation
  compose.py         docker compose wrappers
  config.py          the target registry (single source of truth)
  cli.py             the argparse CLI
  targets/           one module per target
domain.py            CLI entry point
sequence.py          the unattended nine-scan sequence
targets/             compose + nginx assets for the Juice Shop and VAmPI hosts
tests/               the unittest suite
docs/domain.md       the operator guide — read this next
docs/development-log.md  how the domain was built, and the decisions taken
```

## Documentation

- **[`docs/domain.md`](docs/domain.md)** — the operator guide: addresses, scenarios,
  bringing the domain up and down, the nine-scan sequence, reading the ground truth.
- **[`docs/development-log.md`](docs/development-log.md)** — the build log: the
  rulings taken, the defects found by running the domain live, and how they were fixed.
