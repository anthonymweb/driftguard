"""Tool adapters: invoke one external tool and return normalised observations.

Never a shell string, always explicit argv, bounded timeout, and failures raise
rather than silently producing empty observations.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

DEFAULT_TIMEOUT = 120


class ToolError(RuntimeError):
    """A tool invocation failed, was missing, timed out, or produced bad output."""


def _which(name: str) -> str | None:
    return shutil.which(name)


def _resolve_binary(*names: str, env: str | None = None) -> str:
    if env:
        override = os.environ.get(env)
        if override:
            return override
    for name in names:
        path = _which(name)
        if path:
            return path
    raise ToolError(f"required binary not found (tried: {', '.join(names)})")


def _run(cmd: Sequence[str], timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"command timed out after {timeout}s: {cmd[0]}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise ToolError(
            f"command failed with exit code {proc.returncode}: {cmd[0]}: {detail}"
        )
    return proc


# ----------------------------- nmap ----------------------------- #


def parse_nmap(xml_text: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ToolError(f"unparseable nmap output: {exc}") from exc

    open_ports: list[dict[str, Any]] = []
    for port_el in root.findall(".//host/ports/port"):
        state_el = port_el.find("state")
        state = (state_el.get("state") if state_el is not None else "") or ""
        if state != "open":
            continue
        portid = port_el.get("portid") or "0"
        try:
            port = int(portid)
        except ValueError as exc:
            raise ToolError(f"unparseable nmap port id: {portid!r}") from exc
        service_el = port_el.find("service")
        service = (service_el.get("name") if service_el is not None else "") or ""
        product = (service_el.get("product") if service_el is not None else "") or ""
        ver = (service_el.get("version") if service_el is not None else "") or ""
        version = " ".join(p for p in [product, ver] if p).strip()
        open_ports.append(
            {"port": port, "state": state, "service": service, "version": version}
        )
    open_ports.sort(key=lambda x: x["port"])
    return {"open_ports": open_ports}


def run_nmap(host: str, ports: Iterable[int], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    port_list = [int(p) for p in ports]
    if not port_list:
        raise ValueError("ports must not be empty; refusing an unscoped scan")
    binary = _resolve_binary("nmap", env="DRIFTGUARD_NMAP_BIN")
    port_arg = ",".join(str(p) for p in port_list)
    cmd = [binary, "-Pn", "-sV", "-p", port_arg, "-oX", "-", str(host)]
    proc = _run(cmd, timeout=timeout)
    return parse_nmap(proc.stdout)


# ----------------------------- testssl ----------------------------- #


def _bool_from_finding(finding: str) -> bool | None:
    f = (finding or "").strip().lower()
    if f.startswith("not offered") or f == "no" or f.startswith("not supported"):
        return False
    if f.startswith("offered") or f == "yes" or f.startswith("supported"):
        return True
    if "not offered" in f:
        return False
    if "offered" in f:
        return True
    return None


def parse_testssl(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ToolError(f"unparseable testssl output: {exc}") from exc

    scan_result = data.get("scanResult")
    if not isinstance(scan_result, list):
        raise ToolError("unparseable testssl output: missing scanResult")

    target = None
    for item in scan_result:
        if isinstance(item, dict) and ("targetHost" in item or "ip" in item or "protocols" in item):
            target = item
            break
    if target is None:
        raise ToolError("unparseable testssl output: no target result")

    protocols: dict[str, bool] = {}
    for entry in target.get("protocols") or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("id")
        if not name:
            continue
        val = _bool_from_finding(entry.get("finding", ""))
        if val is None:
            sev = (entry.get("severity") or "").upper()
            val = sev in {"OK", "LOW", "MEDIUM", "HIGH", "CRITICAL"} and "not" not in (entry.get("finding", "").lower())
        protocols[str(name)] = bool(val)

    cipher_issues: list[str] = []
    for section in ("ciphers", "vulnerabilities", "cipherTests"):
        for entry in target.get(section) or []:
            if not isinstance(entry, dict):
                continue
            sev = (entry.get("severity") or "").upper()
            finding = entry.get("finding") or ""
            ident = entry.get("id") or section
            if sev in {"LOW", "MEDIUM", "HIGH", "CRITICAL", "WARN"} and finding:
                cipher_issues.append(f"{ident}: {finding}")

    cert: dict[str, Any] = {}
    for entry in target.get("serverDefaults") or []:
        if not isinstance(entry, dict):
            continue
        ident = entry.get("id") or ""
        if ident.startswith("cert") or ident in {
            "issuer",
            "subject",
            "commonName",
            "san",
            "notBefore",
            "notAfter",
        }:
            cert[ident] = entry.get("finding")

    return {"protocols": protocols, "cipher_issues": cipher_issues, "cert": cert}


def run_testssl(host: str, port: int, timeout: int = 300) -> dict[str, Any]:
    binary = _resolve_binary("testssl", "testssl.sh", env="DRIFTGUARD_TESTSSL_BIN")
    target = f"{host}:{int(port)}"
    with tempfile.NamedTemporaryFile(prefix="testssl_", suffix=".json", delete=False) as tf:
        json_path = tf.name
    try:
        cmd = [
            binary,
            "--jsonfile-pretty",
            json_path,
            "--warnings",
            "off",
            "--quiet",
            "--color",
            "0",
            "--ip",
            "one",
            "-p",
            "-S",
            target,
        ]
        proc = _run(cmd, timeout=timeout)
        content = ""
        try:
            with open(json_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            content = ""
        if not content.strip():
            content = proc.stdout or ""
    finally:
        try:
            os.unlink(json_path)
        except OSError:
            pass
    return parse_testssl(content)


# ----------------------------- httpx ----------------------------- #


_HTTP_STATUS_RE = re.compile(r"^HTTP/\d(?:\.\d)?\s+(\d{3})\b", re.MULTILINE)


def parse_httpx(output: str, url: str) -> dict[str, Any]:
    text = output or ""
    status_matches = _HTTP_STATUS_RE.findall(text)
    if not status_matches:
        m = re.search(r"\bStatus\s*:\s*(\d{3})\b", text, re.IGNORECASE)
        if m:
            status_matches = [m.group(1)]
    if not status_matches:
        raise ToolError("unparseable httpx output: no HTTP status code found")

    status_code = int(status_matches[-1])
    scheme = urlsplit(url).scheme or "http"

    location = None
    blocks = re.split(r"(?=^HTTP/\d)", text, flags=re.MULTILINE)
    resp_blocks = [b for b in blocks if b.lstrip().startswith("HTTP/")]
    last = resp_blocks[-1] if resp_blocks else text
    for line in last.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            if k.strip().lower() == "location":
                location = v.strip() or None
    if location is None and status_code in {301, 302, 303, 307, 308}:
        location = None

    final_url = url
    return {
        "status_code": status_code,
        "scheme": scheme,
        "location": location,
        "final_url": final_url,
    }


def run_httpx(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    binary = _resolve_binary("httpx", env="DRIFTGUARD_HTTPX_BIN")
    cmd = [binary, str(url), "--no-verify", "-v"]
    proc = _run(cmd, timeout=timeout)
    try:
        return parse_httpx(proc.stdout or proc.stderr, str(url))
    except ToolError:
        cmd_pd = [binary, "-u", str(url), "-json", "-silent", "-no-verify"]
        proc2 = _run(cmd_pd, timeout=timeout)
        return parse_httpx_json(proc2.stdout, str(url))


def parse_httpx_json(output: str, url: str) -> dict[str, Any]:
    line = None
    for raw in (output or "").splitlines():
        raw = raw.strip()
        if raw.startswith("{") and raw.endswith("}"):
            line = raw
            break
    if not line:
        raise ToolError("unparseable httpx output: no JSON object found")
    try:
        data = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ToolError(f"unparseable httpx json: {exc}") from exc
    status = data.get("status_code") or data.get("status-code") or data.get("status")
    if status is None:
        raise ToolError("unparseable httpx json: missing status code")
    scheme = data.get("scheme") or urlsplit(url).scheme or "http"
    location = data.get("location")
    final_url = data.get("final_url") or data.get("url") or data.get("final-url") or url
    return {
        "status_code": int(status),
        "scheme": str(scheme),
        "location": (str(location) if location not in (None, "") else None),
        "final_url": str(final_url),
    }


# ----------------------------- gobuster ----------------------------- #


_GOBUSTER_RE = re.compile(
    r"^(?P<path>/\S*?)\s+\(Status:\s*(?P<status>\d{3})\)\s+\[Size:\s*(?P<size>\d+)\]",
    re.MULTILINE,
)


def parse_gobuster(output: str) -> dict[str, Any]:
    text = output or ""
    found: list[dict[str, Any]] = []
    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    clean = clean.replace("\r", "")
    for m in _GOBUSTER_RE.finditer(clean):
        found.append(
            {
                "path": m.group("path"),
                "status": int(m.group("status")),
                "size": int(m.group("size")),
            }
        )
    if not found:
        meaningful = [
            ln
            for ln in clean.splitlines()
            if ln.strip()
            and not ln.startswith("=")
            and "Gobuster" not in ln
            and "by OJ Reeves" not in ln
            and "Starting gobuster" not in ln
            and "Finished" not in ln
            and not ln.strip().startswith("[+]")
        ]
        suspicious = [ln for ln in meaningful if not re.match(r"^\s*Progress:", ln)]
        if suspicious:
            raise ToolError(f"unparseable gobuster output: {suspicious[0]!r}")
    found.sort(key=lambda x: (x["path"], x["status"]))
    return {"found": found}


def run_gobuster(
    url: str, wordlist: str, timeout: int = DEFAULT_TIMEOUT
) -> dict[str, Any]:
    binary = _resolve_binary("gobuster", env="DRIFTGUARD_GOBUSTER_BIN")
    cmd = [
        binary,
        "dir",
        "-u",
        str(url),
        "-w",
        str(wordlist),
        "-k",
        "-q",
    ]
    proc = _run(cmd, timeout=timeout)
    return parse_gobuster(proc.stdout)
