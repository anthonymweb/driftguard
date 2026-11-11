"""Live network probes shared by every target module.

The mapping is fixed by the plan: an observation is `present`/`absent` only when
the target was reached and answered in a way that decides the question; anything
that makes the observation meaningless — unreachable, refused TLS, unexpected
status — is `unknown`. The exception is probe_port_open, where a refused connect
*is* the observation (that is what makes DOWN detection work: a target is DOWN
exactly when probe_port_open returns "absent").
"""
import http.client
import ipaddress
import socket
import ssl
import warnings
from collections.abc import Sequence
from pathlib import Path

from .model import ProbeResult

TIMEOUT = 5.0  # seconds; no probe blocks longer than this on any socket


def probe_tls_legacy(host: str, port: int) -> ProbeResult:
    """present when a TLS 1.0 or 1.1 handshake completes; absent when a reachable
    target declines the legacy protocols; unknown when it cannot be reached."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # ssl.TLSVersion.TLSv1 is deprecated
        rejected = False
        for version in (ssl.TLSVersion.TLSv1, ssl.TLSVersion.TLSv1_1):
            try:
                raw = socket.create_connection((host, port), timeout=TIMEOUT)
            except OSError:
                return "unknown"  # nothing to talk to: no observation
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                try:
                    context.set_ciphers("ALL:@SECLEVEL=0")  # as lab.py p_tls
                except ssl.SSLError:
                    pass  # fall back to the default cipher list
                context.minimum_version = context.maximum_version = version
                with raw, context.wrap_socket(raw, server_hostname=host):
                    return "present"
            except ValueError:
                continue  # this build cannot offer the protocol at all
            except OSError:
                rejected = True  # reachable, but the handshake did not complete
        return "absent" if rejected else "unknown"


def probe_cert_mismatch(host: str, port: int, cafiles: Sequence[Path]) -> ProbeResult:
    """present when the served certificate fails hostname verification while
    chaining to the supplied CAs — verify code 62 / "hostname", the failure lab.py's
    two-CA p_cert isolates. Any other verification error (e.g. unknown CA when only
    good.crt is trusted) or an unreachable target is unknown; a handshake that
    verifies cleanly is absent."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # check_hostname on, CERT_REQUIRED
    for cafile in cafiles:
        context.load_verify_locations(cafile=str(cafile))
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT) as raw:
            with context.wrap_socket(raw, server_hostname=_verify_name(host)):
                return "absent"  # verified against the supplied CAs: no mismatch
    except ssl.SSLCertVerificationError as error:
        if error.verify_code == 62 or "hostname" in str(error).lower():
            return "present"
        return "unknown"  # e.g. code 18 self-signed: the CA is wrong, not the name
    except (ssl.SSLError, OSError):
        return "unknown"


def probe_http_plain(host: str, port: int) -> ProbeResult:
    """present when plain HTTP answers 2xx; a redirect (3xx) is absent — the
    remediated configuration sends the client to HTTPS. Other statuses and
    connection failures are unknown."""
    connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
    try:
        connection.request("GET", "/")
        status = connection.getresponse().status
    except (OSError, http.client.HTTPException):
        return "unknown"
    finally:
        connection.close()  # HTTPConnection has no context-manager protocol
    if 200 <= status < 300:
        return "present"
    if 300 <= status < 400:
        return "absent"
    return "unknown"  # 4xx/5xx say nothing about a redirect


def probe_port_open(host: str, port: int) -> ProbeResult:
    """present when a TCP connect completes; a refused or failed connect is
    absent — refusal *is* the observation here, which is what makes this the
    DOWN test (a target is DOWN exactly when this probe returns "absent")."""
    try:
        with socket.create_connection((host, port), timeout=TIMEOUT):
            return "present"
    except OSError:
        return "absent"


def probe_api_path(host: str, port: int, path: str, *, tls: bool = True) -> ProbeResult:
    """present for 2xx; 401/403/404 are absent (the endpoint is masked); a
    connection failure, 5xx or any other status is unknown."""
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # the lab serves self-signed certs
        connection: http.client.HTTPConnection = http.client.HTTPSConnection(
            host, port, timeout=TIMEOUT, context=context)
    else:
        connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT)
    try:
        connection.request("GET", path)
        status = connection.getresponse().status
    except (OSError, http.client.HTTPException):
        return "unknown"
    finally:
        connection.close()  # HTTPConnection has no context-manager protocol
    if 200 <= status < 300:
        return "present"
    if status in (401, 403, 404):
        return "absent"
    return "unknown"  # 5xx and everything else: no conclusion


def _verify_name(host: str) -> str:
    """Name to verify the served certificate against.

    lab.py connects to 127.0.0.1 but verifies as "localhost" (its good.crt is
    issued for DNS:localhost). An IP server_hostname would surface a mismatch as
    verify code 64 "IP address mismatch", not the hostname failure (code 62) the
    cert-mismatch scenario isolates; DNS hosts are verified as themselves.
    """
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    return "localhost"
