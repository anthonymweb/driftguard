import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.targets import civicportal as module

NAMES = [s.name for s in module.TARGET.scenarios]


class CivicPortalTargetTests(unittest.TestCase):
    def test_declares_three_scenarios(self):
        self.assertEqual(set(NAMES), {"tls-legacy", "port-open", "api-debug"})

    def test_target_metadata(self):
        self.assertEqual(module.TARGET.name, "civic-services-portal")
        self.assertEqual(module.TARGET.base_url, "https://127.0.0.1:8445")
        self.assertEqual(module.TARGET.http_base_url, "http://127.0.0.1:8083")
        self.assertEqual(module.TARGET.approved_ports, (8445, 8083))
        self.assertEqual(module.TARGET.drift_ports, (8084,))

    def test_approved_ports_exclude_drift_port(self):
        self.assertNotIn(8084, module.TARGET.approved_ports)
        self.assertIn(8084, module.TARGET.drift_ports)


class CivicPortalRenderTests(unittest.TestCase):
    def test_baseline_blocks_legacy_tls(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", cfg)
        self.assertNotIn("TLSv1 ", cfg)

    def test_tls_legacy_enables_legacy_protocols_and_seclevel_zero(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "tls-legacy": True})
        self.assertIn("TLSv1 ", cfg)
        self.assertIn("@SECLEVEL=0", cfg)

    def test_baseline_blocks_the_debug_endpoint(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("location = /api/v1/admin/debug { return 403; }", cfg)

    def test_api_debug_proxies_the_debug_endpoint(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "api-debug": True})
        self.assertNotIn("location = /api/v1/admin/debug { return 403; }", cfg)
        self.assertIn("location = /api/v1/admin/debug", cfg)
        self.assertIn("proxy_pass http://api/api/v1/admin/debug;", cfg)
        self.assertNotIn("proxy_pass http://api:5000/", cfg)

    def test_rendered_config_contains_no_http_api_port_reference(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "api-debug": True})
        self.assertNotIn("http://api:", cfg)

    def test_no_placeholder_survives_rendering(self):
        for state in ({s: False for s in NAMES}, {s: True for s in NAMES}):
            cfg = module.nginx_config(state)
            self.assertNotIn("{{", cfg)

    def test_port_open_override_publishes_the_raw_api_port(self):
        content = module.OVERRIDE_PATH.read_text()
        self.assertIn("127.0.0.1:8084:5000", content)


class CivicPortalApplyTests(unittest.TestCase):
    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    @patch("domain.targets.civicportal.compose.recreate")
    @patch("domain.targets.civicportal._drift_port_published", return_value=False)
    def test_apply_writes_config_and_reloads(self, mock_published, mock_recreate, mock_write, mock_reload, mock_validate):
        state = {s: False for s in NAMES}
        module.apply(state, state)
        mock_write.assert_called_once()
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)
        mock_recreate.assert_not_called()

    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    @patch("domain.targets.civicportal.compose.recreate")
    @patch("domain.targets.civicportal._drift_port_published", return_value=False)
    def test_apply_enables_port_open_uses_override(self, mock_published, mock_recreate, mock_write, mock_reload, mock_validate):
        previous = {s: False for s in NAMES}
        current = {**previous, "port-open": True}
        module.apply(previous, current)
        mock_recreate.assert_called_once_with(module.COMPOSE_FILE, module.OVERRIDE_PATH)
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    @patch("domain.targets.civicportal.compose.recreate")
    @patch("domain.targets.civicportal._drift_port_published", return_value=True)
    def test_apply_disables_port_open_recreates_without_override(self, mock_published, mock_recreate, mock_write, mock_reload, mock_validate):
        previous = {**{s: False for s in NAMES}, "port-open": True}
        current = {s: False for s in NAMES}
        module.apply(previous, current)
        mock_recreate.assert_called_once_with(module.COMPOSE_FILE, None)
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    @patch("domain.targets.civicportal.compose.recreate")
    @patch("domain.targets.civicportal._drift_port_published", return_value=True)
    def test_apply_withdraws_the_port_when_the_recorded_state_disagrees_with_reality(
            self, mock_published, mock_recreate, mock_write, mock_reload, mock_validate):
        # The recorded state says the port is closed but the port is still
        # published: the apply must repair that, not trust the record.
        previous = {s: False for s in NAMES}
        current = {s: False for s in NAMES}
        module.apply(previous, current)
        mock_recreate.assert_called_once_with(module.COMPOSE_FILE, None)

    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    def test_apply_reloads_correct_compose_path(self, mock_write, mock_reload, mock_validate):
        module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        self.assertEqual(
            mock_reload.call_args[0][0],
            module.ROOT / "civic-services-portal/deploy/compose.yaml",
        )

    @patch("domain.targets.civicportal.state.write_state")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal._write_config")
    def test_apply_validates_before_reload(self, mock_write, mock_validate, mock_reload, mock_persist):
        order = []
        mock_write.side_effect = lambda *_: order.append("write")
        mock_validate.side_effect = lambda *_: order.append("validate")
        mock_reload.side_effect = lambda *_: order.append("reload")
        mock_persist.side_effect = lambda *_: order.append("persist")
        module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        self.assertEqual(order, ["write", "validate", "reload", "persist"])

    @patch("domain.targets.civicportal.state.write_state")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal._write_config")
    def test_apply_does_not_persist_state_when_validation_fails(self, mock_write, mock_validate, mock_reload, mock_persist):
        mock_validate.side_effect = RuntimeError("nginx: [emerg] test failed")
        with self.assertRaises(RuntimeError):
            module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        mock_persist.assert_not_called()
        mock_reload.assert_not_called()


