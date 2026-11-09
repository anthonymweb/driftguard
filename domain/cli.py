"""CLI for the controlled test domain (spec §6.6)."""
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urlparse

from . import config, state
from .config import TARGETS
from .probes import probe_port_open
from .targets import MODULES


def _port_of(base_url: str) -> int:
    parsed = urlparse(base_url)
    if parsed.port is not None:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def _host_of(base_url: str) -> str:
    parsed = urlparse(base_url)
    return parsed.hostname or "127.0.0.1"


def _is_down(target) -> bool:
    """DOWN when probe_port_open on the target's base_url port returns absent."""
    return probe_port_open(_host_of(target.base_url), _port_of(target.base_url)) == "absent"


def _get_target(name: str):
    target = TARGETS.get(name)
    if target is None:
        print(f"unknown target: {name}", file=sys.stderr)
        return None, 2
    return target, 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="domain.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status")
    p_status.add_argument("--json", action="store_true", dest="json_out")

    p_truth = sub.add_parser("truth")
    p_truth.add_argument("--json", action="store_true", dest="json_out")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--json", action="store_true", dest="json_out")

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("label")

    p_up = sub.add_parser("up")
    p_up.add_argument("target", nargs="?")

    p_down = sub.add_parser("down")
    p_down.add_argument("target", nargs="?")

    p_on = sub.add_parser("on")
    p_on.add_argument("target")
    p_on.add_argument("scenario")

    p_off = sub.add_parser("off")
    p_off.add_argument("target")
    p_off.add_argument("scenario")

    p_reset = sub.add_parser("reset")
    p_reset.add_argument("target", nargs="?")

    return parser


def _cmd_status(args) -> int:
    result = {}
    for name, target in TARGETS.items():
        mod = MODULES[name]
        if _is_down(target):
            result[name] = "DOWN"
        else:
            result[name] = mod.read_state()
    if getattr(args, "json_out", False):
        print(json.dumps({"targets": result}))
    else:
        for name, states in result.items():
            if states == "DOWN":
                print(f"{name}: DOWN")
            else:
                print(f"{name}:")
                for k, v in states.items():
                    print(f"  {k}: {v}")
    return 0


def _cmd_truth(args) -> int:
    matrix = state.truth_matrix(TARGETS, state.read_scans())
    if getattr(args, "json_out", False):
        print(json.dumps(matrix))
    else:
        for tname, scenarios in matrix.items():
            print(f"{tname}:")
            for sname, labels in scenarios.items():
                print(f"  {sname}: {labels}")
    return 0


def _cmd_verify(args) -> int:
    result = {}
    failed = False
    for name, target in TARGETS.items():
        mod = MODULES[name]
        if _is_down(target):
            result[name] = {
                s.name: {"observed": "unknown", "expected": None, "match": True}
                for s in target.scenarios}
            continue
        recorded = mod.read_state()
        probes = mod.probes()
        tresult = {}
        for s in target.scenarios:
            expected_state = recorded.get(s.name, False)
            observed = probes[s.name]()
            if expected_state:
                expected_obs = "present"
            else:
                expected_obs = "absent"
            if observed == "unknown":
                match = False  # unknown while UP is mismatch
            else:
                match = observed == expected_obs
            if not match:
                failed = True
            tresult[s.name] = {
                "observed": observed,
                "expected": expected_obs,
                "match": match,
            }
        result[name] = tresult
    if getattr(args, "json_out", False):
        print(json.dumps(result))
    else:
        for tname, scenarios in result.items():
            print(f"{tname}:")
            for sname, info in scenarios.items():
                status = "OK" if info["match"] else "MISMATCH"
                print(f"  {sname}: {info['observed']} (expected {info['expected']}) {status}")
    return 1 if failed else 0


def _cmd_mark(args) -> int:
    states = {}
    for name, target in TARGETS.items():
        mod = MODULES[name]
        if _is_down(target):
            states[name] = None
        else:
            states[name] = mod.read_state()
    state.record_scan(args.label, states)
    return 0


def _cmd_up(args) -> int:
    if args.target:
        target, rc = _get_target(args.target)
        if rc:
            return rc
        MODULES[args.target].up()
    else:
        for name in TARGETS:
            MODULES[name].up()
    return 0


def _cmd_down(args) -> int:
    if args.target:
        target, rc = _get_target(args.target)
        if rc:
            return rc
        MODULES[args.target].down()
    else:
        for name in TARGETS:
            MODULES[name].down()
    return 0


def _cmd_toggle(args, enable: bool) -> int:
    target, rc = _get_target(args.target)
    if rc:
        return rc
    scenario_names = {s.name for s in target.scenarios}
    if args.scenario not in scenario_names:
        print(f"unknown scenario: {args.scenario}", file=sys.stderr)
        return 2
    mod = MODULES[args.target]
    previous = mod.read_state()
    current = dict(previous)
    current[args.scenario] = enable
    mod.apply(previous, current)
    return 0


def _cmd_reset(args) -> int:
    names = [args.target] if args.target else list(TARGETS.keys())
    for name in names:
        target, rc = _get_target(name)
        if rc:
            return rc
        mod = MODULES[name]
        previous = mod.read_state()
        current = {s.name: False for s in target.scenarios}
        mod.apply(previous, current)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 2
        return 2 if code != 0 else 0
    cmd = args.command
    if cmd == "status":
        return _cmd_status(args)
    if cmd == "truth":
        return _cmd_truth(args)
    if cmd == "verify":
        return _cmd_verify(args)
    if cmd == "mark":
        return _cmd_mark(args)
    if cmd == "up":
        return _cmd_up(args)
    if cmd == "down":
        return _cmd_down(args)
    if cmd == "on":
        return _cmd_toggle(args, True)
    if cmd == "off":
        return _cmd_toggle(args, False)
    if cmd == "reset":
        return _cmd_reset(args)
    return 2
