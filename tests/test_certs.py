# tests/test_certs.py
import subprocess
import tempfile
import unittest
from pathlib import Path

from domain.certs import ensure_certs


class CertTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cert_dir = Path(tmp.name)

    def test_creates_both_certificates(self):
        ensure_certs(self.cert_dir)
        for name in ("localhost", "mismatch"):
            self.assertTrue((self.cert_dir / f"{name}.crt").is_file(), name)
            self.assertTrue((self.cert_dir / f"{name}.key").is_file(), name)

    def test_is_idempotent(self):
        ensure_certs(self.cert_dir)
        before = {p.name: p.stat().st_mtime_ns for p in self.cert_dir.iterdir()}
        ensure_certs(self.cert_dir)
        after = {p.name: p.stat().st_mtime_ns for p in self.cert_dir.iterdir()}
        self.assertEqual(before, after)  # existing certs are left untouched

    def test_localhost_cert_has_expected_san(self):
        ensure_certs(self.cert_dir)
        text = subprocess.run(
            ["openssl", "x509", "-text", "-noout",
             "-in", str(self.cert_dir / "localhost.crt")],
            check=True, capture_output=True, text=True).stdout
        self.assertIn("DNS:localhost", text)
        self.assertIn("IP Address:127.0.0.1", text)


if __name__ == "__main__":
    unittest.main()
