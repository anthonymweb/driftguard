"""DemoCommerce lab stack target wrapper."""
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from .. import ROOT, certs, compose, render, state
from ..model import ProbeResult, Scenario, Target
from ..probes import probe_api_path, probe_http_plain, probe_tls_legacy

NAME = "democommerce"
COMPOSE_FILE: Path = ROOT / "democommerce" / "deploy" / "lab.compose.yaml"
TEMPLATE_PATH: Path = ROOT / "democommerce" / "deploy" / "nginx" / "lab.conf.tpl"
CONFIG_PATH: Path = ROOT / "democommerce" / "deploy" / "nginx" / "conf.d" / "default.conf"
STATE_PATH: Path = ROOT / "democommerce" / "deploy" / "lab.state.json"
CERT_DIR: Path = ROOT / "certs"

TARGET = Target(
    name=NAME,
    base_url="https://127.0.0.1:8444",
    http_base_url="http://127.0.0.1:8082",
    approved_ports=(8444, 8082),
    drift_ports=(),
    scope=("tls", "network", "http_api"),
    scenarios=(
        Scenario(name="tls-legacy", area="TLS",
                 expected_finding="Legacy TLS 1.0/1.1 accepted"),
        Scenario(name="http-plain", area="Network",
                 expected_finding="Application served over plain HTTP, no redirect"),
        Scenario(name="api-debug", area="API",
                 expected_finding="Internal security-profile endpoint publicly reachable"),
    ),
)

_HTTP_BASELINE = "    return 301 https://$host:8444$request_uri;"
_HTTP_PLAIN = "    location / { try_files $uri $uri/ /index.html; }"
_DEBUG_BASELINE = "    location = /api/internal/security-profile { return 404; }"
_DEBUG_DRIFT = (
    "    location = /api/internal/security-profile { "
    "proxy_pass http://app/api/internal/security-profile; "
    "proxy_set_header Host $host; "
    "proxy_set_header X-Real-IP $remote_addr; "
    "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; "
    "proxy_set_header X-Forwarded-Proto $scheme; }"
)


def _write_config(content: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix=CONFIG_PATH.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, CONFIG_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def read_state() -> dict[str, bool]:
    data = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    return {s.name: bool(data.get(s.name)) for s in TARGET.scenarios}


def nginx_config(state: dict[str, bool]) -> str:
    template = TEMPLATE_PATH.read_text()
    http_block = _HTTP_PLAIN if state.get("http-plain") else _HTTP_BASELINE
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
    compose.validate_nginx_config(COMPOSE_FILE)
    compose.reload_nginx(COMPOSE_FILE)
    state.write_state(STATE_PATH, current)


def up() -> None:
    certs.ensure_certs(CERT_DIR)
    compose.up(COMPOSE_FILE)
    apply({}, read_state())


def down() -> None:
    compose.down(COMPOSE_FILE)


def probes() -> dict[str, Callable[[], ProbeResult]]:
    host = "127.0.0.1"
    return {
        "tls-legacy": lambda: probe_tls_legacy(host, 8444),
        "http-plain": lambda: probe_http_plain(host, 8082),
        "api-debug": lambda: probe_api_path(host, 8444, "/api/internal/security-profile", tls=True),
    }
