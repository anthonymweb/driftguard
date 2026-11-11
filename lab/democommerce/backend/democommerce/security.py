"""Password, cookie session and reversible HTTP profile handling."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from starlette.responses import Response

from . import models

SESSION_COOKIE = "democommerce_session"
SESSION_TTL = timedelta(hours=12)
HASH_ROUNDS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, HASH_ROUNDS)
    return f"pbkdf2_sha256${HASH_ROUNDS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds_text, salt_hex, expected_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds_text))
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def new_session(db, user: models.User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(models.SessionToken(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + SESSION_TTL,
    ))
    return token


def current_profile(request) -> str:
    return getattr(request.app.state, "security_profile", "BASELINE")


def profile_settings(profile: str) -> dict:
    secure = os.getenv("DEMO_SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    origins = [origin.strip() for origin in os.getenv(
        "DEMO_CORS_ORIGINS", "http://127.0.0.1:5174,http://localhost:5174"
    ).split(",") if origin.strip()]
    base = {
        "headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
        },
        "cors": origins,
        "cors_wildcard": False,
        "cookie_secure": secure,
        "cookie_httponly": True,
        "cookie_samesite": "strict",
    }
    if profile == "TEST_CHANGE":
        # Reversible, non-destructive checks of observable HTTP configuration.
        base["headers"].pop("X-Frame-Options")
        base["headers"].pop("Content-Security-Policy")
        base["cors_wildcard"] = True
        base["cookie_httponly"] = False
        base["cookie_samesite"] = "lax"
    return base


def set_session_cookie(response: Response, token: str, profile: str) -> None:
    config = profile_settings(profile)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=config["cookie_httponly"],
        secure=config["cookie_secure"],
        samesite=config["cookie_samesite"],
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
