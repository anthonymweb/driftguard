# Researcher guide

## Local setup

1. Install Python and Node.js on a local Ubuntu or Windows development machine.
2. Create the backend virtual environment, install requirements, and copy
   `backend/.env.example` to `backend/.env`.
3. Create the research administrator using `python -m democommerce.cli create-admin
   researcher@example.com`.
4. Start FastAPI on loopback, then start Vite on loopback. See the root README for exact
   commands.
5. Confirm `/health`, `/docs`, the catalogue and a new account are working before using
   the app as a test target.

## Repeatable configuration experiment

1. Record the current profile as `BASELINE` and capture the public site/API response
   headers, cookie attributes and CORS behavior.
2. Enable `DEMO_TEST_PROFILES_ENABLED=1` only in the isolated local environment, restart
   the API, then sign in as the research administrator.
3. Select `TEST_CHANGE` in **Admin workspace → Configuration** and record the profile
   history event.
4. Assess only the explicitly authorized host and ports using DriftGuard. Do not run the
   intentionally changed profile on a public target.
5. Select `RESTORED` after assessment and independently check that the original headers,
   CORS allowlist and cookie attributes are back.
6. Export/retain DriftGuard evidence separately. DemoCommerce stores its own profile
   history and does not attempt to determine DriftGuard classifications.

The admin area is not a scanner. It is only a controlled configuration switchboard and
business administration interface.
