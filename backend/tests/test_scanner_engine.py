import unittest
from datetime import datetime, timezone
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard import models
from driftguard.database import Base, get_db
from driftguard.main import app
from driftguard.scanner.engine import ScanRefused, assess_target, derive_host, derive_http_url, derive_tls_port
from driftguard.scanner.tools import ToolError


def _auth_fields(**overrides):
    base = {
        "authorized_by": "alice@example.test",
        "authorized_at": "2026-11-11T10:00:00Z",
        "authorization_basis": "TICKET-123",
    }
    base.update(overrides)
    return base


class _DBTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def tearDown(self):
        self.engine.dispose()

    def db(self):
        return self.Session()


class DerivationTests(unittest.TestCase):
    def test_derive_host_from_bare_hostname(self):
        self.assertEqual(derive_host("example.test"), "example.test")

    def test_derive_host_from_host_port(self):
        self.assertEqual(derive_host("example.test:8443"), "example.test")

    def test_derive_host_from_url(self):
        self.assertEqual(derive_host("https://example.test:8443"), "example.test")

    def test_derive_tls_port_from_url(self):
        self.assertEqual(derive_tls_port("https://example.test:8443", [8443, 443]), 8443)

    def test_derive_tls_port_from_host_port(self):
        self.assertEqual(derive_tls_port("example.test:9443", [9443]), 9443)

    def test_derive_tls_port_falls_back_to_https_like_approved(self):
        self.assertEqual(derive_tls_port("example.test", [8080, 443]), 443)

    def test_derive_tls_port_falls_back_to_first_approved(self):
        self.assertEqual(derive_tls_port("example.test", [8443, 8080]), 8443)

    def test_derive_http_url_from_https_url(self):
        self.assertEqual(derive_http_url("https://example.test:8443", [8443, 443]), "https://example.test:8443")

    def test_derive_http_url_from_http_url(self):
        self.assertEqual(derive_http_url("http://example.test:8080", [8080]), "http://example.test:8080")

    def test_derive_http_url_from_bare_host_uses_http_and_first_web_port(self):
        self.assertEqual(derive_http_url("example.test", [8443, 8080]), "http://example.test:8080")

    def test_derive_http_url_from_bare_host_with_no_approved_ports_is_refused(self):
        with self.assertRaises(ScanRefused):
            derive_http_url("example.test", [])


class EngineRefusalTests(_DBTestCase):
    def _target(self, **overrides):
        data = {
            "name": "t",
            "address": "https://example.test:8443",
            "target_type": "web",
            "authorization_status": "authorized",
            "authorized_by": "alice@example.test",
            "authorized_at": datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc),
            "authorization_basis": "TICKET-123",
            "approved_scope": ["tls", "network", "http_api"],
            "approved_ports": [8443, 8080],
            "status": "active",
            "discovery_enabled": False,
            "discovery_wordlist": None,
        }
        data.update(overrides)
        db = self.db()
        target = models.Target(**data)
        db.add(target)
        db.commit()
        db.refresh(target)
        db.close()
        return target.id

    def test_refuses_when_not_authorized(self):
        target_id = self._target(authorization_status="pending")
        db = self.db()
        target = db.get(models.Target, target_id)
        with self.assertRaises(ScanRefused) as ctx:
            assess_target(db, target)
        self.assertIn("authorized", str(ctx.exception).lower())
        self.assertEqual(db.scalar(select(models.Scan).where(models.Scan.target_id == target_id)), None)
        db.close()

    def test_refuses_when_not_active(self):
        target_id = self._target(status="inactive")
        db = self.db()
        target = db.get(models.Target, target_id)
        with self.assertRaises(ScanRefused) as ctx:
            assess_target(db, target)
        self.assertIn("active", str(ctx.exception).lower())
        self.assertEqual(list(db.scalars(select(models.Scan))), [])
        db.close()

    def test_refuses_when_no_scope(self):
        target_id = self._target(approved_scope=[])
        db = self.db()
        target = db.get(models.Target, target_id)
        with self.assertRaises(ScanRefused) as ctx:
            assess_target(db, target)
        self.assertIn("scope", str(ctx.exception).lower())
        db.close()

    def test_refuses_when_missing_authorisation_record(self):
        target_id = self._target(authorized_by=None, authorized_at=None, authorization_basis=None)
        db = self.db()
        target = db.get(models.Target, target_id)
        with self.assertRaises(ScanRefused) as ctx:
            assess_target(db, target)
        msg = str(ctx.exception).lower()
        self.assertTrue("authorisation" in msg or "authorization" in msg)
        self.assertEqual(list(db.scalars(select(models.Scan))), [])
        db.close()

    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_refuses_when_address_port_not_approved_and_invokes_no_tools(
        self, m_nmap, m_testssl, m_httpx, m_gobuster
    ):
        target_id = self._target(address="https://example.test:9999", approved_ports=[443, 8443])
        db = self.db()
        target = db.get(models.Target, target_id)
        with self.assertRaises(ScanRefused) as ctx:
            assess_target(db, target)
        msg = str(ctx.exception)
        self.assertIn("9999", msg)
        self.assertIn("approved", msg.lower())
        self.assertEqual(list(db.scalars(select(models.Scan))), [])
        m_nmap.assert_not_called()
        m_testssl.assert_not_called()
        m_httpx.assert_not_called()
        m_gobuster.assert_not_called()
        db.close()


