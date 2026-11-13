"""Assessment engine: gather observations for an approved scope, record evidence, classify drift.

Refuses scans that are not explicitly, attributably authorised. Only approved ports and
enabled modules are exercised, with bounded politeness between tool invocations.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import database, drift, models
from . import checks, tools

TOOL_DELAY_SECONDS = 0.2
PLAIN_HTTP_PORTS = (80, 8080, 8000, 3000)


class ScanRefused(Exception):
    """A scan request is not permitted for the given target."""


def _has_authorization_record(target: models.Target) -> bool:
    return bool(
        target.authorized_by
        and target.authorized_at
        and target.authorization_basis
    )


def _explicit_port(address: str) -> int | None:
    """Return the port explicitly carried by the address, or None if implicit."""
    addr = (address or "").strip()
    if "://" in addr:
        parsed = urlsplit(addr)
    else:
        parsed = urlsplit(f"//{addr}")
    try:
        port = parsed.port
    except ValueError:
        return None
    return int(port) if port is not None else None


def _approved_port_set(approved_ports: list[int] | None) -> list[int]:
    return [int(p) for p in (approved_ports or [])]


def ensure_scannable(target: models.Target) -> None:
    reasons: list[str] = []
    if target.status != "active":
        reasons.append("target must be active")
    if target.authorization_status != "authorized":
        reasons.append("target must be explicitly authorized")
    if not target.approved_scope:
        reasons.append("target has no approved assessment scope")
    if not _has_authorization_record(target):
        reasons.append(
            "target must carry an attributable authorisation record (who, when, on what basis)"
        )
    explicit = _explicit_port(target.address)
    approved = _approved_port_set(getattr(target, "approved_ports", None))
    if explicit is not None and explicit not in approved:
        reasons.append(
            f"target address port {explicit} is not in approved_ports; the engine may only assess approved ports"
        )
    if reasons:
        raise ScanRefused("; ".join(reasons))


def derive_host(address: str) -> str:
    """Derive the network hostname from a bare hostname, host:port, or URL."""
    addr = (address or "").strip()
    if "://" in addr:
        parsed = urlsplit(addr)
        host = parsed.hostname
        if host:
            return host.rstrip(".")
    # host or host:port (possibly bracketed IPv6)
    parsed = urlsplit(f"//{addr}")
    host = parsed.hostname
    if host:
        return host.rstrip(".")
    return addr.split("/")[0].split(":")[0].strip()


def derive_tls_port(address: str, approved_ports: list[int]) -> int:
    """Pick the TLS port from the approved set.

    The explicit port in the address takes precedence but must already be approved
    (enforced by ensure_scannable). Otherwise prefer 443/8443, then the first approved port.
    """
    ports = _approved_port_set(approved_ports)
    explicit = _explicit_port(address)
    if explicit is not None:
        if explicit not in ports:
            raise ScanRefused(
                f"target address port {explicit} is not in approved_ports; the engine may only assess approved ports"
            )
        return explicit
    for preferred in (443, 8443):
        if preferred in ports:
            return preferred
    if ports:
        return ports[0]
    raise ScanRefused("cannot derive a TLS port: no approved ports")


def derive_http_url(address: str, approved_ports: list[int] | None = None) -> str:
    """Derive the base (secure/API) URL for HTTP probing, using only approved ports.

    An explicit address port must be approved. A URL with no explicit port is resolved to an
    approved port for its scheme (or a reasonable approved fallback) so the returned URL
    always identifies an approved port.
    """
    addr = (address or "").strip()
    ports = _approved_port_set(approved_ports)
    host = derive_host(addr)

    if "://" in addr:
        parsed = urlsplit(addr)
        scheme = parsed.scheme or "https"
        explicit = parsed.port
        if explicit is not None:
            if int(explicit) not in ports:
                raise ScanRefused(
                    f"target address port {int(explicit)} is not in approved_ports; the engine may only assess approved ports"
                )
            return addr.rstrip("/")
        # No explicit port: choose an approved port for this scheme.
        if scheme == "http":
            for p in (*PLAIN_HTTP_PORTS, 443, 8443):
                if p in ports:
                    return f"http://{host}:{p}"
        else:
            for p in (443, 8443, *PLAIN_HTTP_PORTS):
                if p in ports:
                    return f"https://{host}:{p}"
        if ports:
            return f"{scheme}://{host}:{ports[0]}"
        raise ScanRefused("cannot derive an HTTP URL: no approved ports")

    # host or host:port
    parsed = urlsplit(f"//{addr}")
    explicit = parsed.port
    if explicit is not None:
        if int(explicit) not in ports:
            raise ScanRefused(
                f"target address port {int(explicit)} is not in approved_ports; the engine may only assess approved ports"
            )
        return f"http://{host}:{int(explicit)}"
    for web in PLAIN_HTTP_PORTS:
        if web in ports:
            return f"http://{host}:{web}"
    for secure in (443, 8443):
        if secure in ports:
            return f"https://{host}:{secure}"
    if ports:
        return f"http://{host}:{ports[0]}"
    raise ScanRefused("cannot derive an HTTP URL: no approved ports")


def derive_plain_http_url(address: str, approved_ports: list[int] | None = None) -> str | None:
    """Return the approved plain-HTTP endpoint URL, or None if no plain port is approved."""
    ports = _approved_port_set(approved_ports)
    host = derive_host(address)
    for p in PLAIN_HTTP_PORTS:
        if p in ports:
            return f"http://{host}:{p}"
    return None


def _completed_scans_before(db: Session, target_id: int, scan_id: int) -> list[models.Scan]:
    """Prior completed scans for the target, oldest to newest, excluding this scan."""
    stmt = (
        select(models.Scan)
        .where(
            models.Scan.target_id == target_id,
            models.Scan.id != scan_id,
            models.Scan.status.in_(["completed", "completed_with_errors"]),
        )
        .order_by(models.Scan.id.asc())
    )
    return list(db.scalars(stmt))


def _fingerprints_for_scan(db: Session, scan_id: int) -> set[str]:
    stmt = select(models.Evidence.fingerprint).where(models.Evidence.scan_id == scan_id)
    return {fp for (fp,) in db.execute(stmt).all()}


def _record_drift(db: Session, target: models.Target, scan: models.Scan) -> None:
    history = _completed_scans_before(db, target.id, scan.id)
    if not history:
        # No previous scan: store evidence but emit no drift events.
        return
    previous_scan = history[-1]
    earlier_scans = history[:-1]
    current = _fingerprints_for_scan(db, scan.id)
    previous = _fingerprints_for_scan(db, previous_scan.id)
    earlier = [_fingerprints_for_scan(db, s.id) for s in earlier_scans]
    classified = drift.classify(current, previous, earlier)
    for fingerprint, label in sorted(classified.items()):
        db.add(
            models.DriftEvent(
                target_id=target.id,
                scan_id=scan.id,
                evidence_fingerprint=fingerprint,
                classification=label,
            )
        )


def assess_target(db: Session, target: models.Target, scan: models.Scan | None = None) -> models.Scan:
    """Run the assessment for an authorised target and persist evidence and drift.

    Raises ScanRefused if the target is not active, authorised, scoped, and attributable.
    Tool failures are recorded on the scan and do not abort the whole assessment, but a
    scan with no successful tool observations is marked failed rather than clean.
    """
    ensure_scannable(target)

    if scan is None:
        scan = models.Scan(target_id=target.id, status="queued")
        db.add(scan)
        db.commit()
        db.refresh(scan)

    scan.status = "running"
    scan.error = None
    db.commit()

    host = derive_host(target.address)
    scope = set(target.approved_scope or [])
    ports = _approved_port_set(target.approved_ports)
    base_url = derive_http_url(target.address, ports)
    plain_url = derive_plain_http_url(target.address, ports)
    context = {
        "target": target.name,
        "hostname": host,
        "approved_ports": ports,
        "url": base_url,
        "plain_url": plain_url,
    }

    observations: dict = {}
    errors: list[str] = []
    attempted = 0

    def _delay() -> None:
        if attempted > 0:
            time.sleep(TOOL_DELAY_SECONDS)

    if "network" in scope:
        _delay()
        attempted += 1
        try:
            observations["nmap"] = tools.run_nmap(host, ports)
        except Exception as exc:  # ToolError or unexpected failure
            errors.append(f"nmap: {exc}")

    if "tls" in scope:
        _delay()
        attempted += 1
        try:
            tls_port = derive_tls_port(target.address, ports)
            observations["testssl"] = tools.run_testssl(host, tls_port)
        except Exception as exc:
            errors.append(f"testssl: {exc}")

    if "http_api" in scope:
        # Secure/base probe for API checks (and discovery target).
        _delay()
        attempted += 1
        try:
            observations["httpx"] = tools.run_httpx(base_url)
        except Exception as exc:
            errors.append(f"httpx: {exc}")

        # Plain-HTTP probe for the http-plain check, only when a plain approved port exists.
        if plain_url:
            _delay()
            attempted += 1
            try:
                observations["httpx_plain"] = tools.run_httpx(plain_url)
            except Exception as exc:
                errors.append(f"httpx_plain: {exc}")

        if getattr(target, "discovery_enabled", False):
            wordlist = getattr(target, "discovery_wordlist", None)
            if wordlist:
                _delay()
                attempted += 1
                try:
                    observations["gobuster"] = tools.run_gobuster(base_url, wordlist)
                except Exception as exc:
                    errors.append(f"gobuster: {exc}")

    # Run catalogue and store evidence (fingerprint unique per scan).
    for check in checks.CATALOGUE:
        try:
            items = check.run(observations, context) or []
        except Exception as exc:
            errors.append(f"check {check.id}: {exc}")
            continue
        for item in items:
            db.add(
                models.Evidence(
                    scan_id=scan.id,
                    fingerprint=item["fingerprint"],
                    category=item["category"],
                    title=item["title"],
                    severity=item["severity"],
                    resource=item["resource"],
                    details=item.get("details") or {},
                )
            )

    # Classify drift against previous scan (emits no events if there is no prior scan).
    _record_drift(db, target, scan)

    scan.completed_at = datetime.now(timezone.utc)
    usable = bool(observations)
    if errors:
        scan.error = "; ".join(errors)
        # A run that produced no usable observations is not a clean scan.
        scan.status = "completed_with_errors" if usable else "failed"
    else:
        if not usable and attempted > 0:
            scan.status = "failed"
            scan.error = "assessment produced no observations"
        else:
            scan.status = "completed"
            scan.error = None

    db.commit()
    db.refresh(scan)
    return scan


def run_scan_in_background(scan_id: int, session_factory=None) -> None:
    """Background entry point: open a fresh session and run the queued scan.

    *session_factory* lets the caller supply the session factory (the API
    resolves it as a dependency, so a test can point the assessment at its own
    database).
    """
    db = (session_factory or database.SessionLocal)()
    try:
        scan = db.get(models.Scan, scan_id)
        if scan is None:
            return
        target = db.get(models.Target, scan.target_id)
        if target is None:
            scan.status = "failed"
            scan.error = "target not found"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            return
        try:
            assess_target(db, target, scan=scan)
        except ScanRefused as exc:
            scan.status = "failed"
            scan.error = f"refused: {exc}"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:  # pragma: no cover - defensive
            scan.status = "failed"
            scan.error = str(exc)
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
