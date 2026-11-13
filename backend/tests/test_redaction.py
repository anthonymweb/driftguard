import unittest
import copy

from driftguard.redaction import redact


SEEDED = [
    "TEST-0001",
    "CMTEST00000001",
    "+256700000001",
    "10.20.0.0/24",
    "lab-demo-key",
    "eservices.test",
    "*.eservices.test",
]


def _collect_strings(obj):
    found = []
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            found.extend(_collect_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_collect_strings(v))
    return found


class RedactionTests(unittest.TestCase):
    def test_seeded_identifiers_do_not_survive_redaction(self):
        payload = {
            "endpoint": "https://api.eservices.test/debug?key=lab-demo-key",
            "connection": "postgres://user:pass@10.20.0.1:5432/app",
            "record": {
                "reference": "TEST-0001",
                "national_id": "CMTEST00000001",
                "phone": "+256700000001",
                "network": "10.20.0.0/24",
                "host": "portal.eservices.test",
                "wildcard": "*.eservices.test",
            },
            "items": [
                {"email": "admin@eservices.test", "note": "call +256700000001 now"},
                "CMTEST00000001",
            ],
        }
        tokenised, token_map = redact(copy.deepcopy(payload))
        blob = "\n".join(_collect_strings(tokenised))
        for identifier in SEEDED:
            with self.subTest(identifier=identifier):
                self.assertNotIn(identifier, blob)
        # map must account for originals seen
        self.assertTrue(token_map)
        self.assertNotIn("TEST-0001", blob)

    def test_nested_dicts_and_lists_are_redacted(self):
        payload = {
            "outer": [
                {"inner": {"ip": "203.0.113.5", "url": "https://example.test/path"}},
                ["user@example.test"],
            ]
        }
        tokenised, _ = redact(payload)
        blob = "\n".join(_collect_strings(tokenised))
        for leaked in ["203.0.113.5", "example.test", "user@example.test", "https://example.test/path"]:
            self.assertNotIn(leaked, blob)
        self.assertIsInstance(tokenised["outer"], list)
        self.assertIsInstance(tokenised["outer"][0]["inner"], dict)

    def test_value_containing_sensitive_part_tokenised_as_whole(self):
        payload = {
            "url": "https://api.eservices.test/v1/records/TEST-0001",
            "conn": "postgres://user:secret@db.eservices.test:5432/app",
            "mixed": "contact admin@eservices.test about TEST-0001",
        }
        tokenised, token_map = redact(payload)
        # whole strings replaced, not partially readable
        self.assertNotIn("eservices.test", tokenised["url"])
        self.assertNotIn("TEST-0001", tokenised["url"])
        self.assertNotIn("/v1/records/", tokenised["url"])
        self.assertNotIn("postgres://", tokenised["conn"])
        self.assertNotIn("admin@eservices.test", tokenised["mixed"])
        # tokens present instead
        self.assertRegex(tokenised["url"], r"^[A-Z]+_[0-9a-f]+$")
        self.assertRegex(tokenised["conn"], r"^[A-Z]+_[0-9a-f]+$")
        # originals are keys in map -> their token
        self.assertEqual(token_map[payload["url"]], tokenised["url"])
        self.assertEqual(token_map[payload["conn"]], tokenised["conn"])

    def test_same_value_same_token_different_values_different_tokens(self):
        payload = {
            "a": "TEST-0001",
            "b": "TEST-0001",
            "c": "CMTEST00000001",
            "nested": {"d": "TEST-0001"},
        }
        tokenised, _ = redact(payload)
        self.assertEqual(tokenised["a"], tokenised["b"])
        self.assertEqual(tokenised["a"], tokenised["nested"]["d"])
        self.assertNotEqual(tokenised["a"], tokenised["c"])

    def test_tokens_not_reversible_from_token_alone(self):
        payload = {"id": "TEST-0001", "host": "api.eservices.test", "key": "lab-demo-key"}
        tokenised, _ = redact(payload)
        for orig, tok in [("TEST-0001", tokenised["id"]), ("api.eservices.test", tokenised["host"]), ("lab-demo-key", tokenised["key"])]:
            self.assertNotIn(orig, tok)
            self.assertNotEqual(orig, tok)
            # token is a compact label, not an encoding of the value
            self.assertRegex(tok, r"^[A-Z]+_[0-9a-f]{6,}$")

    def test_non_sensitive_values_preserved(self):
        payload = {"count": 3, "ok": True, "name": "status", "meta": {"severity": "high"}}
        tokenised, token_map = redact(payload)
        self.assertEqual(tokenised, payload)
        self.assertEqual(token_map, {})