class CivicPortalLifecycleTests(unittest.TestCase):
    @patch("domain.targets.civicportal.compose.up")
    @patch("domain.targets.civicportal.certs.ensure_certs")
    @patch("domain.targets.civicportal.apply")
    @patch("domain.targets.civicportal.read_state")
    def test_up_ensures_certs_starts_and_reapplies_state(self, mock_read, mock_apply, mock_certs, mock_up):
        mock_read.return_value = {s: False for s in NAMES}
        module.up()
        mock_certs.assert_called_once_with(module.ROOT / "certs")
        mock_up.assert_called_once_with(module.COMPOSE_FILE)
        mock_apply.assert_called_once_with({}, {s: False for s in NAMES})

    @patch("domain.targets.civicportal.compose.down")
    def test_down_calls_compose_down(self, mock_down):
        module.down()
        mock_down.assert_called_once_with(module.COMPOSE_FILE)


class CivicPortalStateTests(unittest.TestCase):
    def test_read_state_defaults_false_when_missing(self):
        with patch.object(module, "STATE_PATH", Path("/nonexistent/state.json")):
            state = module.read_state()
        self.assertEqual(state, {s: False for s in NAMES})

    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    @patch("domain.targets.civicportal.compose.recreate")
    def test_apply_persists_state_so_read_state_returns_current(self, mock_recreate, mock_write, mock_reload, mock_validate):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "STATE_PATH", Path(tmp) / "state.json"):
                current = {**{s: False for s in NAMES}, "tls-legacy": True}
                module.apply({s: False for s in NAMES}, current)
                self.assertEqual(module.read_state(), current)

    @patch("domain.targets.civicportal.compose.validate_nginx_config")
    @patch("domain.targets.civicportal.compose.reload_nginx")
    @patch("domain.targets.civicportal._write_config")
    @patch("domain.targets.civicportal.compose.recreate")
    def test_successive_toggles_accumulate(self, mock_recreate, mock_write, mock_reload, mock_validate):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "STATE_PATH", Path(tmp) / "state.json"):
                all_false = {s: False for s in NAMES}
                first = {**all_false, "tls-legacy": True}
                second = {**all_false, "tls-legacy": True, "api-debug": True}
                module.apply(all_false, first)
                module.apply(first, second)
                self.assertEqual(module.read_state(), second)
                self.assertTrue(module.read_state()["tls-legacy"])
                self.assertTrue(module.read_state()["api-debug"])


class CivicPortalAtomicWriteTests(unittest.TestCase):
    def test_write_config_writes_atomically_via_replace(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "conf.d" / "default.conf"
            with patch.object(module, "CONFIG_PATH", target), \
                 patch("domain.targets.civicportal.os.replace", wraps=os.replace) as mock_replace, \
                 patch("domain.targets.civicportal.tempfile.mkstemp", wraps=tempfile.mkstemp) as mock_mkstemp:
                module._write_config("hello")
            mock_mkstemp.assert_called_once()
            mock_replace.assert_called_once()
            self.assertEqual(target.read_text(), "hello")
            self.assertFalse(list(target.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
