"""Structured logs and an attribution trail that outlives the database.

Two requirements meet here: the service must emit machine-readable logs, and the
project's safety rules require who/when/basis to be traceable for every
authorisation and every assessment request — including refusals.
"""
import io
import json
import logging
import unittest
from contextlib import contextmanager
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard.audit import audit
from driftguard.database import Base, get_db, get_session_factory
from driftguard.logconfig import JsonFormatter, configure_logging
from driftguard.main import app


@contextmanager
def captured_audit():
    """Collect the audit trail as parsed JSON objects."""
    stream = io.StringIO()
    logger = logging.getLogger("driftguard.audit")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    try:
        yield lambda: [
            json.loads(line) for line in stream.getvalue().splitlines() if line.strip()
        ]
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


class StructuredLoggingTests(unittest.TestCase):
    def test_application_logs_are_one_json_object_per_line(self):
        stream = io.StringIO()
        configure_logging(stream=stream, level=logging.INFO)
        logging.getLogger("driftguard.scanner").info(
            "tool finished", extra={"event": "tool.completed", "tool": "nmap", "duration_s": 1.5}
        )
        lines = [line for line in stream.getvalue().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        payload = json.loads(lines[0])
        self.assertEqual(payload["event"], "tool.completed")
        self.assertEqual(payload["tool"], "nmap")
        self.assertEqual(payload["duration_s"], 1.5)
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "driftguard.scanner")
        self.assertIn("timestamp", payload)

    def test_audit_records_carry_event_actor_and_fields(self):
        with captured_audit() as records:
            returned = audit(
                "target.authorized",
                actor="researcher",
                target_id=3,
                basis="LAB-2026-01",
            )
        entries = records()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["event"], "target.authorized")
        self.assertEqual(entry["actor"], "researcher")
        self.assertEqual(entry["target_id"], 3)
        self.assertEqual(entry["basis"], "LAB-2026-01")
        self.assertIn("timestamp", entry)
        self.assertEqual(returned["event"], "target.authorized")


class AuditTrailApiTests(unittest.TestCase):
    """The endpoints must write the trail, not just the audit helper."""

    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine, expire_on_commit=False)

        def override_db():
            db = factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = lambda: factory
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_scan_requests_are_audited(self):
        with captured_audit() as records:
            with mock.patch("driftguard.scanner.tools.run_testssl", return_value={
                "protocols": {"TLS1_2": True}, "cipher_issues": [],
                "cert": {"cert_commonName": "localhost"},
            }):
                target = self.client.post("/api/targets", json={
                    "name": "Local lab", "address": "https://localhost:8443",
                    "target_type": "web", "authorization_status": "authorized",
                    "approved_scope": ["tls"], "approved_ports": [8443],
                    "authorized_by": "researcher",
                    "authorized_at": "2026-11-13T09:00:00Z",
                    "authorization_basis": "LAB-2026-01",
                })
                self.assertEqual(target.status_code, 201)
                response = self.client.post(f"/api/targets/{target.json()['id']}/scans")
                self.assertEqual(response.status_code, 201)
        entries = records()
        requested = [e for e in entries if e["event"] == "scan.requested"]
        self.assertEqual(len(requested), 1)
        self.assertEqual(requested[0]["target_id"], target.json()["id"])
        self.assertEqual(requested[0]["scan_id"], response.json()["id"])

    def test_refused_scans_are_audited_with_the_reason(self):
        # A refusal is exactly the moment attribution matters most: the record
        # must show that an assessment was requested and turned down.
        with captured_audit() as records:
            target = self.client.post("/api/targets", json={
                "name": "Local lab", "address": "https://localhost:8443",
                "target_type": "web", "approved_scope": ["tls"], "approved_ports": [8443],
            })
            self.assertEqual(target.status_code, 201)
            response = self.client.post(f"/api/targets/{target.json()['id']}/scans")
            self.assertEqual(response.status_code, 403)
        entries = records()
        refused = [e for e in entries if e["event"] == "scan.refused"]
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0]["target_id"], target.json()["id"])
        self.assertIn("explicitly authorized", refused[0]["reason"])

    def test_evidence_exports_are_audited(self):
        # The redacted view is the shareable boundary; exporting it is an
        # attributable action.
        with captured_audit() as records:
            with mock.patch("driftguard.scanner.tools.run_testssl", return_value={
                "protocols": {"TLS1_2": True}, "cipher_issues": [],
                "cert": {"cert_commonName": "localhost"},
            }):
                target = self.client.post("/api/targets", json={
                    "name": "Local lab", "address": "https://localhost:8443",
                    "target_type": "web", "authorization_status": "authorized",
                    "approved_scope": ["tls"], "approved_ports": [8443],
                    "authorized_by": "researcher",
                    "authorized_at": "2026-11-13T09:00:00Z",
                    "authorization_basis": "LAB-2026-01",
                })
                self.assertEqual(target.status_code, 201)
                scan = self.client.post(f"/api/targets/{target.json()['id']}/scans")
                self.assertEqual(scan.status_code, 201)
                response = self.client.get(f"/api/scans/{scan.json()['id']}/evidence/redacted")
                self.assertEqual(response.status_code, 200)
        entries = records()
        exported = [e for e in entries if e["event"] == "evidence.exported"]
        self.assertEqual(len(exported), 1)
        self.assertEqual(exported[0]["scan_id"], scan.json()["id"])
        self.assertIs(exported[0]["redacted"], True)


if __name__ == "__main__":
    unittest.main()
