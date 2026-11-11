"""Five-state drift classification for one scenario's presence history (spec §6.4)."""
from collections.abc import Sequence


def classify(history: Sequence[bool]) -> list[str]:
    """Return the drift label for each scan in a boolean presence history.

    Rules, in order: the first scan is BASELINE when present, else NO DRIFT.
    A present scan after an absent one is RECURRING when it appeared at any
    earlier index, else NEW; a present scan after a present one is PERSISTENT;
    an absent scan after a present one is FIXED; otherwise NO DRIFT.
    """
    labels: list[str] = []
    for i, present in enumerate(history):
        if i == 0:
            labels.append("BASELINE" if present else "NO DRIFT")
        elif present and not history[i - 1]:
            labels.append("RECURRING" if any(history[:i - 1]) else "NEW")
        elif present:
            labels.append("PERSISTENT")
        elif history[i - 1]:
            labels.append("FIXED")
        else:
            labels.append("NO DRIFT")
    return labels
