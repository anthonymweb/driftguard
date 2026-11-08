import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard.database import Base, get_db
from driftguard.main import app


class ApiAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
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
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def test_pending_target_cannot_be_queued_for_assessment(self):
        target = self.client.post("/api/targets", json={
            "name": "Local lab", "address": "https://localhost:8443", "target_type": "web",
            "approved_scope": ["tls"], "approved_ports": [8443],
        })
        self.assertEqual(target.status_code, 201)
        response = self.client.post(f"/api/targets/{target.json()['id']}/scans")
        self.assertEqual(response.status_code, 403)

    def test_authorized_active_scoped_target_records_queued_request(self):
        target = self.client.post("/api/targets", json={
            "name": "Local lab", "address": "https://localhost:8443", "target_type": "web",
            "authorization_status": "authorized", "approved_scope": ["tls"], "approved_ports": [8443],
        })
        response = self.client.post(f"/api/targets/{target.json()['id']}/scans")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")

    def test_out_of_range_port_rejected(self):
        response = self.client.post("/api/targets", json={
            "name": "Bad target", "address": "localhost", "target_type": "host",
            "approved_ports": [70000],
        })
        self.assertEqual(response.status_code, 422)

    def test_unsafe_target_url_rejected(self):
        response = self.client.post("/api/targets", json={
            "name": "Bad target", "address": "https://user:password@example.test/private", "target_type": "web",
        })
        self.assertEqual(response.status_code, 422)

    def test_frontend_origin_has_narrow_cors_access(self):
        response = self.client.options("/api/targets", headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://127.0.0.1:5173")


if __name__ == "__main__":
    unittest.main()
