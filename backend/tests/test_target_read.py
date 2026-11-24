from datetime import datetime, timezone

from driftguard import models
from tests.support import ApiTestCase


class TargetReadTests(ApiTestCase):
    def test_pending_unscoped_target_reports_every_refusal_reason(self):
        target = self.create_target(approved_scope=[], approved_ports=[])
        body = self.client.get(f"/api/targets/{target['id']}").json()
        self.assertFalse(body["scannable"])
        self.assertIsNone(body["last_scan"])
        self.assertIn("target must be explicitly authorized", body["refusal_reasons"])
        self.assertIn("target has no approved assessment scope", body["refusal_reasons"])

    def test_authorized_scoped_target_is_scannable_with_no_reasons(self):
        target = self.create_target(
            authorization_status="authorized", authorized_by="A. Owner",
            authorized_at="2026-11-12T09:00:00Z", authorization_basis="LAB-2026-01",
        )
        body = self.client.get(f"/api/targets/{target['id']}").json()
        self.assertTrue(body["scannable"])
        self.assertEqual(body["refusal_reasons"], [])

    def test_last_scan_is_the_newest_attempt(self):
        target = self.create_target()
        db = self.factory()
        db.add(models.Scan(target_id=target["id"], status="completed"))
        db.add(models.Scan(target_id=target["id"], status="failed"))
        db.commit()
        body = self.client.get(f"/api/targets/{target['id']}").json()
        self.assertEqual(body["last_scan"]["status"], "failed")
        db.close()

    def test_target_list_includes_last_scan_for_each_target(self):
        first = self.create_target()
        second = self.create_target(name="Second")
        db = self.factory()
        db.add(models.Scan(target_id=first["id"], status="completed"))
        db.commit()
        db.close()
        rows = {row["id"]: row for row in self.client.get("/api/targets").json()}
        self.assertEqual(rows[first["id"]]["last_scan"]["status"], "completed")
        self.assertIsNone(rows[second["id"]]["last_scan"])
