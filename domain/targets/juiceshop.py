"""OWASP Juice Shop target wrapper."""
import json
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .. import ROOT, certs, compose, render, state
from ..model import ProbeResult, Scenario, Target
from ..probes import probe_api_path, probe_http_plain, probe_tls_legacy

NAME = "juice-shop"
COMPOSE_FILE: Path = ROOT / "targets" / "juiceshop" / "compose.yaml"
TEMPLATE_PATH: Path = ROOT / "targets" / "juiceshop" / "nginx" / "site.conf.tpl"
CONFIG_PATH: Path = ROOT / "targets" / "juiceshop" / "nginx" / "conf.d" / "default.conf"
STATE_PATH: Path = ROOT / "targets" / "juiceshop" / "state.json"
CERT_DIR: Path = ROOT / "certs"

TARGET = Target(
    name=NAME,
    base_url="https://127.0.0.1:8446",
    http_base_url="http://127.0.0.1:8085",
    approved_ports=(8446, 8085),
    drift_ports=(),
    scope=("tls", "network", "http_api"),
    scenarios=(
        Scenario(name="tls-legacy", area="TLS",
                 expected_finding="Legacy TLS 1.0/1.1 accepted"),
        Scenario(name="http-plain", area="Network",
                 expected_finding="Application served over plain HTTP, no redirect"),
        Scenario(name="api-debug", area="API",
                 expected_finding="Admin API endpoint publicly reachable"),
    ),
)

_HTTP_BLOCK = "    return 301 https://$host:8446$request_uri;"
_HTTP_PLAIN = (
    "    location / {\n"
    "        proxy_pass http://juice-shop:3000;\n"
    "        proxy_http_version 1.1;\n"
    "        proxy_set_header Host $host;\n"
    "        proxy_set_header X-Real-IP $remote_addr;\n"
    "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    "    }"
)
_DEBUG_BASELINE = "    location ^~ /rest/admin/ { return 403; }"
_DEBUG_DRIFT = (
    "    location ^~ /rest/admin/ {\n"
    "        proxy_pass http://juice-shop:3000;\n"
    "        proxy_http_version 1.1;\n"
    "        proxy_set_header Host $host;\n"
    "        proxy_set_header X-Real-IP $remote_addr;\n"
    "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    "    }"
)


def _write_config(content: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(content)


def read_state() -> dict[str, bool]:
    data = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    return {s.name: bool(data.get(s.name)) for s in TARGET.scenarios}


def nginx_config(state: dict[str, bool]) -> str:
    template = TEMPLATE_PATH.read_text()
    http_block = _HTTP_PLAIN if state.get("http-plain") else _HTTP_BLOCK
    if state.get("tls-legacy"):
        ssl_protocols = "TLSv1 TLSv1.1 TLSv1.2 TLSv1.3"
        ssl_ciphers = "DEFAULT:@SECLEVEL=0"
    else:
        ssl_protocols = "TLSv1.2 TLSv1.3"
        ssl_ciphers = "HIGH:!aNULL:!MD5"
    debug_location = _DEBUG_DRIFT if state.get("api-debug") else _DEBUG_BASELINE
    mapping = {
        "HTTP_BLOCK": http_block,
        "DEBUG_LOCATION": debug_location,
        "CERT": "localhost",
        "SSL_PROTOCOLS": ssl_protocols,
        "SSL_CIPHERS": ssl_ciphers,
    }
    return render.render(template, mapping)


def apply(previous: dict[str, bool], current: dict[str, bool]) -> None:
    _write_config(nginx_config(current))
    compose.reload_nginx(COMPOSE_FILE)
    state.write_state(STATE_PATH, current)


def _wait_for_ready(timeout: int = 180) -> None:
    """Poll GET https://127.0.0.1:8446/ until status < 500 or timeout."""
    deadline = time.monotonic() + timeout
    url = "https://127.0.0.1:8446/"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                if resp.status < 500:
                    return
                last_error = RuntimeError(f"HTTP {resp.status}")
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return
            last_error = exc
        except Exception as exc:  # noqa: BLE001 - readiness polling
            last_error = exc
        time.sleep(2)
    raise RuntimeError(
        f"juice-shop did not become ready at {url} within {timeout}s: {last_error}"
    )


def up() -> None:
    certs.ensure_certs(CERT_DIR)
    compose.up(COMPOSE_FILE)
    _wait_for_ready()
    apply({}, read_state())


def down() -> None:
    compose.down(COMPOSE_FILE)


def probes() -> dict[str, Callable[[], ProbeResult]]:
    host = "127.0.0.1"
    return {
        "tls-legacy": lambda: probe_tls_legacy(host, 8446),
        "http-plain": lambda: probe_http_plain(host, 8085),
        "api-debug": lambda: probe_api_path(
            host, 8446, "/rest/admin/application-configuration", tls=True),
    }
