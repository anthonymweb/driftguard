from starlette.datastructures import MutableHeaders

from .security import profile_settings


class SecurityProfileMiddleware:
    """Applies observable headers/CORS from the active reversible profile."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        state = scope.get("app").state if scope.get("app") else None
        profile = getattr(state, "security_profile", "BASELINE")
        config = profile_settings(profile)
        headers_in = dict(scope.get("headers", []))
        origin = headers_in.get(b"origin", b"").decode("latin1")
        if scope["method"] == "OPTIONS" and headers_in.get(b"access-control-request-method"):
            allowed = config["cors_wildcard"] or origin in config["cors"]
            if allowed:
                response_headers = [
                    (b"access-control-allow-methods", b"GET, POST, PATCH, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"content-type"),
                    (b"access-control-max-age", b"300"),
                    (b"vary", b"Origin"),
                ]
                response_headers.append((b"access-control-allow-origin", origin.encode("latin1")))
                response_headers.append((b"access-control-allow-credentials", b"true"))
                await Response(status_code=204, headers={k.decode(): v.decode() for k, v in response_headers})(scope, receive, send)
                return
        async def send_with_profile(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in config["headers"].items():
                    headers.setdefault(name, value)
                headers["X-Active-Profile"] = profile
                if os_hsts_enabled():
                    headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
                if origin and (config["cors_wildcard"] or origin in config["cors"]):
                    headers["Access-Control-Allow-Origin"] = origin
                    headers["Access-Control-Allow-Credentials"] = "true"
                    headers.append("Vary", "Origin")
            await send(message)
        await self.app(scope, receive, send_with_profile)


def os_hsts_enabled():
    import os
    return os.getenv("DEMO_ENABLE_HSTS", "0").lower() in {"1", "true", "yes"}
