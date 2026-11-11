# tests/test_probes.py
import http.server
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
import warnings
from pathlib import Path

from domain.probes import (probe_api_path, probe_cert_mismatch, probe_http_plain,
                           probe_port_open, probe_tls_legacy)


def _status_handler(status: int):
    """A handler class that answers every GET with `status`."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args):
            pass  # silence request logging so unittest output stays pristine

    return Handler


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.certdir = Path(tmp.name)
        cls._gen_cert("good", "/CN=localhost",
                      "subjectAltName=DNS:localhost,DNS:eservices.test,IP:127.0.0.1")
        cls._gen_cert("mismatch", "/CN=wrong-host.example",
                      "subjectAltName=DNS:wrong-host.example")

    @classmethod
    def _gen_cert(cls, name: str, subject: str, san: str) -> None:
        # the same `openssl req -x509` invocation as lab.py gen_certs, into a temp dir
        subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365",
             "-keyout", str(cls.certdir / f"{name}.key"),
             "-out", str(cls.certdir / f"{name}.crt"),
             "-subj", subject, "-addext", san],
            check=True, capture_output=True)

    # --- helpers -------------------------------------------------------------

    def _start_http(self, status: int) -> int:
        server = http.server.HTTPServer(("127.0.0.1", 0), _status_handler(status))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self._stop_http, server, thread)
        return server.server_address[1]

    @staticmethod
    def _stop_http(server: http.server.HTTPServer, thread: threading.Thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    @staticmethod
    def _closed_port() -> int:
        # bound then released: connecting to it is refused
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]

    def _start_listener(self) -> int:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        self.addCleanup(listener.close)
        return listener.getsockname()[1]

    def _start_tls(self, context: ssl.SSLContext) -> int:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(0.25)  # so the accept loop can notice `stopped`
        stopped = threading.Event()

        def serve():
            while not stopped.is_set():
                try:
                    conn, _ = listener.accept()
                except TimeoutError:
                    continue
                except OSError:
                    return  # listener closed during teardown
                try:
                    with context.wrap_socket(conn, server_side=True):
                        pass
                except (ssl.SSLError, OSError):
                    conn.close()  # handshake rejected (e.g. a legacy-only client offer)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.addCleanup(self._stop_tls, listener, thread, stopped)
        return listener.getsockname()[1]

    @staticmethod
    def _stop_tls(listener: socket.socket, thread: threading.Thread,
                  stopped: threading.Event) -> None:
        stopped.set()  # the accept loop exits on its own within one poll interval
        thread.join(timeout=5)
        listener.close()

    def _server_context(self, *, cert: str = "good",
                        legacy: bool = False) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.certdir / f"{cert}.crt"),
                                str(self.certdir / f"{cert}.key"))
        with warnings.catch_warnings():
            # ssl.TLSVersion.TLSv1 is deprecated — the legacy probe deliberately uses it
            warnings.simplefilter("ignore")
            if legacy:
                context.set_ciphers("ALL:@SECLEVEL=0")
                context.minimum_version = ssl.TLSVersion.TLSv1
            else:
                context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context

    # --- probe_api_path ------------------------------------------------------

    def test_api_path_2xx_is_present(self):          # local http.server returning 200
        port = self._start_http(200)
        self.assertEqual(probe_api_path("127.0.0.1", port, "/health", tls=False),
                         "present")

    def test_api_path_403_is_absent(self):           # local handler returning 403
        port = self._start_http(403)
        self.assertEqual(probe_api_path("127.0.0.1", port, "/admin/debug", tls=False),
                         "absent")

    def test_api_path_404_is_absent(self):
        port = self._start_http(404)
        self.assertEqual(probe_api_path("127.0.0.1", port, "/missing", tls=False),
                         "absent")

    def test_api_path_refused_is_unknown(self):      # closed port
        self.assertEqual(
            probe_api_path("127.0.0.1", self._closed_port(), "/health", tls=False),
            "unknown")

    # --- probe_http_plain ----------------------------------------------------

    def test_http_plain_2xx_is_present(self):
        port = self._start_http(200)
        self.assertEqual(probe_http_plain("127.0.0.1", port), "present")

    def test_http_plain_301_is_absent(self):
        port = self._start_http(301)
        self.assertEqual(probe_http_plain("127.0.0.1", port), "absent")

    # --- probe_port_open -----------------------------------------------------

    def test_port_open_refused_is_absent(self):
        self.assertEqual(probe_port_open("127.0.0.1", self._closed_port()), "absent")

    def test_port_open_listening_is_present(self):
        port = self._start_listener()
        self.assertEqual(probe_port_open("127.0.0.1", port), "present")

    # --- probe_tls_legacy ----------------------------------------------------

    @unittest.skipUnless(ssl.HAS_TLSv1, "TLS 1.0 unavailable in this OpenSSL build")
    def test_tls_legacy_handshake_succeeds_is_present(self):
        # in-process TLS 1.0 server (PROTOCOL_TLS_SERVER, minimum_version=TLSv1,
        # set_ciphers("ALL:@SECLEVEL=0")), self-signed cert generated in setUpClass
        port = self._start_tls(self._server_context(legacy=True))
        self.assertEqual(probe_tls_legacy("127.0.0.1", port), "present")

    def test_tls_legacy_tls12_only_server_is_absent(self):
        port = self._start_tls(self._server_context())
        self.assertEqual(probe_tls_legacy("127.0.0.1", port), "absent")

    # --- probe_cert_mismatch -------------------------------------------------

    def test_cert_mismatch_hostname_failure_is_present(self):
        # server presents mismatch.crt while the client trusts BOTH good.crt and
        # mismatch.crt (the lab.py two-CA setup) → hostname verification fails → present
        port = self._start_tls(self._server_context(cert="mismatch"))
        cafiles = [self.certdir / "good.crt", self.certdir / "mismatch.crt"]
        self.assertEqual(probe_cert_mismatch("127.0.0.1", port, cafiles), "present")

    def test_cert_mismatch_untrusted_cert_is_unknown(self):
        # client trusts only good.crt, server presents mismatch.crt → unknown CA,
        # not a hostname failure → unknown
        port = self._start_tls(self._server_context(cert="mismatch"))
        self.assertEqual(
            probe_cert_mismatch("127.0.0.1", port, [self.certdir / "good.crt"]),
            "unknown")


if __name__ == "__main__":
    unittest.main()
