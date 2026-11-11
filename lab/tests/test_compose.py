# tests/test_compose.py
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from domain import compose


class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.compose_file = Path("/lab/demcommerce/deploy/lab.compose.yaml")
        self.override = Path("/lab/demcommerce/deploy/extra.compose.yaml")

    @mock.patch("domain.compose.subprocess.run")
    def test_up_without_override_builds_expected_command(self, run):
        compose.up(self.compose_file)
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file), "up", "-d"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_up_with_override_includes_both_files(self, run):
        compose.up(self.compose_file, self.override)
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file),
             "-f", str(self.override), "up", "-d"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_reload_nginx_does_not_raise_when_container_absent(self, run):
        run.return_value.returncode = 1
        compose.reload_nginx(self.compose_file)  # must not raise
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file),
             "exec", "-T", "nginx", "nginx", "-s", "reload"],
            check=False,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_down_builds_expected_command(self, run):
        compose.down(self.compose_file)
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file), "down"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_recreate_forces_recreate_with_optional_override(self, run):
        compose.recreate(self.compose_file)
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file),
             "up", "-d", "--force-recreate"],
            check=True,
        )
        run.reset_mock()
        compose.recreate(self.compose_file, self.override)
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file),
             "-f", str(self.override), "up", "-d", "--force-recreate"],
            check=True,
        )

    @mock.patch("domain.compose.subprocess.run")
    def test_run_appends_args_and_returns_the_completed_process(self, run):
        result = compose.run(self.compose_file, "ps", "-q", "nginx")
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file),
             "ps", "-q", "nginx"],
            check=True,
        )
        self.assertIs(result, run.return_value)

    @mock.patch("domain.compose.subprocess.run")
    def test_run_passes_check_through(self, run):
        compose.run(self.compose_file, "logs", check=False)
        self.assertFalse(run.call_args.kwargs["check"])


class ValidateNginxConfigTests(unittest.TestCase):
    def setUp(self):
        self.compose_file = Path("/lab/demcommerce/deploy/lab.compose.yaml")

    @mock.patch("domain.compose.subprocess.run")
    def test_raises_when_nginx_rejects_config(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="", stderr='nginx: [emerg] bad directive in /etc/nginx/conf.d/default.conf:21\nnginx: configuration file /etc/nginx/nginx.conf test failed')
        with self.assertRaises(RuntimeError) as ctx:
            compose.validate_nginx_config(self.compose_file)
        self.assertIn("emerg", str(ctx.exception))
        self.assertIn("test failed", str(ctx.exception))

    @mock.patch("domain.compose.subprocess.run")
    def test_does_not_raise_when_container_absent(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="", stderr="service \"nginx\" is not running")
        compose.validate_nginx_config(self.compose_file)  # must not raise

    @mock.patch("domain.compose.subprocess.run")
    def test_does_not_raise_when_nginx_reports_ok(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="nginx: the configuration file /etc/nginx/nginx.conf syntax is ok",
            stderr="nginx: configuration file /etc/nginx/nginx.conf test is successful")
        compose.validate_nginx_config(self.compose_file)  # must not raise

    @mock.patch("domain.compose.subprocess.run")
    def test_runs_nginx_t_in_container(self, run):
        run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        compose.validate_nginx_config(self.compose_file)
        run.assert_called_once_with(
            ["docker", "compose", "-f", str(self.compose_file),
             "exec", "-T", "nginx", "nginx", "-t"],
            check=False, capture_output=True, text=True,
        )


if __name__ == "__main__":
    unittest.main()
