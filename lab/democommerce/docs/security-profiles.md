# Security configuration profiles

The current profile is persisted in `app_settings` and loaded on startup. The researcher
admin UI reads the effective configuration and records every change. The change does not
restart or rewrite application code.

| Profile | Observable behavior |
|---|---|
| `BASELINE` | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, restrictive CSP and Referrer-Policy; CORS allows configured origins only; session cookie is HttpOnly, SameSite=Strict and Secure according to environment |
| `TEST_CHANGE` | Local-only, opt-in; removes CSP and X-Frame-Options, reflects any requesting origin with credentialed CORS, and relaxes cookie HttpOnly/SameSite to Lax |
| `RESTORED` | Restores the secure response headers, configured CORS allowlist and baseline cookie attributes |

`RESTORED` and `BASELINE` use the same secure behavior; they remain separate labels so a
researcher can record the explicit restoration step in the experiment history.

## Environment controls

- `DEMO_CORS_ORIGINS`: comma-separated exact frontend origins; defaults to local Vite
  origins on port 5174.
- `DEMO_SESSION_COOKIE_SECURE`: set to `1` when the browser connects over HTTPS. The local
  HTTP development default is `0`.
- `DEMO_ENABLE_HSTS`: add HSTS only when TLS is correctly terminated and HTTPS is enforced.
- `DEMO_TEST_PROFILES_ENABLED`: must be `1` to apply `TEST_CHANGE`; defaults to disabled.

Do not enable test profiles on a public deployment. The API additionally requires an
administrator session and loopback source for profile changes. The reverse proxy template
has a loopback ACL on profile routes. Confirm both controls before an authorized scan.
After testing, apply `RESTORED`, confirm response headers/cookies/CORS, and record the
change history.

The profile modifies only observable HTTP configuration. The reverse-proxy template uses
a private profile subrequest to apply the selected CSP and frame-header behavior to the
storefront as well as API responses. It does not add exploit code, expose database
internals, or create destructive behavior.
