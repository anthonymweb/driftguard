"""Self-signed lab certificates, mirroring eservices-lab/lab.py gen_certs."""
import shutil
import subprocess
from pathlib import Path

from . import ROOT

# name: (subject, subjectAltName) — localhost covers every HTTPS endpoint
# (certificates do not encode ports); mismatch serves the cert-mismatch drift.
CERT_SPECS = (
    ("localhost", "/CN=localhost",
     "subjectAltName=DNS:localhost,IP:127.0.0.1"),
    ("mismatch", "/CN=wrong-host.example",
     "subjectAltName=DNS:wrong-host.example"),
)


def ensure_certs(cert_dir: Path = ROOT / "certs") -> None:
    """Create localhost.crt/.key and mismatch.crt/.key in *cert_dir* when absent.

    No-op for a certificate that already exists. Prefers a locally installed
    openssl; falls back to `docker run --rm -v <dir>:/certs alpine/openssl`
    exactly as lab.py's gen_certs does.
    """
    cert_dir = Path(cert_dir)
    cert_dir.mkdir(parents=True, exist_ok=True)
    local = shutil.which("openssl")
    for name, subj, san in CERT_SPECS:
        if (cert_dir / f"{name}.crt").exists():
            continue
        base = str(cert_dir) if local else "/certs"
        args = ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "365",
                "-keyout", f"{base}/{name}.key",
                "-out", f"{base}/{name}.crt",
                "-subj", subj, "-addext", san]
        command = (["openssl"] if local else
                   ["docker", "run", "--rm", "-v", f"{cert_dir}:/certs",
                    "alpine/openssl"]) + args
        subprocess.run(command, check=True, stderr=subprocess.DEVNULL)
