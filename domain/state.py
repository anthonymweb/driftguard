"""State, scans and ground-truth storage for the test domain (spec §6.4)."""
import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import ROOT
from .classify import classify
from .model import AREA_LABELS, Target

GROUND_TRUTH_PATH: Path = ROOT / "ground_truth.csv"
SCANS_PATH: Path = ROOT / "scans.json"
GROUND_TRUTH_COLUMNS = ["timestamp_utc", "target", "event", "scenario", "action",
                        "category", "expected_finding", "finding_key", "state_after"]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_state(path: Path, scenario_names: Sequence[str]) -> dict[str, bool]:
    """Scenario states from path; a missing file (or missing key) means False, as in lab.py."""
    data = json.loads(path.read_text()) if path.exists() else {}
    return {name: bool(data.get(name)) for name in scenario_names}


def write_state(path: Path, state: dict[str, bool]) -> None:
    path.write_text(json.dumps(state))


@dataclass(frozen=True)
class ScanRecord:
    label: str
    timestamp_utc: str
    states: dict[str, dict[str, bool] | None]  # None = target down


@dataclass(frozen=True)
class GroundTruthRow:
    timestamp_utc: str
    target: str
    event: str
    scenario: str
    action: str
    category: str
    expected_finding: str
    finding_key: str
    state_after: str

    def __post_init__(self) -> None:
        # Area guard: any row that names a scenario or an area must carry one of the
        # three frozen audit areas, so no finding_key can ever leave {TLS, Network, API}
        # (spec §6.4). Pure event rows with no scenario carry no area and pass through.
        if (self.scenario or self.category) and self.category not in AREA_LABELS:
            raise ValueError(
                f"ground-truth area {self.category!r} is not one of {sorted(AREA_LABELS)}")


def record_scan(label: str, states: dict[str, dict[str, bool] | None]) -> None:
    """Append a scan record to SCANS_PATH (created as [] when absent)."""
    scans = json.loads(SCANS_PATH.read_text()) if SCANS_PATH.exists() else []
    scans.append({"label": label, "timestamp_utc": _utcnow(), "states": states})
    SCANS_PATH.write_text(json.dumps(scans, indent=1))


def read_scans() -> list[ScanRecord]:
    if not SCANS_PATH.exists():
        return []
    return [ScanRecord(label=r["label"], timestamp_utc=r["timestamp_utc"], states=r["states"])
            for r in json.loads(SCANS_PATH.read_text())]


def append_ground_truth(row: GroundTruthRow) -> None:
    """Append one row; the header is written only when the file does not exist (as in lab.py)."""
    new = not GROUND_TRUTH_PATH.exists()
    with GROUND_TRUTH_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if new:
            writer.writerow(GROUND_TRUTH_COLUMNS)
        writer.writerow([getattr(row, column) for column in GROUND_TRUTH_COLUMNS])


def truth_matrix(targets: dict[str, Target],
                 scans: Sequence[ScanRecord]) -> dict[str, dict[str, list[str | None]]]:
    """target → scenario → one label per scan.

    A scan where the target was down is None — excluded from scoring, never "NO DRIFT"
    (spec §6.6); such a scan counts as absent while classifying the neighbouring scans.
    """
    matrix: dict[str, dict[str, list[str | None]]] = {}
    for name, target in targets.items():
        per_scenario: dict[str, list[str | None]] = {}
        for scenario in target.scenarios:
            down: list[bool] = []
            history: list[bool] = []
            for scan in scans:
                states = scan.states.get(name)
                down.append(states is None)
                present = states.get(scenario.name, False) if states else False
                history.append(bool(present))
            labels = classify(history)
            per_scenario[scenario.name] = [
                None if was_down else label for was_down, label in zip(down, labels)]
        matrix[name] = per_scenario
    return matrix
