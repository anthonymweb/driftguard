"""The DriftGuard check catalogue.

Each check consumes normalised observations and yields zero or more evidence items.
The evidence fingerprint is the frozen key ``<target>/<area>/<check-id>`` used by the
evaluation to join scanner findings to ground truth. Checks are declarative records so
the engine can iterate them without knowing what they detect.
"""

from __future__ import annotations

import re
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


#: Certificate fields that name the host: the common name and the subject
#: alternative names. Other fields (issuers, policies, chain of trust) must not
#: be searched for the hostname.
_CERT_NAME_KEYS = ("cert_commonName", "cert_commonName_wo_SNI")
_CERT_SAN_KEYS = ("cert_subjectAltName", "cert_san", "cert_subjectAlternativeName")


def _cert_names(cert: dict[str, Any]) -> set[str]:
    """The host names the certificate claims, from its CN and its SANs."""
    names: set[str] = set()
    for key in _CERT_NAME_KEYS:
        value = cert.get(key)
        if value:
            names.add(str(value).strip().lower())
    for key in _CERT_SAN_KEYS:
        value = cert.get(key)
        if value:
            for part in re.split(r"[,\s]+", str(value)):
                part = part.strip()
                if not part:
                    continue
                # testssl writes SANs as "DNS:host" / "IP Address:1.2.3.4" in
                # some sections and as bare hosts in others.
                part = re.sub(r"^(?i:dns|ip address|ip|email|uri):", "", part)
                if part:
                    names.add(part.strip().lower())
    return names


def _host_matches(hostname: str, name: str) -> bool:
    """Does *hostname* match the certificate name *name*?

    Exact match, or a single-label wildcard (``*.example.test`` matches
    ``www.example.test`` but not ``a.b.example.test``). A plain substring
    test would call a certificate valid whenever the hostname happened to
    appear inside some unrelated field.
    """
    host = (hostname or "").strip().lower().rstrip(".")
    candidate = (name or "").strip().lower().rstrip(".")
    if not host or not candidate:
        return False
    if host == candidate:
        return True
    if candidate.startswith("*."):
        suffix = candidate[1:]  # ".example.test"
        return host.endswith(suffix) and host.count(".") == suffix.count(".")
    return False


def _cert_matches(hostname: str, cert: dict[str, Any]) -> bool:
    host = (hostname or "").strip().lower()
    if not host or not cert:
        return False
    return any(_host_matches(host, name) for name in _cert_names(cert))


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
    httpx = observations.get("httpx_plain") or {}
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
    url = str(httpx.get("final_url") or context.get("plain_url") or context.get("url") or target)
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
    """Is this status code an *exposure*?

    A path that answers with the content is exposed. A redirect (3xx) to a
    sign-in page is not: nothing was disclosed. An authentication or
    not-found answer is not either.
    """
    try:
        code = int(status)
    except (TypeError, ValueError):
        return False
    if code in (401, 403, 404):
        return False
    return 200 <= code < 300


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
