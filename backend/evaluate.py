#!/usr/bin/env python3
"""Evaluate the scanner against the lab's ground truth.

Joins engine evidence to the lab's ground-truth matrix on the frozen finding key
``<target>/<area>/<scenario>`` and the ground-truth scan label (``S0``, ``S1``, ...).

Runnable as a script::

    python3 backend/evaluate.py

and importable. It does not modify the database or the lab.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

# Allow running as `python3 backend/evaluate.py` from the repo root.
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PRESENT_LABELS = {"BASELINE", "NEW", "PERSISTENT", "RECURRING"}
ABSENT_LABELS = {"NO DRIFT", "FIXED"}


def _safe_rate(numer: int, denom: int) -> float | None:
    return (numer / denom) if denom else None


def _new_area_counts() -> dict[str, Any]:
    return {
        "detections": 0,
        "present_total": 0,
        "misses": 0,
        "detection_accuracy": None,
        "false_positives": 0,
        "absent_total": 0,
        "false_positive_rate": None,
        "unmeasured_scans": 0,
        "down_observations": 0,
    }


def _finalize_counts(counts: dict[str, Any]) -> dict[str, Any]:
    counts["misses"] = counts["present_total"] - counts["detections"]
    counts["detection_accuracy"] = _safe_rate(counts["detections"], counts["present_total"])
    counts["false_positive_rate"] = _safe_rate(counts["false_positives"], counts["absent_total"])
    return counts


def evaluate(
    truth_matrix: Mapping[str, Mapping[str, list[str | None]]],
    engine_evidence_by_label: Mapping[str, Iterable[str]],
    scan_labels: list[str],
    planted_scenarios: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Compute detection and false-positive metrics.

    Parameters
    ----------
    truth_matrix:
        ``{target: {scenario_name: [label per scan]}}`` as produced by the lab's
        ``truth_matrix`` (labels aligned with *scan_labels*; ``None`` means down).
    engine_evidence_by_label:
        ``{scan_label: [fingerprint, ...]}`` for engine scans. A label missing
        here means there was no matching engine scan (unmeasured).
    scan_labels:
        Ground-truth scan labels in order.
    planted_scenarios:
        ``{target: {scenario_name: area}}`` for scenarios planted for each target.
    """
    # Normalise evidence sets per label.
    evidence_sets: dict[str, set[str]] = {
        label: {fp for fp in fps} for label, fps in engine_evidence_by_label.items()
    }

    per_target: dict[str, Any] = {}
    overall = _new_area_counts()
    overall_areas: dict[str, dict[str, Any]] = defaultdict(_new_area_counts)
    unmeasured_truth_scans: list[str] = []
    engine_only_scans: list[str] = []

    truth_label_set = set(scan_labels)
    for label in scan_labels:
        if label not in evidence_sets:
            unmeasured_truth_scans.append(label)
    for label in evidence_sets:
        if label not in truth_label_set:
            engine_only_scans.append(label)

    # Per-target/per-area scoring over planted scenarios.
    for target, scenarios in truth_matrix.items():
        t_planted = planted_scenarios.get(target, {})
        t_areas: dict[str, dict[str, Any]] = defaultdict(_new_area_counts)
        for scenario_name, labels in scenarios.items():
            area = t_planted.get(scenario_name)
            if area is None:
                # Scenario in truth but not in planted mapping: cannot attribute to an area.
                continue
            key = f"{target}/{area}/{scenario_name}"
            for idx, label in enumerate(labels):
                scan_label = scan_labels[idx] if idx < len(scan_labels) else f"idx{idx}"
                if label is None:
                    # Target down for this scan: not scored.
                    t_areas[area]["down_observations"] += 1
                    overall_areas[area]["down_observations"] += 1
                    overall["down_observations"] += 1
                    continue
                if scan_label not in evidence_sets:
                    # No matching engine scan: unmeasured, not a miss/FP.
                    t_areas[area]["unmeasured_scans"] += 1
                    overall_areas[area]["unmeasured_scans"] += 1
                    overall["unmeasured_scans"] += 1
                    continue
                found = key in evidence_sets[scan_label]
                if label in PRESENT_LABELS:
                    t_areas[area]["present_total"] += 1
                    overall_areas[area]["present_total"] += 1
                    overall["present_total"] += 1
                    if found:
                        t_areas[area]["detections"] += 1
                        overall_areas[area]["detections"] += 1
                        overall["detections"] += 1
                elif label in ABSENT_LABELS:
                    t_areas[area]["absent_total"] += 1
                    overall_areas[area]["absent_total"] += 1
                    overall["absent_total"] += 1
                    if found:
                        t_areas[area]["false_positives"] += 1
                        overall_areas[area]["false_positives"] += 1
                        overall["false_positives"] += 1
                else:
                    # Unknown label: treat as unmeasured for honesty.
                    t_areas[area]["unmeasured_scans"] += 1
                    overall_areas[area]["unmeasured_scans"] += 1
                    overall["unmeasured_scans"] += 1

        # Findings whose key is not a planted scenario for this target are false positives.
        planted_keys = {f"{target}/{area}/{name}" for name, area in t_planted.items()}
        for label in scan_labels:
            if label not in evidence_sets:
                continue
            for fp in evidence_sets[label]:
                if not fp.startswith(f"{target}/"):
                    continue
                if fp in planted_keys:
                    continue
                # Attribute to the area encoded in the key when possible.
                parts = fp.split("/", 2)
                area = parts[1] if len(parts) >= 3 else "unknown"
                t_areas[area]["false_positives"] += 1
                overall_areas[area]["false_positives"] += 1
                overall["false_positives"] += 1

        per_target[target] = {
            "per_area": {area: _finalize_counts(counts) for area, counts in sorted(t_areas.items())},
        }

    # Findings for targets not present in the truth matrix at all: false positives.
    truth_targets = set(truth_matrix.keys())
    for label in scan_labels:
        if label not in evidence_sets:
            continue
        for fp in evidence_sets[label]:
            parts = fp.split("/", 2)
            if len(parts) < 3:
                continue
            tname, area = parts[0], parts[1]
            if tname in truth_targets:
                continue
            if tname not in per_target:
                per_target[tname] = {"per_area": {}}
            area_counts = per_target[tname]["per_area"].setdefault(area, _new_area_counts())
            area_counts["false_positives"] += 1
            overall_areas[area]["false_positives"] += 1
            overall["false_positives"] += 1

    # Finalise per-target and overall.
    for tdata in per_target.values():
        for counts in tdata["per_area"].values():
            _finalize_counts(counts)

    report = {
        "per_target": per_target,
        "per_area": {area: _finalize_counts(counts) for area, counts in sorted(overall_areas.items())},
        "overall": _finalize_counts(overall),
        "unmeasured": {
            "ground_truth_scans_without_engine_scan": unmeasured_truth_scans,
            "engine_scans_without_ground_truth": engine_only_scans,
        },
        "scan_labels": list(scan_labels),
    }
    return report


