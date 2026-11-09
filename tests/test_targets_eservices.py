import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.targets import eservices


class EservicesTargetTests(unittest.TestCase):
    def test_declares_the_five_existing_scenarios(self):
        names = {s.name for s in eservices.TARGET.scenarios}
        self.assertEqual(
            names,
            {"tls-legacy", "cert-mismatch", "http-plain", "port-open", "api-debug"},
        )

    def test_state_is_read_from_the_existing_state_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text(json.dumps({"tls-legacy": True, "port-open": True}))
            with patch.object(eservices, "STATE_PATH", state_path):
                state = eservices.read_state()
        self.assertEqual(state["tls-legacy"], True)
        self.assertEqual(state["port-open"], True)
        self.assertEqual(state["cert-mismatch"], False)
        self.assertEqual(state["http-plain"], False)
        self.assertEqual(state["api-debug"], False)

    def test_apply_delegates_to_lab_py(self):
        previous = {
            "tls-legacy": False, "cert-mismatch": False, "http-plain": False,
            "port-open": False, "api-debug": False,
        }
        current = {
            "tls-legacy": True, "cert-mismatch": False, "http-plain": False,
            "port-open": True, "api-debug": False,
        }
        with patch("domain.targets.eservices.subprocess.run") as mock_run:
            eservices.apply(previous, current)
        argv_calls = [call.args[0] for call in mock_run.call_args_list]
        lab = str(eservices.LAB_PY)
        self.assertIn(["python3", lab, "on", "tls-legacy"], argv_calls)
        self.assertIn(["python3", lab, "on", "port-open"], argv_calls)
        self.assertEqual(len(argv_calls), 2)

    def test_nginx_config_is_not_reimplemented(self):
        self.assertIsNone(
            eservices.nginx_config({"tls-legacy": False, "cert-mismatch": False,
                                    "http-plain": False, "port-open": False,
                                    "api-debug": False})
        )


if __name__ == "__main__":
    unittest.main()