if __name__ == "__main__":
    unittest.main()

from tempfile import TemporaryDirectory
from unittest import mock
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from driftguard import models
from driftguard.database import Base, get_db, get_session_factory
from driftguard.main import app
from driftguard.redaction import redact, secret_path, _load_or_create_secret


class SecretStorageTests(unittest.TestCase):
    def test_secret_generated_once_and_stable_in_installation(self):
        with TemporaryDirectory() as tmp:
            sp = os.path.join(tmp, ".driftguard_redaction_secret")
            with mock.patch.dict(os.environ, {"DRIFTGUARD_REDACTION_SECRET_PATH": sp}):
                import driftguard.redaction as r
                r._secret_cache = None
                s1 = _load_or_create_secret()
                self.assertTrue(os.path.isfile(sp))
                mode = os.stat(sp).st_mode & 0o777
                self.assertEqual(mode, 0o600)
                r._secret_cache = None
                s2 = _load_or_create_secret()
                self.assertEqual(s1, s2)
                # tokens stable within installation
                t1, _ = redact({"h": "api.eservices.test"})
                t2, _ = redact({"h": "api.eservices.test"})
                self.assertEqual(t1, t2)
                r._secret_cache = None

    def test_fresh_installation_produces_different_secret(self):
        with TemporaryDirectory() as a, TemporaryDirectory() as b:
            import driftguard.redaction as r
            with mock.patch.dict(os.environ, {"DRIFTGUARD_REDACTION_SECRET_PATH": os.path.join(a, "s")}):
                r._secret_cache = None
                sa = _load_or_create_secret()
            with mock.patch.dict(os.environ, {"DRIFTGUARD_REDACTION_SECRET_PATH": os.path.join(b, "s")}):
                r._secret_cache = None
                sb = _load_or_create_secret()
            self.assertNotEqual(sa, sb)
            r._secret_cache = None


class RedactionApiBoundaryTests(unittest.TestCase):
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
        app.dependency_overrides[get_session_factory] = lambda: factory
        self.client = TestClient(app)
        # seed evidence with sensitive lab identifiers
        db = factory()
        target = models.Target(
            name="svc", address="https://api.eservices.test:8443", target_type="web",
            authorization_status="authorized", authorized_by="a", 
            authorized_at=__import__("datetime").datetime(2026,1,1,tzinfo=__import__("datetime").timezone.utc),
            authorization_basis="b", approved_scope=["http_api"], approved_ports=[8443], status="active",
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        scan = models.Scan(target_id=target.id, status="completed")
        db.add(scan)
        db.commit()
        db.refresh(scan)
        self.scan_id = scan.id
        db.add(models.Evidence(
            scan_id=scan.id, fingerprint="fp1", category="http", title="Debug at api.eservices.test",
            severity="high", resource="https://api.eservices.test/debug?key=lab-demo-key",
            details={
                "host": "api.eservices.test",
                "id": "TEST-0001",
                "nid": "CMTEST00000001",
                "phone": "+256700000001",
                "net": "10.20.0.0/24",
                "nested": {"email": "admin@eservices.test", "items": ["*.eservices.test"]},
            },
        ))
        db.commit()
        db.close()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp.cleanup()

    def test_redacted_evidence_endpoint_hides_sensitive_values(self):
        resp = self.client.get(f"/api/scans/{self.scan_id}/evidence/redacted")
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        for ident in SEEDED:
            self.assertNotIn(ident, body)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertNotIn("api.eservices.test", data[0]["resource"])
        self.assertNotIn("api.eservices.test", data[0]["title"])
        self.assertNotIn("TEST-0001", str(data[0]["details"]))

    def test_token_map_never_exposed_by_api(self):
        # redacted endpoint
        resp = self.client.get(f"/api/scans/{self.scan_id}/evidence/redacted")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("token_map", resp.text.lower())
        self.assertNotIn("tokenmap", resp.text.lower())
        # no endpoint should return map; probe common paths
        for path in ["/api/redaction/map", "/api/token-map", "/api/scans/%d/token_map" % self.scan_id]:
            r = self.client.get(path)
            self.assertIn(r.status_code, (404, 405), path)
            self.assertNotIn("TEST-0001", r.text)  # never leak originals via such route