def format_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    def pct(rate):
        return "n/a" if rate is None else f"{rate * 100:.1f}%"

    lines.append("== Overall ==")
    o = report["overall"]
    lines.append(
        f"detection: {o['detections']}/{o['present_total']} ({pct(o['detection_accuracy'])}), "
        f"FPs: {o['false_positives']} over {o['absent_total']} absent ({pct(o['false_positive_rate'])}), "
        f"unmeasured: {o['unmeasured_scans']}, down: {o['down_observations']}"
    )
    for target, tdata in sorted(report["per_target"].items()):
        lines.append(f"\n-- {target} --")
        for area, a in sorted(tdata["per_area"].items()):
            lines.append(
                f"  {area}: detection {a['detections']}/{a['present_total']} ({pct(a['detection_accuracy'])}), "
                f"FP {a['false_positives']}/{a['absent_total']} ({pct(a['false_positive_rate'])}), "
                f"unmeasured {a['unmeasured_scans']}, down {a['down_observations']}"
            )
    unm = report["unmeasured"]
    if unm["ground_truth_scans_without_engine_scan"] or unm["engine_scans_without_ground_truth"]:
        lines.append("\n== Unmeasured scans ==")
        if unm["ground_truth_scans_without_engine_scan"]:
            lines.append(f"  truth without engine: {unm['ground_truth_scans_without_engine_scan']}")
        if unm["engine_scans_without_ground_truth"]:
            lines.append(f"  engine without truth: {unm['engine_scans_without_ground_truth']}")
    return "\n".join(lines)


def load_engine_evidence(db, target_name_by_id: Mapping[int, str] | None = None) -> tuple[dict[str, set[str]], list[str]]:
    """Load evidence grouped by scan label from the database.

    Returns (evidence_by_label, engine_only_labels_info).
    """
    from driftguard import models  # local import so module is importable without DB side effects
    scans = list(db.scalars(__import__('sqlalchemy').select(models.Scan).order_by(models.Scan.id)))
    by_label: dict[str, set[str]] = defaultdict(set)
    for scan in scans:
        if not scan.label:
            continue
        rows = list(db.scalars(__import__('sqlalchemy').select(models.Evidence).where(models.Evidence.scan_id == scan.id)))
        for ev in rows:
            by_label[scan.label].add(ev.fingerprint)
    return dict(by_label), []


def planted_from_registry(targets: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Build {target: {scenario_name: area}} from lab Target objects."""
    out: dict[str, dict[str, str]] = {}
    for name, target in targets.items():
        out[name] = {s.name: s.area for s in target.scenarios}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate scanner findings against lab ground truth.")
    parser.add_argument("--repo-root", default=None, help="Repository root.")
    parser.add_argument("--database-url", default=None, help="Override DRIFTGUARD_DATABASE_URL.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).resolve().parents[1]
    if args.database_url:
        os.environ["DRIFTGUARD_DATABASE_URL"] = args.database_url

    # Load lab ground truth via the lab's own logic.
    from driftguard.sync import load_lab_truth
    scans, truth_matrix, targets = load_lab_truth(repo_root)
    scan_labels = [s.label for s in scans]
    planted = planted_from_registry(targets)

    # Load engine evidence from DB.
    from driftguard.database import SessionLocal
    db = SessionLocal()
    try:
        evidence_by_label, _ = load_engine_evidence(db)
    finally:
        db.close()

    report = evaluate(truth_matrix, evidence_by_label, scan_labels, planted)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
