"""Where the pieces of a DriftGuard installation live.

The engine assesses systems; the **lab** is the controlled test domain it is
measured against. The lab is a sibling of the backend in this repository
(``lab/``), but it may also be pointed somewhere else — a separate checkout, a
copy on another machine — so its location is configurable.
"""
import os
from pathlib import Path

# The repository root: backend/driftguard/settings.py -> backend/ -> repository root.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The controlled test domain's directory.
LAB_DIR = Path(os.getenv("DRIFTGUARD_LAB_DIR", REPO_ROOT / "lab")).resolve()

#: The lab's CLI — the documented interface to the domain. The engine drives the
#: lab through this, never by importing it.
LAB_CLI = LAB_DIR / "domain.py"

#: Where the lab records its authoritative ground-truth log.
LAB_GROUND_TRUTH = LAB_DIR / "ground_truth.csv"


def lab_available() -> bool:
    """Is the lab present and usable?"""
    return LAB_CLI.is_file()
