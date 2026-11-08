"""Deterministic, evidence-based baseline classification."""
from collections.abc import Sequence

DRIFT_TYPES = {"NEW", "PERSISTENT", "FIXED", "RECURRING", "NO DRIFT"}


def classify(current: set[str], previous: set[str], earlier: Sequence[set[str]]) -> dict[str, str]:
    """Classify fingerprints for a scan against the immediately prior scan.

    Current evidence is NEW unless it appeared in earlier history, when it is RECURRING;
    evidence in both scans is PERSISTENT; evidence only in the prior scan is FIXED.
    An empty change set produces a single NO DRIFT event at the caller level.
    """
    result = {fingerprint: "PERSISTENT" for fingerprint in current & previous}
    for fingerprint in current - previous:
        result[fingerprint] = "RECURRING" if any(fingerprint in snapshot for snapshot in earlier) else "NEW"
    for fingerprint in previous - current:
        result[fingerprint] = "FIXED"
    return result
