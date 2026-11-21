"""Politeness: scan requests are bounded and rate-limited per client.

The plan's safety paragraph requires the engine to be polite — bounded timeouts
and a limited request rate. This covers the API side of that: a client may not
queue assessments in an unbounded burst.
"""
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard.database import Base, get_db, get_session_factory
from driftguard.main import app


class ScanRateLimitTests(unittest.TestCase):
    def setUp(self):
        self._reset_limiter()
        self._saved_limit = os.environ.get("DRIFTGUARD_SCAN_RATE_LIMIT")
        os.environ["DRIFTGUARD_SCAN_RATE_LIMIT"] = "2/minute"
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
        # A pending target is refused before any assessment is queued, so the
        # burst below exercises the rate limiter without launching scans.
        target = self.client.post("/api/targets", json={
            "name": "Local lab", "address": "https://localhost:8443", "target_type": "web",
            "approved_scope": ["tls"], "approved_ports": [8443],
        })
        assert target.status_code == 201, target.text
        self.scans_url = f"/api/targets/{target.json()['id']}/scans"

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self._reset_limiter()
        if self._saved_limit is None:
            os.environ.pop("DRIFTGUARD_SCAN_RATE_LIMIT", None)
        else:
            os.environ["DRIFTGUARD_SCAN_RATE_LIMIT"] = self._saved_limit

    @staticmethod
    def _reset_limiter():
        limiter = getattr(app.state, "limiter", None)
        if limiter is not None:
            limiter.reset()

    def test_burst_over_the_limit_is_refused_with_retry_after(self):
        responses = [self.client.post(self.scans_url) for _ in range(3)]
        # The pending target is refused, but every request still counts against
        # the limit; the third crosses it.
        self.assertEqual([r.status_code for r in responses[:2]], [403, 403])
        self.assertEqual(responses[2].status_code, 429)
        self.assertIn("Retry-After", responses[2].headers)

    def test_the_limit_is_configurable(self):
        os.environ["DRIFTGUARD_SCAN_RATE_LIMIT"] = "100/minute"
        statuses = [self.client.post(self.scans_url).status_code for _ in range(10)]
        self.assertEqual(statuses, [403] * 10)


if __name__ == "__main__":
    unittest.main()
