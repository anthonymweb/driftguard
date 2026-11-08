# tests/test_model.py
import dataclasses
import unittest

from domain.model import AREA_LABELS, Scenario, Target


class ModelTests(unittest.TestCase):
    def test_area_labels_cover_exactly_the_three_audit_areas(self):
        self.assertEqual(AREA_LABELS, {"TLS": "TLS/SSL", "Network": "Network/Service", "API": "API"})

    def test_scenario_is_frozen(self):
        s = Scenario(name="tls-legacy", area="TLS", expected_finding="Legacy TLS 1.0/1.1 accepted")
        self.assertRaises(dataclasses.FrozenInstanceError, setattr, s, "name", "other")

    def test_finding_key_uses_the_frozen_format(self):
        t = Target(name="eservices-lab", base_url="https://127.0.0.1:8443",
                   http_base_url="http://127.0.0.1:8080", approved_ports=(8443, 8080),
                   drift_ports=(8081,), scope=("tls", "network", "http_api"),
                   scenarios=(Scenario(name="tls-legacy", area="TLS", expected_finding="x"),))
        self.assertEqual(t.finding_key("tls-legacy"), "eservices-lab/TLS/tls-legacy")

    def test_finding_key_rejects_unknown_scenario(self):
        t = Target(name="eservices-lab", base_url="https://127.0.0.1:8443",
                   http_base_url="http://127.0.0.1:8080", approved_ports=(8443, 8080),
                   drift_ports=(8081,), scope=("tls", "network", "http_api"),
                   scenarios=(Scenario(name="tls-legacy", area="TLS", expected_finding="x"),))
        self.assertRaises(KeyError, t.finding_key, "nope")