class EngineAssessmentTests(_DBTestCase):
    def _make_target(self, db, **overrides):
        data = {
            "name": "svc",
            "address": "https://svc.test:8443",
            "target_type": "web",
            "authorization_status": "authorized",
            "authorized_by": "alice@example.test",
            "authorized_at": datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc),
            "authorization_basis": "TICKET-123",
            "approved_scope": ["network", "tls", "http_api"],
            "approved_ports": [8443, 8080],
            "status": "active",
            "discovery_enabled": False,
            "discovery_wordlist": None,
        }
        data.update(overrides)
        target = models.Target(**data)
        db.add(target)
        db.commit()
        db.refresh(target)
        return target

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_authorized_target_stores_evidence_and_calls_tools_with_approved_ports(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db)
        m_nmap.return_value = {"open_ports": [{"port": 8081, "state": "open", "service": "http", "version": ""}]}
        m_testssl.return_value = {"protocols": {"TLS1": True, "TLS1_1": False}, "cipher_issues": [], "cert": {"cert_commonName": "svc.test"}}

        def httpx_side(url, **kwargs):
            if str(url).startswith("https://"):
                return {"status_code": 200, "scheme": "https", "location": None, "final_url": str(url)}
            return {"status_code": 301, "scheme": "http", "location": "https://svc.test:8443/", "final_url": str(url)}

        m_httpx.side_effect = httpx_side
        m_gobuster.return_value = {"found": []}

        scan = assess_target(db, target)

        m_nmap.assert_called_once_with("svc.test", [8443, 8080])
        m_testssl.assert_called_once_with("svc.test", 8443)
        # secure/base probe and plain-HTTP probe (8080 is an approved plain port)
        self.assertEqual(m_httpx.call_args_list[0].args[0], "https://svc.test:8443")
        self.assertEqual(m_httpx.call_args_list[1].args[0], "http://svc.test:8080")
        m_gobuster.assert_not_called()  # discovery off by default

        self.assertEqual(scan.status, "completed")
        self.assertIsNotNone(scan.completed_at)
        evidence = list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id)))
        fps = {e.fingerprint for e in evidence}
        self.assertIn("svc/Network/port-open", fps)
        self.assertIn("svc/TLS/tls-legacy", fps)
        self.assertNotIn("svc/Network/http-plain", fps)  # plain endpoint redirected to HTTPS
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_tool_failure_records_failure_and_continues_partial_not_clean(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db)
        m_nmap.side_effect = ToolError("nmap boom")
        m_testssl.return_value = {"protocols": {"TLS1": False, "TLS1_1": False, "TLS1_2": True}, "cipher_issues": [], "cert": {"cert_commonName": "svc.test"}}

        def httpx_side(url, **kwargs):
            if str(url).startswith("https://"):
                return {"status_code": 200, "scheme": "https", "location": None, "final_url": str(url)}
            return {"status_code": 301, "scheme": "http", "location": "https://svc.test:8443/", "final_url": str(url)}

        m_httpx.side_effect = httpx_side

        scan = assess_target(db, target)

        self.assertEqual(scan.status, "completed_with_errors")
        self.assertIn("nmap", (scan.error or "").lower())
        # testssl/httpx still ran (secure + plain probes)
        m_testssl.assert_called_once()
        self.assertEqual(m_httpx.call_count, 2)
        # no evidence items expected from these observations, but scan is not clean
        evidence = list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id)))
        self.assertEqual(evidence, [])
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_all_tools_fail_marks_scan_failed_not_clean(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db)
        m_nmap.side_effect = ToolError("nmap boom")
        m_testssl.side_effect = ToolError("tls boom")
        m_httpx.side_effect = ToolError("http boom")

        scan = assess_target(db, target)

        self.assertEqual(scan.status, "failed")
        self.assertIsNotNone(scan.error)
        # secure and plain probes both attempted and failed
        self.assertGreaterEqual(m_httpx.call_count, 2)
        evidence = list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id)))
        self.assertEqual(evidence, [])
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_no_previous_scan_produces_evidence_but_no_drift_events(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db, approved_scope=["network"], approved_ports=[8443])
        m_nmap.return_value = {"open_ports": [{"port": 8081, "state": "open", "service": "http", "version": ""}]}

        scan = assess_target(db, target)

        evidence = list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id)))
        self.assertTrue(any(e.fingerprint == "svc/Network/port-open" for e in evidence))
        events = list(db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id == scan.id)))
        self.assertEqual(events, [])
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_drift_classified_against_previous_scan(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db, approved_scope=["network"], approved_ports=[8443])

        # previous scan has port-open
        prev = models.Scan(target_id=target.id, status="completed")
        db.add(prev)
        db.flush()
        db.add(models.Evidence(scan_id=prev.id, fingerprint="svc/Network/port-open", category="Network",
                               title="Unexpected open port", severity="high", resource="8081", details={}))
        db.commit()

        # current scan: port-open gone
        m_nmap.return_value = {"open_ports": []}
        scan = assess_target(db, target)

        events = list(db.scalars(select(models.DriftEvent).where(models.DriftEvent.scan_id == scan.id)))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].evidence_fingerprint, "svc/Network/port-open")
        self.assertEqual(events[0].classification, "FIXED")
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_discovery_off_by_default_gobuster_never_called(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db, approved_scope=["http_api"], discovery_enabled=False)

        def httpx_side(url, **kwargs):
            if str(url).startswith("https://"):
                return {"status_code": 200, "scheme": "https", "location": None, "final_url": str(url)}
            return {"status_code": 301, "scheme": "http", "location": "https://svc.test:8443/", "final_url": str(url)}

        m_httpx.side_effect = httpx_side
        assess_target(db, target)
        m_gobuster.assert_not_called()
        # base + plain probes
        self.assertEqual(m_httpx.call_count, 2)
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_discovery_enabled_calls_gobuster_for_that_target_only(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db, approved_scope=["http_api"], discovery_enabled=True, discovery_wordlist="/tmp/wl.txt")

        def httpx_side(url, **kwargs):
            if str(url).startswith("https://"):
                return {"status_code": 200, "scheme": "https", "location": None, "final_url": str(url)}
            return {"status_code": 301, "scheme": "http", "location": "https://svc.test:8443/", "final_url": str(url)}

        m_httpx.side_effect = httpx_side
        m_gobuster.return_value = {"found": [{"path": "/debug", "status": 200, "size": 10}]}
        scan = assess_target(db, target)
        m_gobuster.assert_called_once_with("https://svc.test:8443", "/tmp/wl.txt")
        fps = {e.fingerprint for e in db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id))}
        self.assertIn("svc/API/api-debug", fps)
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_plain_http_probe_produces_http_plain_evidence(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db, approved_scope=["http_api"], approved_ports=[8443, 8080])

        def httpx_side(url, **kwargs):
            if str(url).startswith("https://"):
                return {"status_code": 200, "scheme": "https", "location": None, "final_url": str(url)}
            # plain endpoint serves the app (no redirect to HTTPS)
            return {"status_code": 200, "scheme": "http", "location": None, "final_url": str(url)}

        m_httpx.side_effect = httpx_side
        scan = assess_target(db, target)
        evidence = list(db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id)))
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].fingerprint, "svc/Network/http-plain")
        db.close()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_gobuster")
    @mock.patch("driftguard.scanner.engine.tools.run_httpx")
    @mock.patch("driftguard.scanner.engine.tools.run_testssl")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_no_plain_http_probe_when_no_plain_port_approved(
        self, m_nmap, m_testssl, m_httpx, m_gobuster, m_sleep
    ):
        db = self.db()
        target = self._make_target(db, approved_scope=["http_api"], approved_ports=[8443])
        m_httpx.return_value = {"status_code": 200, "scheme": "https", "location": None, "final_url": "https://svc.test:8443"}
        scan = assess_target(db, target)
        # only the secure/base probe; no plain-HTTP endpoint is approved
        m_httpx.assert_called_once_with("https://svc.test:8443")
        fps = {e.fingerprint for e in db.scalars(select(models.Evidence).where(models.Evidence.scan_id == scan.id))}
        self.assertNotIn("svc/Network/http-plain", fps)
        db.close()


class ApiScanEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        def override_db():
            db = factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        # Background assessment opens its own session; point it at the test database.
        import driftguard.database as dg_db

        self._orig_session_local = dg_db.SessionLocal
        dg_db.SessionLocal = factory
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        import driftguard.database as dg_db

        dg_db.SessionLocal = self._orig_session_local
        app.dependency_overrides.clear()
        self.engine.dispose()

    def _create_authorized_target(self, **extra):
        payload = {
            "name": "svc",
            "address": "https://svc.test:8443",
            "target_type": "web",
            "authorization_status": "authorized",
            "approved_scope": ["network"],
            "approved_ports": [8443],
            **_auth_fields(),
            **extra,
        }
        r = self.client.post("/api/targets", json=payload)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    @mock.patch("driftguard.scanner.engine.time.sleep")
    @mock.patch("driftguard.scanner.engine.tools.run_nmap")
    def test_scan_endpoint_runs_assessment_and_returns_completed(self, m_nmap, m_sleep):
        m_nmap.return_value = {"open_ports": []}
        target = self._create_authorized_target()
        r = self.client.post(f"/api/targets/{target['id']}/scans")
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        self.assertEqual(body["status"], "queued")
        # Starlette's TestClient runs background tasks before returning, so the
        # assessment has completed and the scan record reflects the final state.
        scans = self.client.get(f"/api/targets/{target['id']}/scans").json()
        self.assertEqual(scans[0]["id"], body["id"])
        self.assertEqual(scans[0]["status"], "completed")

    def test_create_target_requires_auth_record_when_authorized(self):
        payload = {
            "name": "svc",
            "address": "https://svc.test:8443",
            "target_type": "web",
            "authorization_status": "authorized",
            "approved_scope": ["network"],
            "approved_ports": [8443],
            # missing auth fields
        }
        r = self.client.post("/api/targets", json=payload)
        self.assertEqual(r.status_code, 422)

    def test_pending_target_can_be_created_without_auth_record(self):
        payload = {
            "name": "svc",
            "address": "https://svc.test:8443",
            "target_type": "web",
            "authorization_status": "pending",
            "approved_scope": ["network"],
            "approved_ports": [8443],
        }
        r = self.client.post("/api/targets", json=payload)
        self.assertEqual(r.status_code, 201)


if __name__ == "__main__":
    unittest.main()
