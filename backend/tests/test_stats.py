from driftguard import models
from tests.support import ApiTestCase


class StatsTests(ApiTestCase):
    def test_stats_counts_and_mode(self):
        target = self.create_target()
        db = self.factory()
        scan = models.Scan(target_id=target["id"], status="completed")
        db.add(scan)
        db.flush()
        db.add(models.Evidence(scan_id=scan.id, fingerprint="t/TLS/x", category="TLS",
                               title="x", severity="Low", resource="r", details={}))
        db.add(models.DriftEvent(target_id=target["id"], scan_id=scan.id,
                                 evidence_fingerprint="t/TLS/x", classification="NEW"))
        db.commit()
        db.close()
        body = self.client.get("/api/stats").json()
        self.assertEqual(body["targets"], 1)
        self.assertEqual(body["scans"], 1)
        self.assertEqual(body["evidence"], 1)
        self.assertEqual(body["drift_events"], 1)
        self.assertEqual(body["auth_mode"], "local_research")
        self.assertTrue(body["redaction"]["enabled"])