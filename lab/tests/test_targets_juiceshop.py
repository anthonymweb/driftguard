import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.targets import juiceshop as module

NAMES = [s.name for s in module.TARGET.scenarios]


class JuiceShopTargetTests(unittest.TestCase):
    def test_declares_three_scenarios(self):
        self.assertEqual(set(NAMES), {"tls-legacy", "http-plain", "api-debug"})

    def test_target_metadata(self):
        self.assertEqual(module.TARGET.name, "juice-shop")
        self.assertEqual(module.TARGET.base_url, "https://127.0.0.1:8446")
        self.assertEqual(module.TARGET.http_base_url, "http://127.0.0.1:8085")
        self.assertEqual(module.TARGET.approved_ports, (8446, 8085))
        self.assertEqual(module.TARGET.drift_ports, ())

    def test_no_drift_ports(self):
        self.assertEqual(module.TARGET.drift_ports, ())


class JuiceShopRenderTests(unittest.TestCase):
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
        self.assertIn("return 301 https://$host:8446$request_uri;", cfg)

    def test_http_plain_serves_the_app_instead(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "http-plain": True})
        port80 = cfg.split("server {")[1]
        self.assertNotIn("return 301", port80)
        self.assertIn("proxy_pass http://juice-shop;", port80)

    def test_baseline_blocks_the_admin_api(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("location ^~ /rest/admin/ { return 403; }", cfg)

    def test_api_debug_proxies_the_admin_api(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "api-debug": True})
        self.assertNotIn("location ^~ /rest/admin/ { return 403; }", cfg)
        self.assertIn("location ^~ /rest/admin/", cfg)
        self.assertIn("proxy_pass http://juice-shop;", cfg)

    def test_proxy_pass_references_upstream_group_without_port(self):
        # Template location / and DEBUG_LOCATION drift must not carry :3000 on the group.
        for state in ({s: False for s in NAMES}, {s: True for s in NAMES}):
            cfg = module.nginx_config(state)
            self.assertNotIn("proxy_pass http://juice-shop:3000", cfg)

    def test_upstream_points_at_the_benchmark_container(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("server juice-shop:3000;", cfg)

    def test_no_placeholder_survives_rendering(self):
        for state in ({s: False for s in NAMES}, {s: True for s in NAMES}):
            cfg = module.nginx_config(state)
            self.assertNotIn("{{", cfg)


class JuiceShopApplyTests(unittest.TestCase):
    @patch("domain.targets.juiceshop.compose.validate_nginx_config")
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_writes_config_and_reloads(self, mock_write, mock_reload, mock_validate):
        state = {s: False for s in NAMES}
        module.apply(state, state)
        mock_write.assert_called_once()
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.juiceshop.compose.validate_nginx_config")
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_reloads_correct_compose_path(self, mock_write, mock_reload, mock_validate):
        module.apply({}, {s: False for s in NAMES})
        self.assertEqual(
            mock_reload.call_args[0][0],
            module.ROOT / "targets/juiceshop/compose.yaml",
        )

    @patch("domain.targets.juiceshop.state.write_state")
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop.compose.validate_nginx_config")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_validates_before_reload(self, mock_write, mock_validate, mock_reload, mock_persist):
        order = []
        mock_write.side_effect = lambda *_: order.append("write")
        mock_validate.side_effect = lambda *_: order.append("validate")
        mock_reload.side_effect = lambda *_: order.append("reload")
        mock_persist.side_effect = lambda *_: order.append("persist")
        module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        self.assertEqual(order, ["write", "validate", "reload", "persist"])

    @patch("domain.targets.juiceshop.state.write_state")
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop.compose.validate_nginx_config")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_does_not_persist_state_when_validation_fails(self, mock_write, mock_validate, mock_reload, mock_persist):
        mock_validate.side_effect = RuntimeError("nginx: [emerg] test failed")
        with self.assertRaises(RuntimeError):
            module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        mock_persist.assert_not_called()
        mock_reload.assert_not_called()


class JuiceShopLifecycleTests(unittest.TestCase):
    @patch("domain.targets.juiceshop.compose.up")
    @patch("domain.targets.juiceshop.certs.ensure_certs")
    @patch("domain.targets.juiceshop.apply")
    @patch("domain.targets.juiceshop.read_state")
    @patch("domain.targets.juiceshop._wait_for_ready")
    def test_up_ensures_certs_starts_applies_then_waits_and_reapplies_state(
        self, mock_wait, mock_read, mock_apply, mock_certs, mock_up
    ):
        mock_read.return_value = {s: False for s in NAMES}
        order = []
        mock_certs.side_effect = lambda *_: order.append("certs")
        mock_up.side_effect = lambda *_: order.append("up")
        mock_apply.side_effect = lambda *_: order.append("apply")
        mock_wait.side_effect = lambda *_: order.append("wait")
        module.up()
        mock_certs.assert_called_once_with(module.ROOT / "certs")
        mock_up.assert_called_once_with(module.COMPOSE_FILE)
        mock_wait.assert_called_once()
        mock_apply.assert_called_once_with({}, {s: False for s in NAMES})
        self.assertEqual(order, ["certs", "up", "apply", "wait"])

    @patch("domain.targets.juiceshop.compose.down")
    def test_down_calls_compose_down(self, mock_down):
        module.down()
        mock_down.assert_called_once_with(module.COMPOSE_FILE)


class JuiceShopReadinessTests(unittest.TestCase):
    def test_wait_for_ready_polls_root_until_status_below_500(self):
        import http.client
        import ssl
        import urllib.error

        responses = [502, 503, 200]

        class FakeResp:
            def __init__(self, status):
                self.status = status
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req, context=None, timeout=None):
            status = responses.pop(0)
            if status >= 500:
                raise urllib.error.HTTPError(req.full_url, status, "err", {}, None)
            return FakeResp(status)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"), \
             patch("time.monotonic", side_effect=[0, 1, 2, 3, 4, 5, 6]):
            module._wait_for_ready(timeout=180)

        self.assertEqual(responses, [])

    def test_wait_for_ready_times_out_with_clear_message(self):
        import urllib.error

        def fake_urlopen(req, context=None, timeout=None):
            raise urllib.error.URLError("refused")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"), \
             patch("time.monotonic", side_effect=[0, 1, 181]):
            with self.assertRaises(RuntimeError) as ctx:
                module._wait_for_ready(timeout=180)
        self.assertIn("juice-shop", str(ctx.exception).lower())


