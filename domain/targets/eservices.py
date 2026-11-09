"""eServices-lab target wrapper.

Shells out to the existing ``eservices-lab/lab.py`` for lifecycle and state
changes, and reads ``eservices-lab/state.json`` for state. ``lab.py`` owns its
nginx template, so :func:`nginx_config` returns ``None``. This module must not
import or modify ``lab.py``.
"""
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from .. import ROOT
from ..model import ProbeResult, Scenario, Target
from ..probes import (probe_api_path, probe_cert_mismatch, probe_http_plain,
                      probe_port_open, probe_tls_legacy)

NAME = "eservices-lab"
LAB_PY: Path = ROOT / "eservices-lab" / "lab.py"
STATE_PATH: Path = ROOT / "eservices-lab" / "state.json"
CERTS: Path = ROOT / "eservices-lab" / "certs"

TARGET = Target(
    name=NAME,
    base_url="https://127.0.0.1:8443",
    http_base_url="http://127.0.0.1:8080",
    approved_ports=(8443, 8080),
    drift_ports=(8081,),
    scope=("tls", "network", "http_api"),
    scenarios=(
        Scenario(name="tls-legacy", area="TLS",
                 expected_finding="Legacy TLS 1.0/1.1 accepted"),
        Scenario(name="cert-mismatch", area="TLS",
                 expected_finding="Certificate does not match hostname"),
        Scenario(name="http-plain", area="Network",
                 expected_finding="Application served over plain HTTP, no redirect"),
        Scenario(name="port-open", area="Network",
                 expected_finding="Unexpected legacy admin service on port 8081"),
        Scenario(name="api-debug", area="API",
                 expected_finding="Debug endpoint /api/v1/admin/debug publicly reachable"),
    ),
)


def _lab(*args: str) -> None:
    subprocess.run(["python3", str(LAB_PY), *args], check=True)


def up() -> None:
    _lab("up")


def down() -> None:
    _lab("down")


def read_state() -> dict[str, bool]:
    """Scenario states from STATE_PATH; a missing file means all False."""
    data = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    return {s.name: bool(data.get(s.name)) for s in TARGET.scenarios}


def apply(previous: dict[str, bool], current: dict[str, bool]) -> None:
    for scenario in TARGET.scenarios:
        name = scenario.name
        if current.get(name) != previous.get(name):
            _lab("on" if current.get(name) else "off", name)


def nginx_config(state: dict[str, bool]) -> str | None:
    return None  # lab.py owns the nginx template


def probes() -> dict[str, Callable[[], ProbeResult]]:
    host = "127.0.0.1"
    cafiles = [CERTS / "good.crt", CERTS / "mismatch.crt"]
    return {
        "tls-legacy": lambda: probe_tls_legacy(host, 8443),
        "cert-mismatch": lambda: probe_cert_mismatch(host, 8443, cafiles),
        "http-plain": lambda: probe_http_plain(host, 8080),
        "port-open": lambda: probe_port_open(host, 8081),
        "api-debug": lambda: probe_api_path(host, 8443, "/api/v1/admin/debug", tls=True),
    }
