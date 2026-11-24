from datetime import datetime, timezone

from driftguard import models
from tests.support import ApiTestCase


class HistoryTests(ApiTestCase):
    def _seed(self):
        target = self.create_target()
        db = self.factory()
        baseline = models.Scan(target_id=target["id"], status="completed", is_baseline=True)
        changed = models.Scan(target_id=target["id"], status="completed")
        failed = models.Scan(target_id=target["id"], status="failed")
        db.add_all([baseline, changed, failed])
        db.flush()
        fp = "eservices-lab/Network/port-open"
        db.add(models.Evidence(scan_id=baseline.id, fingerprint=fp, category="Network",
                               title="Unexpected open port", severity="High",
                               resource="8081", details={}))
        db.add(models.Evidence(scan_id=changed.id, fingerprint=fp, category="Network",
                               title="Unexpected open port", severity="High",
                               resource="8081", details={}))
        db.add(models.DriftEvent(target_id=target["id"], scan_id=changed.id,
                                 evidence_fingerprint=fp, classification="PERSISTENT"))
        db.commit()
        db.close()
        return target["id"], fp

    def test_history_returns_scans_newest_first_with_summaries(self):
        target_id, fp = self._seed()
        body = self.client.get(f"/api/targets/{target_id}/history").json()
        self.assertEqual([s["scan"]["status"] for s in body["scans"]],
                         ["failed", "completed", "completed"])
        self.assertEqual(body["scans"][0]["summary"]["state"], "INCOMPLETE")
        self.assertFalse(body["scans"][0]["comparable"])
        self.assertEqual(body["scans"][0]["drift"], [])
        self.assertEqual(body["scans"][1]["summary"]["state"], "CHANGED")
        self.assertEqual(body["scans"][1]["summary"]["counts"]["PERSISTENT"], 1)
        self.assertEqual(body["scans"][2]["summary"]["state"], "BASELINE")
        self.assertEqual(body["fingerprints"][fp]["severity"], "High")

    def test_comparable_scan_with_no_change_is_no_drift(self):
        target = self.create_target()
        db = self.factory()
        first = models.Scan(target_id=target["id"], status="completed", is_baseline=True)
        second = models.Scan(target_id=target["id"], status="completed")
        db.add_all([first, second])
        db.commit()
        db.close()
        body = self.client.get(f"/api/targets/{target['id']}/history").json()
        self.assertEqual(body["scans"][0]["summary"]["state"], "NO DRIFT")

    def test_history_is_scoped_to_the_target(self):
        first, _ = self._seed()
        second = self.create_target(name="Other", address="https://other.test:8444")
        body = self.client.get(f"/api/targets/{second['id']}/history").json()
        self.assertEqual(body["scans"], [])

    def test_history_rejects_unknown_target(self):
        self.assertEqual(self.client.get("/api/targets/9999/history").status_code, 404)

    def test_history_limit_is_clamped(self):
        target, _ = self._seed()
        self.assertEqual(self.client.get(f"/api/targets/{target}/history?limit=0").status_code, 422)
        self.assertEqual(self.client.get(f"/api/targets/{target}/history?limit=101").status_code, 422)