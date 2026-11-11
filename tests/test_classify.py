# tests/test_classify.py
import importlib.util
import unittest

from domain import ROOT
from domain.classify import classify

BACKEND_DRIFT = ROOT / "eservices-lab" / "backend" / "driftguard" / "drift.py"

HISTORIES = [
    [False, True, True, False, True, True, True, True, True],
    [False, False, True, True, True, True, False, True, True],
    [False, False, False, True, True, True, False, False, True],
    [False, False, False, False, False, True, False, True, True],
]


class ClassifyTests(unittest.TestCase):
    def test_tls_area_nine_scan_sequence(self):
        history = [False, True, True, False, True, True, True, True, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NEW", "PERSISTENT", "FIXED", "RECURRING",
            "PERSISTENT", "PERSISTENT", "PERSISTENT", "PERSISTENT"])

    def test_http_plain_nine_scan_sequence(self):
        history = [False, False, True, True, True, True, False, True, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NO DRIFT", "NEW", "PERSISTENT", "PERSISTENT",
            "PERSISTENT", "FIXED", "RECURRING", "PERSISTENT"])

    def test_port_open_nine_scan_sequence(self):
        history = [False, False, False, True, True, True, False, False, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NO DRIFT", "NO DRIFT", "NEW", "PERSISTENT",
            "PERSISTENT", "FIXED", "NO DRIFT", "RECURRING"])

    def test_api_debug_nine_scan_sequence(self):
        history = [False, False, False, False, False, True, False, True, True]
        self.assertEqual(classify(history), [
            "NO DRIFT", "NO DRIFT", "NO DRIFT", "NO DRIFT", "NO DRIFT",
            "NEW", "FIXED", "RECURRING", "PERSISTENT"])

    def test_first_scan_present_is_baseline(self):
        self.assertEqual(classify([True]), ["BASELINE"])

    def test_labels_are_within_the_frozen_set(self):
        labels = set(classify([False, True, True, False, True, True, False, True, True]))
        self.assertTrue(labels <= {"BASELINE", "NEW", "PERSISTENT", "FIXED", "RECURRING", "NO DRIFT"})

    def test_agrees_with_driftguard_backend_classifier(self):
        """The evaluation compares ground truth (this module) against the
        backend's evidence classifier. They must not disagree."""
        # Load eservices-lab/backend/driftguard/drift.py by path (stdlib imports only),
        # then for every index i >= 1 compare:
        #   domain label  vs  backend.classify(current, previous, earlier).get(F, "NO DRIFT")
        # where current/previous/earlier are {F} or set() built from the history.
        spec = importlib.util.spec_from_file_location("driftguard_drift", BACKEND_DRIFT)
        drift = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(drift)
        fingerprint = "f"
        for history in HISTORIES:
            labels = classify(history)
            for i in range(1, len(history)):
                current = {fingerprint} if history[i] else set()
                previous = {fingerprint} if history[i - 1] else set()
                earlier = [{fingerprint} if h else set() for h in history[:i - 1]]
                backend = drift.classify(current, previous, earlier).get(fingerprint, "NO DRIFT")
                self.assertEqual(
                    labels[i], backend,
                    f"disagreement at index {i} of history {history}: "
                    f"domain={labels[i]!r} backend={backend!r}")
