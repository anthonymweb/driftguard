import json
import os
import re
import sys
import unittest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from server import app  # noqa: E402

# Captured from the pre-change implementation (Task 14 contract): byte-identical.
DEBUG_PAYLOAD = (
    b'{"api_key":"lab-demo-key","db":"postgres://svc_admin:lab-secret@db-internal.eservices.test:5432/records",'
    b'"internal_hosts":["10.20.0.5","10.20.0.6"],"sample_record":{"id":"TEST-0001","name":"Test Citizen One",'
    b'"national_id":"CMTEST00000001","pension_status":"ACTIVE","phone":"+256700000001"}}\n'
)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_body_is_unchanged(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok", "service": "eservices-lab"})

    def test_services_is_a_list_keeping_id_name_dept(self):
        r = self.client.get("/api/v1/services")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 9)
        ids = [s["id"] for s in data]
        for sid in ("SVC-01", "SVC-02", "SVC-03"):
            self.assertIn(sid, ids)
        for s in data:
            self.assertIn("id", s)
            self.assertIn("name", s)
            self.assertIn("dept", s)
            self.assertIsInstance(s["id"], str)
            self.assertIsInstance(s["name"], str)
            self.assertIsInstance(s["dept"], str)

    def test_records_requires_the_api_key(self):
        r = self.client.get("/api/v1/records/TEST-0001")
        self.assertEqual(r.status_code, 401)

    def test_unknown_record_is_404(self):
        r = self.client.get("/api/v1/records/NO-SUCH-RECORD", headers={"X-API-Key": "lab-demo-key"})
        self.assertEqual(r.status_code, 404)

    def test_record_fields_preserved(self):
        r = self.client.get("/api/v1/records/TEST-0001", headers={"X-API-Key": "lab-demo-key"})
        self.assertEqual(r.status_code, 200)
        rec = r.get_json()
        for k in ("id", "name", "phone", "national_id", "pension_status"):
            self.assertIn(k, rec)
        self.assertEqual(rec["id"], "TEST-0001")
        self.assertEqual(rec["name"], "Test Citizen One")
        self.assertEqual(rec["phone"], "+256700000001")
        self.assertEqual(rec["national_id"], "CMTEST00000001")
        self.assertEqual(rec["pension_status"], "ACTIVE")

    def test_debug_payload_is_byte_identical(self):
        r = self.client.get("/api/v1/admin/debug")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, DEBUG_PAYLOAD)

    def test_demo_data_holds_no_real_looking_identifiers(self):
        # Scan demo_data module textually for real-looking hostnames/IPs/emails.
        import demo_data  # noqa: F401
        path = demo_data.__file__
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # No real TLD-like production hostnames outside .test; allow 10.20.0.0/24 and localhost refs in comments none.
        self.assertNotRegex(text, r"\b\S+\.com\b")
        self.assertNotRegex(text, r"\b\S+\.org\b")
        self.assertNotRegex(text, r"\b\S+\.gov\b")
        self.assertNotRegex(text, r"\b\S+\.net\b")
        # No public IPv4 outside 10.20.0.0/24 range used.
        for m in re.finditer(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", text):
            ip = m.group(1)
            self.assertTrue(ip.startswith("10.20.0."), f"unexpected IP {ip}")


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_page_renders_the_catalogue(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn("eServices", body)
        self.assertIn("DEMONSTRATION SITE", body.upper())
        self.assertIn("SVC-01", body)
        self.assertIn("Registry", body)

    def test_service_page_renders_one_service(self):
        r = self.client.get("/services/SVC-01")
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn("SVC-01", body)
        self.assertIn("Citizen Records Lookup", body)

    def test_applications_page_renders_sample_references(self):
        r = self.client.get("/applications")
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn("ESB-2026-000123", body)

    def test_notices_page_renders(self):
        r = self.client.get("/notices")
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn("Notices", body)

    def test_help_page_renders(self):
        r = self.client.get("/help")
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        self.assertIn("Help", body)

    def test_records_lookup_page_renders(self):
        r = self.client.get("/records")
        self.assertEqual(r.status_code, 200)
        body = r.get_data(as_text=True)
        # key must be asked for, not baked in
        self.assertIn("API", body)
        self.assertNotIn("lab-demo-key", body)

    def test_post_application_returns_new_reference(self):
        r = self.client.post("/api/v1/applications", json={"service_id": "SVC-01", "applicant": "Test Applicant"})
        self.assertEqual(r.status_code, 201)
        data = r.get_json()
        self.assertIn("reference", data)
        self.assertTrue(data["reference"].startswith("ESB-2026-"))

    def test_additive_api_routes(self):
        r = self.client.get("/api/v1/services/SVC-01")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["id"], "SVC-01")
        r = self.client.get("/api/v1/departments")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.get_json(), list)
        r = self.client.get("/api/v1/applications")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/v1/notices")
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
