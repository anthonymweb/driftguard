# DriftGuard

A **drift-detection research project**: an engine that scans a set of systems over time,
decides whether what it finds is *new*, *persistent*, *fixed* or *recurring*, and reports
the change.

This repository holds two things:

| | |
|---|---|
| **`backend/`** | the system — the scanning engine and its API |
| **`frontend/`** | the dashboard that presents what the engine found |
| **`lab/`** | a controlled test domain: five target applications whose security drift can be switched on and off, with an authoritative ground-truth log |

The lab is what makes the system measurable. Every finding the engine produces is scored
against a log of what was *actually* true at the moment of the scan, so detection
accuracy and false-positive rate are measured rather than asserted.

## The three audited areas

DriftGuard assesses exactly three areas, and nothing else. HTTP headers, CORS, cookies,
HSTS and rate limiting are deliberately **out of scope**.

| Area | What is assessed |
|---|---|
| **TLS/SSL** | accepted protocol versions and ciphers; certificate/hostname agreement |
| **Network/Service** | which ports are published; whether the application is served in the clear |
| **API exposure** | whether internal or administrative endpoints are publicly reachable |

## The lab

```bash
cd lab
./bootstrap.sh          # pull images → build the front-end bundles → start the domain → verify
```

Five targets stand behind a controlled nginx host, each with reversible drift:

| Target | App | HTTPS | HTTP | Scenarios |
|---|---|---|---|---|
| `eservices-lab` | Flask portal | 8443 | 8080 | `tls-legacy`, `cert-mismatch`, `http-plain`, `port-open`, `api-debug` |
| `democommerc` | FastAPI + React store | 8444 | 8082 | `tls-legacy`, `http-plain`, `api-debug` |
| `civic-services-portal` | Flask API + React portal | 8445 | 8083 | `tls-legacy`, `port-open`, `api-debug` |
| `juice-shop` | OWASP Juice Shop (unmodified) | 8446 | 8085 | `tls-legacy`, `http-plain`, `api-debug` |
| `vampi` | OWASP VAmPI (unmodified) | 8447 | 8086 | `tls-legacy`, `port-open`, `api-debug` |

Seventeen scenarios in total. Driving them:

```bash
python3 domain.py status                  # the targets and their scenarios
python3 domain.py on eservices-lab tls-legacy    # switch a drift on
python3 domain.py off eservices-lab tls-legacy   # and back off again
python3 domain.py verify                  # probe every target against its recorded state
python3 domain.py truth                   # the ground-truth classification matrix
python3 sequence.py                       # the full nine-scan sequence
```

**[`lab/README.md`](lab/README.md)** is the lab's operator guide — addresses, scenarios,
the nine-scan sequence, the ground-truth contract, and how to read `truth`.

## The system

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn driftguard.main:app --host 127.0.0.1 --port 8000
```

The API is the system's interface. It exposes the target registry, the scans it has run,
the evidence each scan produced, the drift classification between scans, and
remediations. The dashboard in `frontend/` consumes it.

**Nothing is scanned that has not been explicitly authorized.** A target must be active,
carry an `authorized` status and have an approved scope before the engine will assess
it; the approved ports come from the lab's own registry, so a port the lab publishes only
under a drift scenario is an *unapproved* port and is reported as one.

### Tools

The engine drives established tools and turns their output into evidence:

| Area | Tool | Detects |
|---|---|---|
| Network/Service | **nmap** | a published port outside the target's approved set |
| TLS/SSL | **testssl.sh** | legacy protocol/cipher acceptance; certificate/hostname disagreement |
| HTTP probing | **httpx** | the application served over plain HTTP with no redirect |
| API exposure | **gobuster** *(optional, off by default)* | a sensitive path answering without authentication |

Gobuster is a content-discovery tool: it finds paths that were never planted, and an
unplanted finding cannot be scored. It therefore runs only when explicitly enabled, and
only findings that map to a planted weakness count towards the metrics — everything else
it reports is informational.

## Safety

- **Everything binds to `127.0.0.1`.** The lab's drift scenarios deliberately open a
  debug dump, an admin API and a legacy admin port. Never expose it to the internet.
- **All data is fictional.** The seeded identifiers (`TEST-0001`, `CMTEST00000001`,
  `+256700000001`, `10.20.0.0/24`, `lab-demo-key`, `*.eservices.test`) are one known set
  that the redaction zero-leakage check looks for. No real hostname, real IP address,
  credential or personal data appears anywhere.

## Documentation

| | |
|---|---|
| [`docs/superpowers/specs/`](docs/superpowers/specs/) | the approved design — the classification rules, the scan sequence, the API contract, the fictional-data conventions |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | the implementation plan, task by task |
| [`docs/development-log.md`](docs/development-log.md) | how it was built: the rulings taken, the defects that only live runs surfaced, and how each was fixed |
| [`lab/docs/domain.md`](lab/docs/domain.md) | the lab's operator guide |

## Licence

MIT — see [LICENSE](LICENSE). The Juice Shop and VAmPI images are third-party artefacts
used unmodified and are not covered by it.
