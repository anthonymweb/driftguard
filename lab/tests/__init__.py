"""Test package for the test-domain controller.

Rule: tests must never write to the repository's live state or config paths.
The registered target modules keep their live state/config at fixed, gitignored
paths inside the worktree; a test that reaches them can silently corrupt the
authoritative ground truth of a research run.

Do not run ``git clean -fdx`` in this worktree: it destroys live domain
artifacts (built front-end bundles, state files, rendered configs).
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from domain.targets import MODULES


class LivePaths(NamedTuple):
    state: Path
    config: Path | None


def _snapshot(paths: LivePaths) -> dict[str, object]:
    def info(path: Path | None):
        if path is None:
            return None
        try:
            st = path.stat()
            return (True, st.st_mtime_ns, st.st_size, path.read_bytes())
        except FileNotFoundError:
            return (False, None, None, None)

    return {"state": info(paths.state), "config": info(paths.config)}


# Real STATE_PATH / CONFIG_PATH values of every registered target module,
# captured at import time so a regression guard can assert they stay untouched.
LIVE_TARGET_PATHS: dict[str, LivePaths] = {
    name: LivePaths(
        state=Path(mod.STATE_PATH),
        config=Path(mod.CONFIG_PATH) if getattr(mod, "CONFIG_PATH", None) is not None else None,
    )
    for name, mod in MODULES.items()
}


def live_path_snapshots() -> dict[str, dict[str, object]]:
    """Current bytes/mtime/existence of every live state/config path."""
    return {name: _snapshot(paths) for name, paths in LIVE_TARGET_PATHS.items()}
