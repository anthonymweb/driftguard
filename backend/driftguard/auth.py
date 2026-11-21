"""Authentication and role-based authorisation.

The safety rules require every assessment to be attributable. When the API is
reachable beyond a single researcher's machine, that attribution has to come
from an authenticated caller rather than from whoever can reach the port.

Roles are ordered — ``viewer`` < ``operator`` < ``admin`` — so a role implies
every action below it. With no secret configured the service stays open for
local research (this project's documented default), but *demanding* auth
without supplying a secret fails fast rather than silently running open.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request
from jose import JWTError, jwt

#: Ordered so a role implies every role beneath it.
ROLES: dict[str, int] = {"viewer": 0, "operator": 1, "admin": 2}


@dataclass(frozen=True)
class Principal:
    """The caller behind a request."""

    username: str
    role: str

    def has(self, minimum: str) -> bool:
        """Does this principal hold *minimum* or better?"""
        return ROLES.get(self.role, -1) >= ROLES[minimum]


def auth_enabled() -> bool:
    """Is authentication enforced?"""
    return bool(os.getenv("DRIFTGUARD_AUTH_SECRET"))


def auth_required() -> bool:
    """Was this installation told to refuse to run unauthenticated?"""
    return os.getenv("DRIFTGUARD_AUTH_REQUIRED", "").strip().lower() in {"1", "true", "yes", "on"}


def validate_auth_config() -> None:
    """Fail fast rather than run an open service that was asked to be locked down."""
    if auth_required() and not auth_enabled():
        raise RuntimeError(
            "DRIFTGUARD_AUTH_REQUIRED is set but DRIFTGUARD_AUTH_SECRET is missing; "
            "refusing to start without authentication"
        )


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (salted per hash; never stored in clear text)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_token(principal: Principal) -> tuple[str, int]:
    """Sign a bearer token; returns ``(token, lifetime_seconds)``."""
    ttl_minutes = int(os.getenv("DRIFTGUARD_TOKEN_TTL_MINUTES", "60"))
    now = datetime.now(timezone.utc)
    claims = {
        "sub": principal.username,
        "role": principal.role,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    token = jwt.encode(claims, os.environ["DRIFTGUARD_AUTH_SECRET"], algorithm="HS256")
    return token, ttl_minutes * 60


def optional_principal(request: Request) -> Principal | None:
    """Resolve the caller, or ``None`` when there is no usable credential.

    ``None`` is distinct from a *refused* credential: the user-bootstrap path
    needs to know "nobody said who they are" so it can decide whether the
    installation has any users at all.
    """
    if not auth_enabled():
        return Principal(username="local-research", role="admin")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        claims = jwt.decode(
            header[7:].strip(),
            os.environ["DRIFTGUARD_AUTH_SECRET"],
            algorithms=["HS256"],
        )
    except JWTError:
        return None
    role = claims.get("role")
    return Principal(
        username=str(claims.get("sub", "")),
        role=role if role in ROLES else "viewer",
    )


def current_principal(request: Request) -> Principal:
    """The authenticated caller; raises 401 when there is none."""
    principal = optional_principal(request)
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_role(minimum: str):
    """Dependency factory: the caller must hold *minimum* or better (else 403)."""

    def dependency(request: Request) -> Principal:
        principal = current_principal(request)
        if not principal.has(minimum):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"role '{principal.role}' may not perform this action; "
                    f"'{minimum}' required"
                ),
            )
        return principal

    return dependency
