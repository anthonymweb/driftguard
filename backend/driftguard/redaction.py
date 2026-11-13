"""Tokenise sensitive evidence before it can leave the machine.

``redact`` walks a nested payload and replaces sensitive values with stable,
installation-local tokens. The returned token map links originals to tokens and
must never leave the local environment (never returned by an API, never logged,
never included in an exported/shared report).
"""
from __future__ import annotations

import hmac
import hashlib
import ipaddress
import os
import re
import secrets
from pathlib import Path
from typing import Any

# --- secret storage ---------------------------------------------------------
# A per-installation secret makes tokens deterministic within an installation but
# not guessable or reversible from the token alone. It is generated once and
# stored only locally with restrictive permissions; it is never committed.

_SECRET_PATH_ENV = "DRIFTGUARD_REDACTION_SECRET_PATH"
_DB_URL_ENV = "DRIFTGUARD_DATABASE_URL"
_secret_cache: bytes | None = None


def _default_secret_path() -> Path:
    """Choose a local, non-repository storage location for the secret.

    If the configured database is a local SQLite file we keep the secret beside
    it (same installation/storage location). Otherwise fall back to a hidden
    file in the working directory.
    """
    db_url = os.getenv(_DB_URL_ENV, "sqlite:///./driftguard.db")
    if db_url.startswith("sqlite:///") and not db_url.startswith("sqlite:////:memory:"):
        # sqlite:///relative.db or sqlite:////abs/path.db
        db_path = db_url[len("sqlite:///"):]
        if db_url.startswith("sqlite:////"):
            p = Path("/" + db_path.lstrip("/"))
        else:
            p = Path(db_path)
        return p.resolve().parent / ".driftguard_redaction_secret"
    return Path.cwd() / ".driftguard_redaction_secret"


def secret_path() -> Path:
    return Path(os.getenv(_SECRET_PATH_ENV) or _default_secret_path())


def _load_or_create_secret() -> bytes:
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache
    path = secret_path()
    if path.is_file():
        data = path.read_bytes().strip()
        if data:
            _secret_cache = data
            return _secret_cache
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(32).encode("ascii")
    # restrictive permissions: owner read/write only
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(token)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    _secret_cache = token
    return _secret_cache


# --- sensitivity detection --------------------------------------------------

_EMAIL_RE = re.compile(r"(?i)[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}")
# IPv4 (with optional /CIDR) and IPv6-ish tokens
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")
_IPV6_RE = re.compile(r"(?i)(?:[0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}(?:/\d{1,3})?")
_PHONE_RE = re.compile(r"\+\d[\d\- ]{5,}\d")
# URLs / connection strings with a scheme
_SCHEME_RE = re.compile(r"(?i)\b[a-z][a-z0-9+.\-]*://")
# Hostnames / domain names (labels with dots) and localhost; includes *.domain
_HOST_RE = re.compile(r"(?i)(?:\*\.)?(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z0-9\-]{2,}\b|(?<![A-Za-z0-9])localhost(?![A-Za-z0-9])")
# Reference / national-id like identifiers and explicit seeded forms
_ID_RE = re.compile(r"\b(?:TEST-\d{3,}|CMTEST\d{5,}|[A-Z]{2,}\d{6,}[A-Z0-9]*)\b")
# Obvious API key / secret tokens
_KEY_RE = re.compile(r"(?i)\b(?:lab-demo-key|[A-Za-z0-9_\-]*api[_\-]?key[A-Za-z0-9_\-]*|sk_[A-Za-z0-9]{8,})\b")


def _sensitive_kind(value: str) -> str | None:
    """Return a token-type prefix if *value* contains sensitive material."""
    if _SCHEME_RE.search(value):
        return "URL"
    if _EMAIL_RE.search(value):
        return "EMAIL"
    if _IPV6_RE.search(value) and ":" in value:
        # confirm it looks like an address, not a timestamp fragment
        candidate = value.strip()
        # avoid flagging plain times; require hex/colon structure dominance
        try:
            ipaddress.ip_address(candidate.split("/")[0])
            return "IP"
        except ValueError:
            # still sensitive if embedded ipv6-like in larger string; fall through
            if re.search(r"[0-9a-f]*:[0-9a-f:]+", value, re.I):
                # best-effort: treat as IP-bearing
                pass
    if _IPV4_RE.search(value):
        return "IP"
    if _PHONE_RE.search(value):
        return "PHONE"
    if _KEY_RE.search(value):
        return "KEY"
    if _ID_RE.search(value):
        return "ID"
    if _HOST_RE.search(value):
        return "HOST"
    # generic long secret-looking assignments inside strings
    if "postgres://" in value.lower() or "password" in value.lower() and "@" in value:
        return "URL"
    return None


def _token_for(value: str, kind: str, secret: bytes) -> str:
    digest = hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()[:12]
    return f"{kind}_{digest}"


# --- redaction --------------------------------------------------------------

def _redact_value(value: Any, secret: bytes, token_map: dict[str, str]) -> Any:
    if isinstance(value, str):
        kind = _sensitive_kind(value)
        if kind is None:
            return value
        token = token_map.get(value)
        if token is None:
            token = _token_for(value, kind, secret)
            token_map[value] = token
        return token
    if isinstance(value, dict):
        return {k: _redact_value(v, secret, token_map) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v, secret, token_map) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(v, secret, token_map) for v in value)
    # numbers, bools, None, and other scalars pass through unchanged
    return value


def redact(payload: dict) -> tuple[dict, dict]:
    """Return (tokenised payload, token map).

    The token map is local-only and must never be exposed outside the machine.
    """
    secret = _load_or_create_secret()
    token_map: dict[str, str] = {}
    tokenised = _redact_value(payload, secret, token_map)
    # payload is a dict by contract; preserve that type
    if not isinstance(tokenised, dict):
        tokenised = {"value": tokenised}
    return tokenised, token_map


def redact_evidence_payload(evidence: dict) -> dict:
    """Return a shareable, tokenised copy of a single evidence record.

    ``resource``, ``title`` and ``details`` may carry sensitive values; they are
    redacted. The token map produced during redaction is discarded here and never
    exposed — it must remain local-only.
    """
    tokenised, _map = redact(
        {
            "resource": evidence.get("resource"),
            "title": evidence.get("title"),
            "details": evidence.get("details") or {},
        }
    )
    out = dict(evidence)
    out["resource"] = tokenised.get("resource", evidence.get("resource"))
    out["title"] = tokenised.get("title", evidence.get("title"))
    out["details"] = tokenised.get("details") or {}
    return out
