import unittest

from driftguard.drift import classify


class DriftClassificationTests(unittest.TestCase):
    def test_new_finding(self):
        self.assertEqual(classify({"a"}, set(), []), {"a": "NEW"})

    def test_persistent_finding(self):
        self.assertEqual(classify({"a"}, {"a"}, []), {"a": "PERSISTENT"})

    def test_fixed_finding(self):
        self.assertEqual(classify(set(), {"a"}, [{"a"}]), {"a": "FIXED"})

    def test_recurring_finding(self):
        self.assertEqual(classify({"a"}, set(), [{"a"}, set()]), {"a": "RECURRING"})

    def test_no_drift_has_no_fingerprint_event(self):
        self.assertEqual(classify({"a"}, {"a"}, [{"a"}]), {"a": "PERSISTENT"})
        self.assertFalse(classify(set(), set(), []))


if __name__ == "__main__":
    unittest.main()
