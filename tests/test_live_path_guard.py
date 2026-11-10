"""Regression guard: tests must never touch live state/config paths.

Exercises each registered target module's apply()/up() code paths with paths
redirected to a temporary directory and all external side effects mocked, then
asserts the repository's real live state/config files were not modified.
Deterministic and fast: no real network, no real sleeps, no docker.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from domain.targets import MODULES

try:
    from . import live_path_snapshots
except ImportError:  # pragma: no cover - supports `unittest discover -s tests`
    from tests import live_path_snapshots  # type: ignore[no-redef]



class LivePathGuardTests(unittest.TestCase):
    def _exercise_module(self, name: str, module, tmp: Path) -> None:
        patches = [mock.patch.object(module, "STATE_PATH", tmp / "state.json")]
        if getattr(module, "CONFIG_PATH", None) is not None:
            patches.append(
                mock.patch.object(module, "CONFIG_PATH", tmp / "conf.d" / "default.conf")
            )

        # Mock external side effects/waits on the module (attribute lookups).
        for attr in ("compose", "certs", "_wait_for_ready", "_init_db"):
            if hasattr(module, attr):
                patches.append(mock.patch.object(module, attr))

        # eservices shells out via its imported `subprocess.run`.
        if name == "eservices-lab":
            patches.append(mock.patch("domain.targets.eservices.subprocess.run"))

        # Enter patches manually to keep control explicit.
        started = [p.start() for p in patches]
        try:
            previous = module.read_state()
            current = dict(previous)
            module.apply(previous, current)
            if hasattr(module, "up"):
                module.up()
        finally:
            for p in reversed(patches):
                p.stop()

    def test_apply_and_up_never_touch_live_paths(self):
        before = live_path_snapshots()
        for name, module in MODULES.items():
            with self.subTest(target=name):
                with tempfile.TemporaryDirectory() as td:
                    self._exercise_module(name, module, Path(td))
                self.assertEqual(
                    before[name],
                    live_path_snapshots()[name],
                    f"{name} modified its live state/config path(s)",
                )


if __name__ == "__main__":
    unittest.main()
