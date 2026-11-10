"""OWASP VAmPI target wrapper."""
import json
import os
import ssl
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .. import ROOT, certs, compose, render, state
from ..model import ProbeResult, Scenario, Target
from ..probes import probe_api_path, probe_port_open, probe_tls_legacy

NAME = "vampi"
COMPOSE_FILE: Path = ROOT / "targets" / "vampi" / "compose.yaml"
OVERRIDE_PATH: Path = ROOT / "targets" / "vampi" / "expose.override.yaml"
TEMPLATE_PATH: Path = ROOT / "targets" / "vampi" / "nginx" / "site.conf.tpl"
CONFIG_PATH: Path = ROOT / "targets" / "vampi" / "nginx" / "conf.d" / "default.conf"
STATE_PATH: Path = ROOT / "targets" / "vampi" / "state.json"
CERT_DIR: Path = ROOT / "certs"

TARGET = Target(
    name=NAME,
    base_url="https://127.0.0.1:8447",
    http_base_url="http://127.0.0.1:8086",
    approved_ports=(8447, 8086),
    drift_ports=(8087,),
    scope=("tls", "network", "http_api"),
    scenarios=(
        Scenario(
            name="tls-legacy",
            area="TLS",
            expected_finding="Legacy TLS 1.0/1.1 accepted",
        ),
        Scenario(
            name="port-open",
            area="Network",
            expected_finding="Unexpected API port 8087 exposed",
        ),
        Scenario(
            name="api-debug",
            area="API",
            expected_finding="Debug endpoint /users/v1/_debug publicly reachable",
        ),
    ),
)

_HTTP_BLOCK = "    return 301 https://$host:8447$request_uri;"
_DEBUG_BASELINE = "    location = /users/v1/_debug { return 403; }"
_DEBUG_DRIFT = (
    "    location = /users/v1/_debug {\n"
    "        proxy_pass http://vampi/users/v1/_debug;\n"
    "        proxy_http_version 1.1;\n"
    "        proxy_set_header Host $host;\n"
    "        proxy_set_header X-Real-IP $remote_addr;\n"
    "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
    "        proxy_set_header X-Forwarded-Proto $scheme;\n"
    "    }"
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


def nginx_config(state_map: dict[str, bool]) -> str:
    template = TEMPLATE_PATH.read_text()
    if state_map.get("tls-legacy"):
        ssl_protocols = "TLSv1 TLSv1.1 TLSv1.2 TLSv1.3"
        ssl_ciphers = "DEFAULT:@SECLEVEL=0"
    else:
        ssl_protocols = "TLSv1.2 TLSv1.3"
        ssl_ciphers = "HIGH:!aNULL:!MD5"
    debug_location = _DEBUG_DRIFT if state_map.get("api-debug") else _DEBUG_BASELINE
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
    compose.validate_nginx_config(COMPOSE_FILE)
    prev_port = bool(previous.get("port-open"))
    curr_port = bool(current.get("port-open"))
    if prev_port != curr_port:
        compose.recreate(COMPOSE_FILE, OVERRIDE_PATH if curr_port else None)
    compose.reload_nginx(COMPOSE_FILE)
    state.write_state(STATE_PATH, current)


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _init_db() -> None:
    """Call GET /createdb once through the controlled host."""
    url = "https://127.0.0.1:8447/createdb"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, context=_ssl_context(), timeout=30):
            return
    except urllib.error.HTTPError:
        # Any HTTP response means the endpoint was reached.
        return
    except Exception as exc:  # noqa: BLE001 - best-effort init
        raise RuntimeError(f"vampi /createdb initialization failed at {url}: {exc}") from exc


def _wait_for_ready(timeout: int = 180) -> None:
    """Poll GET https://127.0.0.1:8447/ until status < 500 or timeout."""
    deadline = time.monotonic() + timeout
    url = "https://127.0.0.1:8447/"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=_ssl_context(), timeout=10) as resp:
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
        f"vampi did not become ready at {url} within {timeout}s: {last_error}"
    )


def up() -> None:
    certs.ensure_certs(CERT_DIR)
    compose.up(COMPOSE_FILE)
    _init_db()
    _wait_for_ready()
    apply({}, read_state())


def down() -> None:
    compose.down(COMPOSE_FILE)


def probes() -> dict[str, Callable[[], ProbeResult]]:
    host = "127.0.0.1"
    return {
        "tls-legacy": lambda: probe_tls_legacy(host, 8447),
        "port-open": lambda: probe_port_open(host, 8087),
        "api-debug": lambda: probe_api_path(host, 8447, "/users/v1/_debug", tls=True),
    }
