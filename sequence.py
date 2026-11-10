#!/usr/bin/env python3
"""Run the canonical nine-scan drift-classification sequence (spec §6.5).

Drives the frozen ``domain.py`` CLI in subprocesses, records marks S0–S9,
and prints the final ground-truth matrix. Safe to run more than once.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOMAIN_PY = ROOT / "domain.py"

STEPS = [
    ("S1", []),  # all off
    ("S2", [("on", "tls-legacy"), ("on", "cert-mismatch")]),
    ("S3", [("on", "http-plain")]),
    ("S4", [("off", "tls-legacy"), ("on", "port-open")]),
    ("S5", [("on", "tls-legacy")]),
    ("S6", [("on", "api-debug")]),
    ("S7", [("off", "http-plain"), ("off", "port-open"), ("off", "api-debug")]),
    ("S8", [("on", "http-plain"), ("on", "api-debug")]),
    ("S9", [("on", "port-open")]),
]


def run(*args: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(DOMAIN_PY), *args]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=capture,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        msg = f"command failed (exit {proc.returncode}): {' '.join(cmd)}"
        if detail:
            msg += f"\n{detail}"
        raise SystemExit(msg)
    return proc


def supported_scenarios() -> dict[str, set[str]]:
    proc = run("status", "--json", capture=True)
    data = json.loads(proc.stdout)
    out: dict[str, set[str]] = {}
    for target, states in data.get("targets", {}).items():
        if states == "DOWN":
            out[target] = set()
        else:
            out[target] = set(states.keys())
    return out


def main() -> int:
    if not DOMAIN_PY.exists():
        raise SystemExit(f"domain CLI not found: {DOMAIN_PY}")

    # Known baseline and S0 mark before any drift (so the first drift is NEW).
    run("reset")
    run("mark", "S0")

    scenarios = supported_scenarios()
    for label, toggles in STEPS:
        for action, scenario in toggles:
            for target, has in scenarios.items():
                if scenario in has:
                    run(action, target, scenario)
        run("mark", label)

    run("truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
