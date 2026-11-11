# DemoCommerce

**DemoCommerce is the controlled test website that DriftGuard will assess.** It is an
independent project. It contains no scanner or drift detection system.

The store uses fictional products and test accounts. It supports catalogue browsing and
search, customer registration and sign-in, a persistent cart, profile updates, order
history and status, simulated checkout, product and order administration, a local contact
inbox, and researcher-controlled HTTP security profiles. Checkout never connects to a
payment provider or asks for card information.

## Current environment

Development is currently running on Windows 11 Pro, Python 3.15.2, Node.js 26.13.0 and
npm 11.20.0. The backend dependencies install and the current application tests run on
this host. Git and Docker are not installed, so Docker deployment was not exercised.
Ubuntu deployment instructions are provided, but still need verification on Ubuntu.
No target domain or public deployment value has been assumed.

## Local development

Use two terminals from this folder. In terminal one:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m democommerce.cli create-admin researcher@example.com
uvicorn democommerce.main:app --env-file .env --host 127.0.0.1 --port 8001
```

Create the administrator password when prompted. The first API start creates the SQLite
database and seeds eight fictional products. OpenAPI docs are at
`http://127.0.0.1:8001/docs`.

In terminal two:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5174`. The frontend talks to the local API and stores cart,
accounts, orders, contact messages and configuration in SQLite. Product art is generated
with local CSS and icons; the storefront does not fetch images or fonts from a third party.

For a Python shell without a `.env` file, use `DEMO_DATABASE_URL` to choose another
database path. Keep the API bound to loopback during local research. Set
`DEMO_SESSION_COOKIE_SECURE=1` behind HTTPS and configure `DEMO_CORS_ORIGINS` to the exact
store origin outside development.

## Research administrator

The account created by `python -m democommerce.cli create-admin EMAIL` can sign in through
the customer sign-in form. Its account menu opens **Admin workspace**, which includes:

- Product create and edit controls.
- Customer and order records; order statuses can be updated.
- The local contact inbox.
- Current security profile, effective settings and configuration history.
- BASELINE, TEST_CHANGE and RESTORED profile controls.

`TEST_CHANGE` is off unless the server environment sets
`DEMO_TEST_PROFILES_ENABLED=1`. It changes observable response headers, CORS behavior and
session cookie attributes. It is local-only, reversible, and recorded in both profile and
application audit tables. Restore `BASELINE` or `RESTORED` immediately after an experiment.
Never enable `TEST_CHANGE` on a public deployment.

## Project documentation

- [Architecture](docs/architecture.md)
- [Database](docs/database.md)
- [API guide](docs/api.md)
- [Security profiles](docs/security-profiles.md)
- [Researcher guide](docs/researcher-guide.md)
- [Ubuntu and reverse-proxy deployment](docs/ubuntu-deployment.md)
- [Reverse-proxy template](deploy/nginx/demo.conf.template)

Run backend checks from `backend/`:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Build the storefront from `frontend/` with `npm run build`.

## Scope and limitations

This is a controlled research target, not a production commerce service. Password login,
role checks, hashed sessions, input validation, stock updates and simulated orders are
implemented. Real payment, outbound email, shipping integrations, password reset, rate
limiting, formal database migrations, and production deployment verification are not yet
implemented. The UI never claims that a real payment or shipment occurred.
