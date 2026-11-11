import json
import unittest
from unittest.mock import patch

import sequence


class SequenceTests(unittest.TestCase):
    def test_supported_scenarios_refuses_when_a_target_is_down(self):
        status = {
            "targets": {
                "eservices-lab": {"tls-legacy": False},
                "juice-shop": "DOWN",
            }
        }
        completed = type("CP", (), {"stdout": json.dumps(status), "returncode": 0})()
        with patch("sequence.run", return_value=completed):
            with self.assertRaises(SystemExit) as ctx:
                sequence.supported_scenarios()
        message = str(ctx.exception)
        self.assertIn("juice-shop", message)
        self.assertIn("DOWN", message)
        self.assertIn("domain.py up", message)

    def test_run_fails_loudly_on_nonzero_exit(self):
        completed = type("CP", (), {"stdout": "", "stderr": "boom", "returncode": 2})()
        with patch("sequence.subprocess.run", return_value=completed):
            with self.assertRaises(SystemExit) as ctx:
                sequence.run("status", "--json", capture=True)
        self.assertIn("exit 2", str(ctx.exception))
        self.assertIn("boom", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
