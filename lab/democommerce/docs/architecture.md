# Architecture

DemoCommerce is an independent target web application. DriftGuard is a separate system
that can observe the public site and the documented API. The stack is React 19 with Vite,
FastAPI, SQLAlchemy and SQLite. The API owns business rules and persistence; the browser
does not seed or invent product, customer, order or configuration data.

```text
Browser
  ├── React/Vite storefront (development: 127.0.0.1:5174)
  └── FastAPI API (development: 127.0.0.1:8001)
        └── SQLAlchemy → SQLite

Optional deployment:
Internet → TLS reverse proxy → static storefront + private API service → SQLite volume
```

The `frontend/` folder contains customer pages and the admin workspace. `backend/`
contains the catalogue, auth, cart, order, profile, researcher configuration and audit
routes. `deploy/` contains the reverse-proxy template. No test domain is hardcoded.

## Request boundaries

- Public routes expose active product information and accept validated contact requests.
- Customer routes require an active session and scope order/cart/profile queries to that
  user.
- Admin routes require the `admin` role. Admin accounts are created from a local CLI;
  customers cannot choose or update their own role.
- Research profile routes also require an admin session and a loopback client address.
  The production reverse proxy denies those routes to non-local clients as a second
  boundary.
- Session values are random, stored as SHA-256 digests, expire after 12 hours, and are
  delivered in HttpOnly, SameSite=Strict cookies in BASELINE/RESTORED.

## Main data flows

1. Store startup creates the initial relational schema and inserts only the fictional
   catalogue if it is absent.
2. Customer registration/login sets a server-managed cookie session.
3. Cart changes validate product activity and stock. Checkout creates a simulated order,
   snapshots product names/prices, decrements stock and clears the cart in one database
   transaction. No payment details are accepted.
4. Admin mutations and configuration changes append audit events.
5. A researcher profile is loaded from SQLite at startup and applied by middleware to API
   responses and CORS preflight. Profile changes are immediately visible and logged.

## Security configuration

HTTP profile behavior lives in `backend/democommerce/security.py` and
`middleware.py`. Normal application and database behavior do not change when a profile is
selected. Environment variables define the database, allowed browser origins, cookie
transport, HSTS and whether the local test profile is enabled.

The site does not claim production readiness. In the deployment template, Nginx asks the
private API for the active profile before serving each public/static or API response. It
then applies/removes the matching response headers across the whole site, while the app
middleware handles API CORS and cookie behavior. The reverse-proxy ACL keeps researcher
controls local.
