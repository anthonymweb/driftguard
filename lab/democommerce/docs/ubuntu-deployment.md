# Ubuntu installation and deployment

This guide is provided for the later Ubuntu environment. It has not been run or verified
on Ubuntu yet. Do not use a public hostname until it is supplied and explicitly authorized.

## Local Ubuntu development

From the `democommerce/` project directory:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
python -m democommerce.cli create-admin researcher@example.com
uvicorn democommerce.main:app --env-file .env --host 127.0.0.1 --port 8001
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5174`. Local development keeps the API and Vite server on
loopback. No test hostname, TLS certificate, service or third-party system is contacted.

## Reverse-proxy deployment checklist

1. Use a dedicated Ubuntu host and install supported Python, Node.js, Nginx, Git and
   optionally Docker/Compose using the host's maintained packages.
2. Copy the project to a private deployment directory and create a backend `.env` with a
   production SQLite path on a persistent disk. Set exact `DEMO_CORS_ORIGINS` to the
   supplied HTTPS origin, `DEMO_SESSION_COOKIE_SECURE=1`,
   `DEMO_TEST_PROFILES_ENABLED=0`, and enable HSTS only after HTTPS works.
3. Create the admin with the local CLI. Do not place the password in shell history or a
   source file.
4. Build the frontend and serve its `dist/` directory through Nginx. Run Uvicorn on
   loopback or a private Unix socket; never publish port 8000 to the internet.
5. Obtain a certificate through the organization's approved process. Put its path and the
   supplied hostname into a locally reviewed Nginx configuration; this repository does
   not invent either value.
6. Proxy `/api/` to the private API and enable TLS, strict headers, body size/timeouts and
   request logging. Keep `/api/admin/security-profile` loopback-only as shown in
   `deploy/nginx/demo.conf.template`.
7. Verify BASELINE headers, cookie flags, origin-restricted CORS, customer/order flow,
   database persistence and backup/restore before exposing the hostname.
8. Confirm written authorization and approved scope before DriftGuard scans the site.

Do not deploy `TEST_CHANGE` on the public domain. For remote maintenance, use an SSH
port-forward to the loopback API rather than exposing profile endpoints.

## Docker compatibility

`deploy/compose.yaml` describes an optional container layout with the API private to the
Compose network, a static web/reverse-proxy container and a persistent SQLite volume.
Copy `deploy/.env.example` to `deploy/.env`, supply the authorized hostname and exact
HTTPS origin, place certificate/key files under `deploy/certs/`, create the researcher
administrator in the API container, then start with `docker compose --env-file .env up -d
--build` from `deploy/`. The API has no published host port. Configuration profile routes
are blocked at Nginx except for loopback clients; use a local shell/SSH tunnel for
researcher control. Docker is not available in the current environment, so the Compose
build has not been tested here.
