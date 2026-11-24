from datetime import datetime, timezone
from unittest import mock

from driftguard import models
from tests.support import ApiTestCase


class EvaluationApiTests(ApiTestCase):
    def test_unavailable_ground_truth_is_reported_without_numbers(self):
        with mock.patch("driftguard.evaluation_service.load_lab_truth",
                        side_effect=FileNotFoundError("lab ground truth missing")):
            body = self.client.get("/api/evaluation").json()
        self.assertFalse(body["available"])
        self.assertIn("lab ground truth missing", body["reason"])
        self.assertIsNone(body.get("overall"))

    def test_duplicate_completed_labels_block_evaluation(self):
        target = self.create_target()
        db = self.factory()
        db.add_all([
            models.Scan(target_id=target["id"], status="completed", label="S1"),
            models.Scan(target_id=target["id"], status="completed", label="S1"),
        ])
        db.commit()
        db.close()
        with mock.patch("driftguard.evaluation_service.load_lab_truth") as truth:
            truth.return_value = ([], {}, {})
            body = self.client.get("/api/evaluation").json()
        self.assertFalse(body["available"])
        self.assertIn("S1", body["duplicates"])

    def test_evaluation_is_read_only(self):
        target = self.create_target()
        db = self.factory()
        db.add(models.Scan(target_id=target["id"], status="completed", label="S1"))
        db.commit()
        before = (db.query(models.Scan).count(), db.query(models.Evidence).count(),
                  db.query(models.DriftEvent).count())
        db.close()
        with mock.patch("driftguard.evaluation_service.load_lab_truth",
                        side_effect=FileNotFoundError("missing")):
            self.client.get("/api/evaluation")
        db = self.factory()
        after = (db.query(models.Scan).count(), db.query(models.Evidence).count(),
                 db.query(models.DriftEvent).count())
        db.close()
        self.assertEqual(before, after)