class JuiceShopStateTests(unittest.TestCase):
    def test_read_state_defaults_false_when_missing(self):
        with patch.object(module, "STATE_PATH", Path("/nonexistent/state.json")):
            state = module.read_state()
        self.assertEqual(state, {s: False for s in NAMES})

    @patch("domain.targets.juiceshop.compose.validate_nginx_config")
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_persists_state_so_read_state_returns_current(self, mock_write, mock_reload, mock_validate):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "STATE_PATH", Path(tmp) / "state.json"):
                current = {**{s: False for s in NAMES}, "tls-legacy": True}
                module.apply({s: False for s in NAMES}, current)
                self.assertEqual(module.read_state(), current)

    @patch("domain.targets.juiceshop.compose.validate_nginx_config")
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop._write_config")
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


class JuiceShopAtomicWriteTests(unittest.TestCase):
    def test_write_config_writes_atomically_via_replace(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "conf.d" / "default.conf"
            with patch.object(module, "CONFIG_PATH", target), \
                 patch("domain.targets.juiceshop.os.replace", wraps=os.replace) as mock_replace, \
                 patch("domain.targets.juiceshop.tempfile.mkstemp", wraps=tempfile.mkstemp) as mock_mkstemp:
                module._write_config("hello")
            mock_mkstemp.assert_called_once()
            mock_replace.assert_called_once()
            self.assertEqual(target.read_text(), "hello")
            self.assertFalse(list(target.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
