import unittest
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard import models
from driftguard.database import Base, get_db, get_session_factory
from driftguard.main import app


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)

        def override_db():
            db = self.factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_session_factory] = lambda: self.factory
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def create_target(self, **overrides):
        payload = {
            "name": "Local lab", "address": "https://localhost:8443", "target_type": "web",
            "approved_scope": ["tls"], "approved_ports": [8443],
        }
        payload.update(overrides)
        response = self.client.post("/api/targets", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()
