"""Civic Services Portal target wrapper."""
import json
from collections.abc import Callable
from pathlib import Path

from .. import ROOT, certs, compose, render
from ..model import ProbeResult, Scenario, Target
from ..probes import probe_api_path, probe_port_open, probe_tls_legacy

NAME = "civic-services-portal"
COMPOSE_FILE: Path = ROOT / "civic-services-portal" / "deploy" / "compose.yaml"
OVERRIDE_PATH: Path = ROOT / "civic-services-portal" / "deploy" / "expose.override.yaml"
TEMPLATE_PATH: Path = ROOT / "civic-services-portal" / "deploy" / "nginx" / "site.conf.tpl"
CONFIG_PATH: Path = ROOT / "civic-services-portal" / "deploy" / "nginx" / "conf.d" / "default.conf"
STATE_PATH: Path = ROOT / "civic-services-portal" / "deploy" / "state.json"
CERT_DIR: Path = ROOT / "certs"

TARGET = Target(
    name=NAME,
    base_url="https://127.0.0.1:8445",
    http_base_url="http://127.0.0.1:8083",
    approved_ports=(8445, 8083),
    drift_ports=(8084,),
    scope=("tls", "network", "http_api"),
    scenarios=(
        Scenario(name="tls-legacy", area="TLS",
                 expected_finding="Legacy TLS 1.0/1.1 accepted"),
        Scenario(name="port-open", area="Network",
                 expected_finding="Unexpected API port 8084 exposed"),
        Scenario(name="api-debug", area="API",
                 expected_finding="Debug endpoint /api/v1/admin/debug publicly reachable"),
    ),
)

_HTTP_BLOCK = "    return 301 https://$host:8445$request_uri;"
_DEBUG_BASELINE = "    location = /api/v1/admin/debug { return 403; }"
_DEBUG_DRIFT = (
    "    location = /api/v1/admin/debug { "
    "proxy_pass http://api:5000/api/v1/admin/debug; "
    "proxy_set_header Host $host; "
    "proxy_set_header X-Real-IP $remote_addr; "
    "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; "
    "proxy_set_header X-Forwarded-Proto $scheme; }"
)


def _write_config(content: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(content)


def read_state() -> dict[str, bool]:
    data = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    return {s.name: bool(data.get(s.name)) for s in TARGET.scenarios}


def nginx_config(state: dict[str, bool]) -> str:
    template = TEMPLATE_PATH.read_text()
    if state.get("tls-legacy"):
        ssl_protocols = "TLSv1 TLSv1.1 TLSv1.2 TLSv1.3"
        ssl_ciphers = "DEFAULT:@SECLEVEL=0"
    else:
        ssl_protocols = "TLSv1.2 TLSv1.3"
        ssl_ciphers = "HIGH:!aNULL:!MD5"
    debug_location = _DEBUG_DRIFT if state.get("api-debug") else _DEBUG_BASELINE
    mapping = {
        "HTTP_BLOCK": _HTTP_BLOCK,
        "DEBUG_LOCATION": debug_location,
        "CERT": "localhost",
        "SSL_PROTOCOLS": ssl_protocols,
        "SSL_CIPHERS": ssl_ciphers,
    }
    return render.render(template, mapping)


def apply(previous: dict[str, bool], current: dict[str, bool]) -> None:
    _write_config(nginx_config(current))
    prev_port = bool(previous.get("port-open"))
    curr_port = bool(current.get("port-open"))
    if prev_port != curr_port:
        compose.recreate(COMPOSE_FILE, OVERRIDE_PATH if curr_port else None)
    compose.reload_nginx(COMPOSE_FILE)


def up() -> None:
    certs.ensure_certs(CERT_DIR)
    compose.up(COMPOSE_FILE)
    apply({}, read_state())


def down() -> None:
    compose.down(COMPOSE_FILE)


def probes() -> dict[str, Callable[[], ProbeResult]]:
    host = "127.0.0.1"
    return {
        "tls-legacy": lambda: probe_tls_legacy(host, 8445),
        "port-open": lambda: probe_port_open(host, 8084),
        "api-debug": lambda: probe_api_path(host, 8445, "/api/v1/admin/debug", tls=True),
    }
