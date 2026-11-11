import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.targets import democommerce as module

NAMES = [s.name for s in module.TARGET.scenarios]


class DemocommerceTargetTests(unittest.TestCase):
    def test_declares_three_scenarios(self):
        self.assertEqual(set(NAMES), {"tls-legacy", "http-plain", "api-debug"})

    def test_target_metadata(self):
        self.assertEqual(module.TARGET.name, "democommerce")
        self.assertEqual(module.TARGET.base_url, "https://127.0.0.1:8444")
        self.assertEqual(module.TARGET.http_base_url, "http://127.0.0.1:8082")
        self.assertEqual(module.TARGET.approved_ports, (8444, 8082))
        self.assertEqual(module.TARGET.drift_ports, ())


class DemocommerceRenderTests(unittest.TestCase):
    def test_baseline_blocks_legacy_tls(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", cfg)
        self.assertNotIn("TLSv1 ", cfg)

    def test_tls_legacy_enables_legacy_protocols_and_seclevel_zero(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "tls-legacy": True})
        self.assertIn("TLSv1 ", cfg)
        self.assertIn("@SECLEVEL=0", cfg)

    def test_baseline_redirects_http(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("return 301 https://$host:8444$request_uri;", cfg)

    def test_http_plain_serves_the_store_instead(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "http-plain": True})
        port80 = cfg.split("server {")[1]          # the listen-80 server block is first in the template
        self.assertNotIn("return 301", port80)
        # `/` must be served as the static bundle: the API has no route for `/`, so proxying it
        # would answer 404, `probe_http_plain` would return unknown, and verify would fail
        self.assertIn("try_files $uri $uri/ /index.html;", port80)
        self.assertNotIn("proxy_pass", port80)

    def test_port80_server_block_declares_root_and_index_for_static_bundle(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        port80 = cfg.split("server {")[1]          # the listen-80 server block is first in the template
        self.assertIn("root /usr/share/nginx/html;", port80)
        self.assertIn("index index.html;", port80)

    def test_baseline_masks_the_internal_profile_endpoint(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("location = /api/internal/security-profile { return 404; }", cfg)

    def test_api_debug_proxies_the_internal_profile_endpoint(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "api-debug": True})
        self.assertNotIn("location = /api/internal/security-profile { return 404; }", cfg)
        self.assertIn("location = /api/internal/security-profile", cfg)
        self.assertIn("proxy_pass http://app/api/internal/security-profile", cfg)

    def test_no_placeholder_survives_rendering(self):
        for state in ({s: False for s in NAMES},
                      {s: True for s in NAMES}):
            cfg = module.nginx_config(state)
            self.assertNotIn("{{", cfg)


class DemocommerceApplyTests(unittest.TestCase):
    @patch("domain.targets.democommerce.compose.validate_nginx_config")
    @patch("domain.targets.democommerce.compose.reload_nginx")
    @patch("domain.targets.democommerce._write_config")
    def test_apply_writes_config_and_reloads(self, mock_write, mock_reload, mock_validate):
        state = {s: False for s in NAMES}
        module.apply({}, state)
        mock_write.assert_called_once()
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.democommerce.compose.validate_nginx_config")
    @patch("domain.targets.democommerce.compose.reload_nginx")
    @patch("domain.targets.democommerce._write_config")
    def test_apply_reloads_correct_compose_path(self, mock_write, mock_reload, mock_validate):
        module.apply({}, {s: False for s in NAMES})
        self.assertEqual(mock_reload.call_args[0][0], module.ROOT / "democommerce/deploy/lab.compose.yaml")

    @patch("domain.targets.democommerce.state.write_state")
    @patch("domain.targets.democommerce.compose.reload_nginx")
    @patch("domain.targets.democommerce.compose.validate_nginx_config")
    @patch("domain.targets.democommerce._write_config")
    def test_apply_validates_before_reload(self, mock_write, mock_validate, mock_reload, mock_persist):
        order = []
        mock_write.side_effect = lambda *_: order.append("write")
        mock_validate.side_effect = lambda *_: order.append("validate")
        mock_reload.side_effect = lambda *_: order.append("reload")
        mock_persist.side_effect = lambda *_: order.append("persist")
        module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        self.assertEqual(order, ["write", "validate", "reload", "persist"])

    @patch("domain.targets.democommerce.state.write_state")
    @patch("domain.targets.democommerce.compose.reload_nginx")
    @patch("domain.targets.democommerce.compose.validate_nginx_config")
    @patch("domain.targets.democommerce._write_config")
    def test_apply_does_not_persist_state_when_validation_fails(self, mock_write, mock_validate, mock_reload, mock_persist):
        mock_validate.side_effect = RuntimeError("nginx: [emerg] test failed")
        with self.assertRaises(RuntimeError):
            module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        mock_persist.assert_not_called()
        mock_reload.assert_not_called()


class DemocommerceLifecycleTests(unittest.TestCase):
    @patch("domain.targets.democommerce.compose.up")
    @patch("domain.targets.democommerce.certs.ensure_certs")
    @patch("domain.targets.democommerce.apply")
    @patch("domain.targets.democommerce.read_state")
    def test_up_ensures_certs_starts_and_reapplies_state(self, mock_read, mock_apply, mock_certs, mock_up):
        mock_read.return_value = {s: False for s in NAMES}
        module.up()
        mock_certs.assert_called_once_with(module.ROOT / "certs")
        mock_up.assert_called_once_with(module.COMPOSE_FILE)
        mock_apply.assert_called_once_with({}, {s: False for s in NAMES})

    @patch("domain.targets.democommerce.compose.down")
    def test_down_calls_compose_down(self, mock_down):
        module.down()
        mock_down.assert_called_once_with(module.COMPOSE_FILE)


class DemocommerceStateTests(unittest.TestCase):
    def test_read_state_defaults_false_when_missing(self):
        with patch.object(module, "STATE_PATH", Path("/nonexistent/state.json")):
            state = module.read_state()
        self.assertEqual(state, {s: False for s in NAMES})

    @patch("domain.targets.democommerce.compose.validate_nginx_config")
    @patch("domain.targets.democommerce.compose.reload_nginx")
    @patch("domain.targets.democommerce._write_config")
    def test_apply_persists_state_so_read_state_returns_current(self, mock_write, mock_reload, mock_validate):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "STATE_PATH", Path(tmp) / "state.json"):
                current = {**{s: False for s in NAMES}, "tls-legacy": True}
                module.apply({s: False for s in NAMES}, current)
                self.assertEqual(module.read_state(), current)

    @patch("domain.targets.democommerce.compose.validate_nginx_config")
    @patch("domain.targets.democommerce.compose.reload_nginx")
    @patch("domain.targets.democommerce._write_config")
    def test_successive_toggles_accumulate(self, mock_write, mock_reload, mock_validate):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "STATE_PATH", Path(tmp) / "state.json"):
                all_false = {s: False for s in NAMES}
                first = {**all_false, "tls-legacy": True}
                second = {**all_false, "tls-legacy": True, "http-plain": True}
                module.apply(all_false, first)
                module.apply(first, second)
                self.assertEqual(module.read_state(), second)
                self.assertTrue(module.read_state()["tls-legacy"])
                self.assertTrue(module.read_state()["http-plain"])


class DemocommerceAtomicWriteTests(unittest.TestCase):
    def test_write_config_writes_atomically_via_replace(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "conf.d" / "default.conf"
            with patch.object(module, "CONFIG_PATH", target), \
                 patch("domain.targets.democommerce.os.replace", wraps=os.replace) as mock_replace, \
                 patch("domain.targets.democommerce.tempfile.mkstemp", wraps=tempfile.mkstemp) as mock_mkstemp:
                module._write_config("hello")
            mock_mkstemp.assert_called_once()
            mock_replace.assert_called_once()
            self.assertEqual(target.read_text(), "hello")
            self.assertFalse(list(target.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
