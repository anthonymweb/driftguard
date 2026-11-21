"""Authentication and role-based authorisation.

The safety rules require every assessment to be attributable. When the API is
exposed beyond a single researcher's machine, that attribution has to come from
an authenticated caller rather than from whoever can reach the port: a
``viewer`` may read evidence, an ``operator`` may queue assessments, an
``admin`` may register targets and manage users.

With no secret configured the service stays open for local research — the
documented default for this project — but demanding auth without supplying a
secret must fail fast rather than silently run open.
"""
import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard.auth import validate_auth_config
from driftguard.database import Base, get_db, get_session_factory
from driftguard.main import app

SECRET = "test-secret-key-for-driftguard-auth"
CONFIG_VARS = (
    "DRIFTGUARD_AUTH_SECRET",
    "DRIFTGUARD_AUTH_REQUIRED",
    "DRIFTGUARD_LOGIN_RATE_LIMIT",
)


class AuthTestCase(unittest.TestCase):
    """Shared harness: auth enabled, isolated database, clean rate-limit state."""

    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in CONFIG_VARS}
        os.environ["DRIFTGUARD_AUTH_SECRET"] = SECRET
        os.environ.pop("DRIFTGUARD_AUTH_REQUIRED", None)
        limiter = getattr(app.state, "limiter", None)
        if limiter is not None:
            limiter.reset()

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
        limiter = getattr(app.state, "limiter", None)
        if limiter is not None:
            limiter.reset()
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    # -- helpers ----------------------------------------------------------
    def create_user(self, username, password, role, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.client.post(
            "/api/users",
            json={"username": username, "password": password, "role": role},
            headers=headers,
        )

    def login(self, username, password):
        return self.client.post(
            "/api/auth/token",
            json={"username": username, "password": password},
        )

    @staticmethod
    def bearer(response):
        return {"Authorization": f"Bearer {response.json()['access_token']}"}


class AuthenticationTests(AuthTestCase):
    def test_requests_without_a_token_are_refused(self):
        self.assertEqual(self.client.get("/api/targets").status_code, 401)
        self.assertEqual(self.client.post("/api/targets", json={
            "name": "x", "address": "localhost", "target_type": "host",
        }).status_code, 401)
        self.assertEqual(self.client.post("/api/targets/1/scans").status_code, 401)

    def test_a_malformed_token_is_refused(self):
        response = self.client.get(
            "/api/targets", headers={"Authorization": "Bearer not-a-jwt"}
        )
        self.assertEqual(response.status_code, 401)

    def test_login_issues_a_token_and_rejects_a_wrong_password(self):
        self.assertEqual(
            self.create_user("admin", "correct-horse-battery", "admin").status_code, 201
        )
        ok = self.login("admin", "correct-horse-battery")
        self.assertEqual(ok.status_code, 200)
        body = ok.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["token_type"], "bearer")
        self.assertEqual(body["role"], "admin")
        self.assertEqual(self.login("admin", "wrong-password").status_code, 401)

    def test_login_attempts_are_rate_limited(self):
        self.create_user("admin", "correct-horse-battery", "admin")
        os.environ["DRIFTGUARD_LOGIN_RATE_LIMIT"] = "3/minute"
        statuses = [
            self.login("admin", "wrong-password").status_code for _ in range(4)
        ]
        self.assertEqual(statuses[:3], [401, 401, 401])
        self.assertEqual(statuses[3], 429)

    def test_local_research_mode_stays_open_without_a_secret(self):
        os.environ.pop("DRIFTGUARD_AUTH_SECRET", None)
        response = self.client.post("/api/targets", json={
            "name": "Local lab", "address": "https://localhost:8443",
            "target_type": "web", "approved_scope": ["tls"], "approved_ports": [8443],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get("/api/targets").status_code, 200)

    def test_demanding_auth_without_a_secret_fails_fast(self):
        os.environ.pop("DRIFTGUARD_AUTH_SECRET", None)
        os.environ["DRIFTGUARD_AUTH_REQUIRED"] = "1"
        with self.assertRaises(RuntimeError):
            validate_auth_config()


class RoleTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(
            self.create_user("admin", "correct-horse-battery", "admin").status_code, 201
        )
        self.admin = self.bearer(self.login("admin", "correct-horse-battery"))
        self.admin_token = self.admin["Authorization"].split()[1]

    def test_bootstrap_creates_the_first_user_without_a_token(self):
        # Already exercised above: the first user was created with no token at
        # all. A *second* attempt without a token must not be allowed.
        response = self.create_user("sneaky", "another-password", "admin")
        self.assertEqual(response.status_code, 401)

    def test_viewer_may_read_but_not_act(self):
        self.create_user("viewer", "viewer-password-1", "viewer", token=self.admin_token)
        viewer = self.bearer(self.login("viewer", "viewer-password-1"))

        self.assertEqual(self.client.get("/api/targets", headers=viewer).status_code, 200)
        self.assertEqual(self.client.post("/api/targets", json={
            "name": "x", "address": "localhost", "target_type": "host",
        }, headers=viewer).status_code, 403)
        self.assertEqual(
            self.client.post("/api/targets/1/scans", headers=viewer).status_code, 403
        )

    def test_operator_may_assess_but_not_register_targets(self):
        self.create_user("analyst", "analyst-password", "operator",
                         token=self.admin_token)
        operator = self.bearer(self.login("analyst", "analyst-password"))

        target = self.client.post("/api/targets", json={
            "name": "Local lab", "address": "https://localhost:8443",
            "target_type": "web", "authorization_status": "authorized",
            "approved_scope": ["tls"], "approved_ports": [8443],
            "authorized_by": "researcher",
            "authorized_at": "2026-11-13T09:00:00Z",
            "authorization_basis": "LAB-2026-01",
        }, headers=self.admin)
        self.assertEqual(target.status_code, 201)

        self.assertEqual(self.client.post("/api/targets", json={
            "name": "x", "address": "localhost", "target_type": "host",
        }, headers=operator).status_code, 403)

        with mock.patch("driftguard.scanner.tools.run_testssl", return_value={
            "protocols": {"TLS1_2": True}, "cipher_issues": [],
            "cert": {"cert_commonName": "localhost"},
        }):
            scan = self.client.post(
                f"/api/targets/{target.json()['id']}/scans", headers=operator
            )
        self.assertEqual(scan.status_code, 201)


if __name__ == "__main__":
    unittest.main()
