# eServices target application

The simulated government portal that DriftGuard assesses as its first target. It runs
behind the lab's controlled nginx host (`https://localhost:8443`), which is what
terminates TLS and masks the admin endpoint.

```
app/
  server.py       the Flask application: pages, the JSON API, and the admin debug route
  demo_data.py    the fictional dataset (services, records, applications, notices)
  templates/      the portal's Jinja templates
  static/         the portal's stylesheet and the little bit of JavaScript
  tests/          the contract tests — see "Running the tests" below
```

## What is frozen

The **API contract** of this app is what the measurement depends on, and it must not
drift:

| Route | Guarantee |
|---|---|
| `GET /health` | the body is unchanged |
| `GET /api/v1/services` | a JSON **list** whose entries keep `id`, `name`, `dept` |
| `GET /api/v1/records/<rid>` | 401 without `X-API-Key`, 404 for an unknown id, same record fields |
| `GET /api/v1/admin/debug` | **byte-identical** payload |

`GET /api/v1/admin/debug` is simultaneously the `api-debug` drift surface and the
baseline the later redaction zero-leakage check greps for — which is why its bytes are
pinned by a test rather than merely described.

Everything the app serves is fictional: `TEST-%04d` record references, `CMTEST%08d`
national ids, `+256700000%03d` phone numbers, `10.20.0.0/24` internal addresses,
`*.eservices.test` hostnames and the `lab-demo-key` API key. No real hostname, real IP
address, real organisation, credential or personal data appears anywhere.

## Routes

Pages: `/`, `/services/<id>`, `/records`, `/applications`, `/notices`, `/help`.

API: `/health`, `/api/v1/services`, `/api/v1/services/<id>`, `/api/v1/records/<rid>`,
`/api/v1/admin/debug`, `/api/v1/departments`, `/api/v1/applications`,
`/api/v1/applications/<ref>`, `/api/v1/notices`, and `POST /api/v1/applications`.

## Running the tests

The application needs Flask, and the host Python is PEP 668 "externally managed", so
use a virtualenv:

```bash
python3 -m venv /tmp/esvc-venv
/tmp/esvc-venv/bin/pip install -r eservices-lab/app/requirements-dev.txt
/tmp/esvc-venv/bin/python -m unittest discover -s eservices-lab/app/tests -v
```

The tests use Flask's test client, so they need no containers and no network.

The domain's own suite is separate and needs no dependencies at all:

```bash
python3 -m unittest discover -s tests -v
```
