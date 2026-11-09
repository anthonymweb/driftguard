# tests/test_compose.py
import unittest
from pathlib import Path
from unittest import mock

from domain import compose


class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.project_dir = Path("/lab/demcommerce/deploy")
        self.compose_yaml = str(self.project_dir / "compose.yaml")

    @mock.patch("domain.compose.subprocess.run")
    def test_up_without_override_builds_expected_command(self, run):
        compose.up(self.project_dir)
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml, "up", "-d"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_up_with_override_includes_both_files(self, run):
        override = Path("/lab/demcommerce/deploy/extra.yaml")
        compose.up(self.project_dir, override)
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml,
             "-f", str(override), "up", "-d"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_reload_nginx_does_not_raise_when_container_absent(self, run):
        run.return_value.returncode = 1
        compose.reload_nginx(self.project_dir)  # must not raise
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml,
             "exec", "-T", "nginx", "nginx", "-s", "reload"],
            check=False,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_down_builds_expected_command(self, run):
        compose.down(self.project_dir)
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml, "down"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_recreate_forces_recreate_with_optional_override(self, run):
        compose.recreate(self.project_dir)
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml,
             "up", "-d", "--force-recreate"],
            check=True,
        )
        run.reset_mock()
        override = Path("/lab/demcommerce/deploy/extra.yaml")
        compose.recreate(self.project_dir, override)
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml,
             "-f", str(override), "up", "-d", "--force-recreate"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_run_appends_args_and_returns_the_completed_process(self, run):
        result = compose.run(self.project_dir, "ps", "-q", "nginx")
        run.assert_called_once_with(
            ["docker", "compose", "-f", self.compose_yaml, "ps", "-q", "nginx"],
            check=True,
        )
        self.assertIs(result, run.return_value)

    @mock.patch("domain.compose.subprocess.run")
    def test_run_passes_check_through(self, run):
        compose.run(self.project_dir, "logs", check=False)
        self.assertFalse(run.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
