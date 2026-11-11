import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from driftguard.scanner import tools

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


class NmapAdapterTests(unittest.TestCase):
    def test_parse_nmap_fixture(self):
        out = tools.parse_nmap(read_fixture("nmap_8443.xml"))
        self.assertEqual(
            out,
            {
                "open_ports": [
                    {
                        "port": 8443,
                        "state": "open",
                        "service": "http",
                        "version": "nginx 1.27.5",
                    }
                ]
            },
        )

    def test_run_nmap_refuses_empty_ports(self):
        with self.assertRaises(ValueError):
            tools.run_nmap("127.0.0.1", [])

    def test_run_nmap_builds_scoped_command(self):
        calls = {}

        def fake_run(cmd, **kwargs):
            calls["cmd"] = cmd
            calls["kwargs"] = kwargs
            return subprocess.CompletedProcess(cmd, 0, stdout=read_fixture("nmap_8443.xml"), stderr="")

        with mock.patch.object(tools, "_which", return_value="/usr/bin/nmap"), \
             mock.patch.object(tools.subprocess, "run", side_effect=fake_run):
            tools.run_nmap("127.0.0.1", [8445, 8083])
        self.assertEqual(calls["cmd"][0], "/usr/bin/nmap")
        self.assertIn("-p", calls["cmd"])
        idx = calls["cmd"].index("-p")
        self.assertEqual(calls["cmd"][idx + 1], "8445,8083")
        self.assertFalse(calls["kwargs"].get("shell"))
        self.assertIn("timeout", calls["kwargs"])

    def test_run_nmap_nonzero_exit_raises(self):
        cp = subprocess.CompletedProcess(["nmap"], 1, stdout="", stderr="boom")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/nmap"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_nmap("127.0.0.1", [8443])

    def test_run_nmap_missing_binary_raises(self):
        with mock.patch.object(tools, "_which", return_value=None):
            with self.assertRaises(tools.ToolError):
                tools.run_nmap("127.0.0.1", [8443])

    def test_run_nmap_unparseable_raises(self):
        cp = subprocess.CompletedProcess(["nmap"], 0, stdout="not xml", stderr="")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/nmap"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_nmap("127.0.0.1", [8443])

    def test_run_nmap_timeout_raises(self):
        with mock.patch.object(tools, "_which", return_value="/usr/bin/nmap"), \
             mock.patch.object(tools.subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="nmap", timeout=1)):
            with self.assertRaises(tools.ToolError):
                tools.run_nmap("127.0.0.1", [8443])


class TestsslAdapterTests(unittest.TestCase):
    def test_parse_testssl_fixture(self):
        out = tools.parse_testssl(read_fixture("testssl_8443.json"))
        self.assertIn("protocols", out)
        self.assertIn("cipher_issues", out)
        self.assertIn("cert", out)
        self.assertIsInstance(out["cipher_issues"], list)
        self.assertIsInstance(out["cert"], dict)
        self.assertEqual(out["protocols"].get("TLS1_2"), True)
        self.assertEqual(out["protocols"].get("TLS1_3"), True)
        self.assertEqual(out["protocols"].get("SSLv2"), False)
        self.assertEqual(out["protocols"].get("SSLv3"), False)

    def test_run_testssl_resolves_binary(self):
        calls = {}

        def fake_run(cmd, **kwargs):
            calls["cmd"] = cmd
            return subprocess.CompletedProcess(cmd, 0, stdout=read_fixture("testssl_8443.json"), stderr="")

        with mock.patch.object(tools, "_which", side_effect=lambda n: "/usr/bin/testssl" if n == "testssl" else None), \
             mock.patch.object(tools.subprocess, "run", side_effect=fake_run):
            tools.run_testssl("127.0.0.1", 8443)
        self.assertTrue(calls["cmd"][0].endswith("testssl"))

    def test_run_testssl_nonzero_exit_raises(self):
        cp = subprocess.CompletedProcess(["testssl"], 2, stdout="", stderr="err")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/testssl"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_testssl("127.0.0.1", 8443)

    def test_run_testssl_missing_binary_raises(self):
        with mock.patch.object(tools, "_which", return_value=None):
            with self.assertRaises(tools.ToolError):
                tools.run_testssl("127.0.0.1", 8443)

    def test_run_testssl_unparseable_raises(self):
        cp = subprocess.CompletedProcess(["testssl"], 0, stdout="not json", stderr="")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/testssl"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_testssl("127.0.0.1", 8443)


class HttpxAdapterTests(unittest.TestCase):
    def test_parse_httpx_fixture(self):
        out = tools.parse_httpx(read_fixture("httpx_verbose_8443.txt"), "https://127.0.0.1:8443")
        self.assertEqual(out["status_code"], 200)
        self.assertEqual(out["scheme"], "https")
        self.assertIsNone(out.get("location"))
        self.assertEqual(out.get("final_url"), "https://127.0.0.1:8443")

    def test_run_httpx_nonzero_exit_raises(self):
        cp = subprocess.CompletedProcess(["httpx"], 1, stdout="", stderr="err")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/httpx"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_httpx("https://127.0.0.1:8443")

    def test_run_httpx_missing_binary_raises(self):
        with mock.patch.object(tools, "_which", return_value=None):
            with self.assertRaises(tools.ToolError):
                tools.run_httpx("https://127.0.0.1:8443")

    def test_run_httpx_unparseable_raises(self):
        cp = subprocess.CompletedProcess(["httpx"], 0, stdout="garbage", stderr="")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/httpx"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_httpx("https://127.0.0.1:8443")


class GobusterAdapterTests(unittest.TestCase):
    def test_parse_gobuster_fixture(self):
        out = tools.parse_gobuster(read_fixture("gobuster_8443.txt"))
        self.assertIn("found", out)
        self.assertEqual(out["found"], [{"path": "/health", "status": 200, "size": 42}])

    def test_parse_gobuster_with_no_hits_is_an_empty_result_not_a_failure(self):
        # A clean scan that found nothing is a valid observation, not a parse
        # failure: the banner and progress lines must be filtered out and the
        # result must be an empty list rather than an error.
        out = tools.parse_gobuster(read_fixture("gobuster_8443_nohits.txt"))
        self.assertEqual(out, {"found": []})

    def test_run_gobuster_nonzero_exit_raises(self):
        cp = subprocess.CompletedProcess(["gobuster"], 1, stdout="", stderr="err")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/gobuster"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_gobuster("https://127.0.0.1:8443", "/tmp/wl.txt")

    def test_run_gobuster_missing_binary_raises(self):
        with mock.patch.object(tools, "_which", return_value=None):
            with self.assertRaises(tools.ToolError):
                tools.run_gobuster("https://127.0.0.1:8443", "/tmp/wl.txt")

    def test_run_gobuster_unparseable_raises(self):
        cp = subprocess.CompletedProcess(["gobuster"], 0, stdout="nonsense line", stderr="")
        with mock.patch.object(tools, "_which", return_value="/usr/bin/gobuster"), \
             mock.patch.object(tools.subprocess, "run", return_value=cp):
            with self.assertRaises(tools.ToolError):
                tools.run_gobuster("https://127.0.0.1:8443", "/tmp/wl.txt")


if __name__ == "__main__":
    unittest.main()
