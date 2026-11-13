import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from driftguard import models
from driftguard.database import Base
from driftguard.sync import load_lab_registry, sync_targets


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


class SyncTests(_DBTestCase):
    def test_loads_real_lab_registry_shape(self):
        registry = load_lab_registry(REPO_ROOT)
        self.assertIn("eservices-lab", registry)
        t = registry["eservices-lab"]
        self.assertEqual(t.base_url, "https://127.0.0.1:8443")
        self.assertEqual(tuple(t.approved_ports), (8443, 8080))
        self.assertEqual(tuple(t.drift_ports), (8081,))
        self.assertEqual(tuple(t.scope), ("tls", "network", "http_api"))
        self.assertTrue(any(s.name == "port-open" for s in t.scenarios))

    def test_sync_registers_targets_with_correct_fields_and_no_drift_ports(self):
        db = self.db()
        count = sync_targets(
            db,
            repo_root=REPO_ROOT,
            authorized_by="tester",
            authorized_at=datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc),
            authorization_basis="lab-eval",
        )
        db.commit()
        targets = list(db.scalars(select(models.Target).order_by(models.Target.name)))
        self.assertEqual(count, len(targets))
        es = next(t for t in targets if t.name == "eservices-lab")
        self.assertEqual(es.address, "https://127.0.0.1:8443")
        self.assertEqual(sorted(es.approved_ports), [8080, 8443])
        self.assertNotIn(8081, es.approved_ports)
        self.assertEqual(set(es.approved_scope), {"tls", "network", "http_api"})
        self.assertEqual(es.authorization_status, "authorized")
        self.assertEqual(es.authorized_by, "tester")
        self.assertEqual(es.authorization_basis, "lab-eval")
        self.assertIsNotNone(es.authorized_at)
        self.assertFalse(es.discovery_enabled)
        db.close()

    def test_sync_is_idempotent(self):
        db = self.db()
        sync_targets(db, repo_root=REPO_ROOT, authorized_by="t", authorization_basis="b")
        db.commit()
        first = list(db.scalars(select(models.Target).order_by(models.Target.id)))
        sync_targets(db, repo_root=REPO_ROOT, authorized_by="t", authorization_basis="b")
        db.commit()
        second = list(db.scalars(select(models.Target).order_by(models.Target.id)))
        self.assertEqual([t.id for t in first], [t.id for t in second])
        self.assertEqual(len(first), len(second))
        db.close()


if __name__ == "__main__":
    unittest.main()
