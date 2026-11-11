"""The DriftGuard check catalogue.

Each check consumes normalised observations and yields zero or more evidence items.
The evidence fingerprint is the frozen key ``<target>/<area>/<check-id>`` used by the
evaluation to join scanner findings to ground truth. Checks are declarative records so
the engine can iterate them without knowing what they detect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

Observation = dict[str, Any]
Context = dict[str, Any]
EvidenceItem = dict[str, Any]
CheckFn = Callable[[Observation, Context], list[EvidenceItem]]


@dataclass(frozen=True)
class Check:
    id: str
    area: str
    severity: str
    title: str
    run: CheckFn


def _fp(target: str, area: str, check_id: str) -> str:
    return f"{target}/{area}/{check_id}"


def _ev(
    target: str,
    area: str,
    check_id: str,
    title: str,
    severity: str,
    resource: str,
    details: dict[str, Any],
) -> EvidenceItem:
    return {
        "fingerprint": _fp(target, area, check_id),
        "category": area,
        "title": title,
        "severity": severity,
        "resource": resource,
        "details": details,
    }


def _run_tls_legacy(observations: Observation, context: Context) -> list[EvidenceItem]:
    target = str(context.get("target", ""))
    testssl = observations.get("testssl") or {}
    protocols = testssl.get("protocols") or {}
    offered: dict[str, bool] = {}
    for name in ("TLS1", "TLS1_1", "TLSv1", "TLSv1.0", "TLSv1_0", "TLSv1.1", "TLSv1_1"):
        if protocols.get(name) is True:
            offered[name] = True
    # also accept generic keys containing 1.0/1.1
    for name, val in protocols.items():
        low = str(name).lower().replace("-", ".").replace("_", ".")
        if val is True and ("1.0" in low or "1.1" in low) and "1.2" not in low and "1.3" not in low:
            offered[str(name)] = True
    if not offered:
        return []
    return [
        _ev(
            target,
            "TLS",
            "tls-legacy",
            "Legacy TLS protocol accepted",
            "high",
            str(context.get("hostname") or target),
            {"offered_protocols": offered, **offered},
        )
    ]


def _cert_matches(hostname: str, cert: dict[str, Any]) -> bool:
    host = (hostname or "").strip().lower()
    if not host or not cert:
        return False
    for key, value in cert.items():
        if value is None:
            continue
        text = str(value).lower()
        # direct match or present as SAN/CN token
        if host in text:
            return True
    return False


def _run_cert_mismatch(observations: Observation, context: Context) -> list[EvidenceItem]:
    target = str(context.get("target", ""))
    hostname = str(context.get("hostname") or target)
    testssl = observations.get("testssl") or {}
    cert = testssl.get("cert") or {}
    if not cert:
        return []
    if _cert_matches(hostname, cert):
        return []
    return [
        _ev(
            target,
            "TLS",
            "cert-mismatch",
            "Certificate hostname mismatch",
            "medium",
            hostname,
            {"hostname": hostname, "cert": cert},
        )
    ]


def _run_port_open(observations: Observation, context: Context) -> list[EvidenceItem]:
    target = str(context.get("target", ""))
    approved = set(int(p) for p in (context.get("approved_ports") or []))
    nmap = observations.get("nmap") or {}
    open_ports = nmap.get("open_ports") or []
    items: list[EvidenceItem] = []
    for entry in open_ports:
        try:
            port = int(entry.get("port"))
        except (TypeError, ValueError):
            continue
        if port in approved:
            continue
        items.append(
            _ev(
                target,
                "Network",
                "port-open",
                "Unexpected open port",
                "high",
                str(port),
                {"port": port, "service": entry.get("service"), "version": entry.get("version")},
            )
        )
    return items


def _run_http_plain(observations: Observation, context: Context) -> list[EvidenceItem]:
    target = str(context.get("target", ""))
    httpx = observations.get("httpx") or {}
    if not httpx:
        return []
    scheme = str(httpx.get("scheme") or "")
    location = httpx.get("location")
    loc = str(location).lower() if location else ""
    # plain HTTP that does not redirect to HTTPS
    if scheme != "http":
        return []
    if loc.startswith("https://"):
        return []
    url = str(context.get("url") or httpx.get("final_url") or target)
    return [
        _ev(
            target,
            "Network",
            "http-plain",
            "Plain HTTP without redirect to HTTPS",
            "medium",
            url,
            {"status_code": httpx.get("status_code"), "location": location, "scheme": scheme},
        )
    ]


def _is_exposed_status(status: Any) -> bool:
    try:
        code = int(status)
    except (TypeError, ValueError):
        return False
    if code in (401, 403, 404):
        return False
    return 200 <= code < 400


def _run_api_debug(observations: Observation, context: Context) -> list[EvidenceItem]:
    target = str(context.get("target", ""))
    found_lists = []
    gobuster = observations.get("gobuster") or {}
    if gobuster.get("found"):
        found_lists.extend(gobuster.get("found") or [])
    probe = observations.get("probe") or {}
    if probe.get("found"):
        found_lists.extend(probe.get("found") or [])
    items: list[EvidenceItem] = []
    for entry in found_lists:
        if not isinstance(entry, dict):
            continue
        status = entry.get("status")
        if not _is_exposed_status(status):
            continue
        path = str(entry.get("path") or entry.get("resource") or "")
        if not path:
            continue
        items.append(
            _ev(
                target,
                "API",
                "api-debug",
                "Sensitive or administrative path exposed",
                "high",
                path,
                {"path": path, "status": int(status), "size": entry.get("size")},
            )
        )
    return items


tls_legacy = Check("tls-legacy", "TLS", "high", "Legacy TLS protocol accepted", _run_tls_legacy)
cert_mismatch = Check("cert-mismatch", "TLS", "medium", "Certificate hostname mismatch", _run_cert_mismatch)
port_open = Check("port-open", "Network", "high", "Unexpected open port", _run_port_open)
http_plain = Check("http-plain", "Network", "medium", "Plain HTTP without redirect to HTTPS", _run_http_plain)
api_debug = Check("api-debug", "API", "high", "Sensitive or administrative path exposed", _run_api_debug)

CATALOGUE: tuple[Check, ...] = (
    tls_legacy,
    cert_mismatch,
    port_open,
    http_plain,
    api_debug,
)
