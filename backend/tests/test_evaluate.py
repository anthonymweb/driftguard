import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from evaluate import evaluate


def planted_eservices():
    # target -> scenario -> area
    return {"eservices-lab": {"tls-legacy": "TLS", "cert-mismatch": "TLS", "http-plain": "Network",
                              "port-open": "Network", "api-debug": "API"}}


class EvaluateTests(unittest.TestCase):
    def test_present_scenario_with_matching_finding_is_detection(self):
        # truth_matrix: target -> scenario -> [label per scan]
        truth = {"eservices-lab": {"tls-legacy": ["NO DRIFT", "NEW"]}}
        evidence = {"S1": ["eservices-lab/TLS/tls-legacy"]}
        scan_labels = ["S0", "S1"]
        report = evaluate(truth, evidence, scan_labels, planted_eservices())
        area = report["per_target"]["eservices-lab"]["per_area"]["TLS"]
        self.assertEqual(area["detections"], 1)
        self.assertEqual(area["present_total"], 1)
        self.assertEqual(area["false_positives"], 0)

    def test_absent_scenario_with_finding_is_false_positive(self):
        truth = {"eservices-lab": {"tls-legacy": ["NO DRIFT", "NO DRIFT"]}}
        evidence = {"S1": ["eservices-lab/TLS/tls-legacy"]}
        scan_labels = ["S0", "S1"]
        report = evaluate(truth, evidence, scan_labels, planted_eservices())
        area = report["per_target"]["eservices-lab"]["per_area"]["TLS"]
        self.assertEqual(area["detections"], 0)
        self.assertEqual(area["present_total"], 0)
        self.assertEqual(area["false_positives"], 1)

    def test_finding_on_never_planted_scenario_is_false_positive(self):
        truth = {"eservices-lab": {"tls-legacy": ["NO DRIFT"]}}
        evidence = {"S0": ["eservices-lab/API/other-thing"]}
        scan_labels = ["S0"]
        report = evaluate(truth, evidence, scan_labels, planted_eservices())
        self.assertEqual(report["per_target"]["eservices-lab"]["per_area"]["API"]["false_positives"], 1)

    def test_ground_truth_scan_with_no_engine_scan_is_unmeasured_not_miss(self):
        truth = {"eservices-lab": {"tls-legacy": ["NO DRIFT", "NEW"]}}
        evidence = {}
        scan_labels = ["S0", "S1"]
        report = evaluate(truth, evidence, scan_labels, planted_eservices())
        area = report["per_target"]["eservices-lab"]["per_area"]["TLS"]
        self.assertEqual(area["unmeasured_scans"], 2)
        self.assertEqual(area["present_total"], 0)
        self.assertEqual(area["detections"], 0)
        self.assertEqual(area["misses"], 0)

    def test_down_target_not_scored(self):
        truth = {"eservices-lab": {"tls-legacy": [None, "NEW"]}}
        evidence = {"S1": ["eservices-lab/TLS/tls-legacy"]}
        scan_labels = ["S0", "S1"]
        report = evaluate(truth, evidence, scan_labels, planted_eservices())
        area = report["per_target"]["eservices-lab"]["per_area"]["TLS"]
        self.assertEqual(area["detections"], 1)
        self.assertEqual(area["present_total"], 1)
        self.assertEqual(area["unmeasured_scans"], 0)


if __name__ == "__main__":
    unittest.main()
