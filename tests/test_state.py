# tests/test_state.py
import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from domain import state
from domain.classify import classify
from domain.model import Scenario, Target
from domain.state import GroundTruthRow, ScanRecord

COLUMNS = ["timestamp_utc", "target", "event", "scenario", "action",
           "category", "expected_finding", "finding_key", "state_after"]


def make_target(scenarios):
    return Target(name="eservices-lab", base_url="https://127.0.0.1:8443",
                  http_base_url="http://127.0.0.1:8080", approved_ports=(8443, 8080),
                  drift_ports=(8081,), scope=("tls", "network", "http_api"),
                  scenarios=scenarios)


def make_row(**overrides):
    values = dict(timestamp_utc="2026-11-09T00:00:00Z", target="eservices-lab",
                  event="change", scenario="tls-legacy", action="introduced",
                  category="TLS", expected_finding="Legacy TLS 1.0/1.1 accepted",
                  finding_key="eservices-lab/TLS/tls-legacy",
                  state_after='{"tls-legacy": true}')
    values.update(overrides)
    return GroundTruthRow(**values)


class StateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for attr, filename in (("GROUND_TRUTH_PATH", "ground_truth.csv"),
                               ("SCANS_PATH", "scans.json")):
            patcher = mock.patch.object(state, attr, self.root / filename)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_read_state_missing_file_returns_all_false(self):
        path = self.root / "state.json"  # never written
        self.assertEqual(state.read_state(path, ["tls-legacy", "http-plain"]),
                         {"tls-legacy": False, "http-plain": False})

    def test_write_then_read_roundtrips(self):
        path = self.root / "state.json"
        original = {"tls-legacy": True, "cert-mismatch": False, "http-plain": True}
        state.write_state(path, original)
        self.assertEqual(state.read_state(path, list(original)), original)

    def test_ground_truth_header_is_written_once_with_finding_key_column(self):
        state.append_ground_truth(make_row())
        state.append_ground_truth(make_row(action="remediated",
                                           state_after='{"tls-legacy": false}'))
        with state.GROUND_TRUTH_PATH.open(newline="") as f:
            rows = list(csv.reader(f))
        self.assertEqual(state.GROUND_TRUTH_COLUMNS, COLUMNS)  # the frozen schema
        self.assertEqual(rows[0], COLUMNS)                     # header incl. finding_key
        self.assertEqual(len(rows), 3)                         # written once, not per row

    def test_ground_truth_row_writes_finding_key(self):
        target = make_target((Scenario(name="tls-legacy", area="TLS",
                                       expected_finding="Legacy TLS 1.0/1.1 accepted"),))
        state.append_ground_truth(make_row(finding_key=target.finding_key("tls-legacy")))
        with state.GROUND_TRUTH_PATH.open(newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["finding_key"], "eservices-lab/TLS/tls-legacy")

    def test_record_scan_persists_down_target_as_none(self):
        state.record_scan("S1", {"eservices-lab": {"tls-legacy": True}, "juice-shop": None})
        state.record_scan("S2", {"eservices-lab": {"tls-legacy": False}, "juice-shop": None})
        scans = state.read_scans()
        self.assertEqual(len(scans), 2)  # file created as [] then appended to
        self.assertIsInstance(scans[0], ScanRecord)
        self.assertEqual(scans[0].label, "S1")
        self.assertRegex(scans[0].timestamp_utc, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertIsNone(scans[0].states["juice-shop"])
        self.assertEqual(scans[1].states["eservices-lab"], {"tls-legacy": False})

    def test_truth_matrix_marks_down_target_as_none(self):
        target = make_target((Scenario(name="tls-legacy", area="TLS",
                                       expected_finding="Legacy TLS 1.0/1.1 accepted"),))
        scans = [
            ScanRecord(label="S1", timestamp_utc="2026-11-09T00:00:01Z",
                       states={"eservices-lab": {"tls-legacy": False}}),
            ScanRecord(label="S2", timestamp_utc="2026-11-09T00:00:02Z",
                       states={"eservices-lab": None}),  # target down
            ScanRecord(label="S3", timestamp_utc="2026-11-09T00:00:03Z",
                       states={"eservices-lab": {"tls-legacy": False}}),
        ]
        matrix = state.truth_matrix({"eservices-lab": target}, scans)
        # down at scan 2 → that label position is None, not "NO DRIFT"
        self.assertEqual(matrix["eservices-lab"]["tls-legacy"],
                         ["NO DRIFT", None, "NO DRIFT"])

    def test_truth_matrix_matches_classify_for_a_live_target(self):
        tls_history = [False, True, True, False, True, True, True, True, True]
        http_history = [False, False, True, True, True, True, False, True, True]
        target = make_target((
            Scenario(name="tls-legacy", area="TLS",
                     expected_finding="Legacy TLS 1.0/1.1 accepted"),
            Scenario(name="http-plain", area="Network",
                     expected_finding="Application served over plain HTTP, no redirect"),
        ))
        scans = [ScanRecord(label=f"S{i + 1}", timestamp_utc=f"2026-11-09T00:00:{i:02d}Z",
                            states={"eservices-lab": {"tls-legacy": t, "http-plain": h}})
                 for i, (t, h) in enumerate(zip(tls_history, http_history))]
        matrix = state.truth_matrix({"eservices-lab": target}, scans)["eservices-lab"]
        self.assertEqual(matrix["tls-legacy"], classify(tls_history))
        self.assertEqual(matrix["tls-legacy"],
                         ["NO DRIFT", "NEW", "PERSISTENT", "FIXED", "RECURRING",
                          "PERSISTENT", "PERSISTENT", "PERSISTENT", "PERSISTENT"])
        self.assertEqual(matrix["http-plain"], classify(http_history))
        self.assertEqual(matrix["http-plain"],
                         ["NO DRIFT", "NO DRIFT", "NEW", "PERSISTENT", "PERSISTENT",
                          "PERSISTENT", "FIXED", "RECURRING", "PERSISTENT"])

    def test_row_writer_rejects_an_unknown_area(self):
        with self.assertRaises(ValueError):
            make_row(category="TSL", finding_key="eservices-lab/TSL/tls-legacy")

    def test_row_writer_rejects_finding_key_disagreeing_with_columns(self):
        # key names the wrong scenario for the row's own target/category/scenario.
        with self.assertRaises(ValueError):
            make_row(scenario="tls-legacy", category="TLS",
                     finding_key="eservices-lab/TLS/cert-mismatch")
        # key names the wrong target.
        with self.assertRaises(ValueError):
            make_row(target="juice-shop", scenario="tls-legacy", category="TLS",
                     finding_key="eservices-lab/TLS/tls-legacy")
        # key names the wrong area.
        with self.assertRaises(ValueError):
            make_row(scenario="tls-legacy", category="TLS",
                     finding_key="eservices-lab/Network/tls-legacy")

    def test_row_writer_accepts_well_formed_scenario_row(self):
        row = make_row(target="juice-shop", scenario="api-debug", category="API",
                       expected_finding="Admin API endpoint publicly reachable",
                       finding_key="juice-shop/API/api-debug")
        self.assertEqual(row.finding_key, "juice-shop/API/api-debug")


if __name__ == "__main__":
    unittest.main()
