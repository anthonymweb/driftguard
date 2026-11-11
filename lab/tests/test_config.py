import unittest

from domain import config


class RegistryTests(unittest.TestCase):
    def test_eservices_is_registered(self):
        self.assertIn("eservices-lab", config.TARGETS)
        self.assertIs(config.get("eservices-lab"), config.TARGETS["eservices-lab"])

    def test_registry_never_lists_drift_ports_as_approved(self):
        for target in config.TARGETS.values():
            self.assertEqual(set(target.drift_ports) & set(target.approved_ports), set())

    def test_every_registered_target_has_all_three_areas(self):
        for target in config.TARGETS.values():
            self.assertEqual({s.area for s in target.scenarios}, {"TLS", "Network", "API"})


if __name__ == "__main__":
    unittest.main()
