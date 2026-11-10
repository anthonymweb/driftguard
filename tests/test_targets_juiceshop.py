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
        self.assertIn("proxy_pass http://juice-shop:3000;", port80)

    def test_baseline_blocks_the_admin_api(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("location ^~ /rest/admin/ { return 403; }", cfg)

    def test_api_debug_proxies_the_admin_api(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "api-debug": True})
        self.assertNotIn("location ^~ /rest/admin/ { return 403; }", cfg)
        self.assertIn("location ^~ /rest/admin/", cfg)
        self.assertIn("proxy_pass http://juice-shop:3000;", cfg)

    def test_upstream_points_at_the_benchmark_container(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("server juice-shop:3000;", cfg)

    def test_no_placeholder_survives_rendering(self):
        for state in ({s: False for s in NAMES}, {s: True for s in NAMES}):
            cfg = module.nginx_config(state)
            self.assertNotIn("{{", cfg)


class JuiceShopApplyTests(unittest.TestCase):
    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_writes_config_and_reloads(self, mock_write, mock_reload):
        state = {s: False for s in NAMES}
        module.apply(state, state)
        mock_write.assert_called_once()
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.juiceshop.compose.reload_nginx")
    @patch("domain.targets.juiceshop._write_config")
    def test_apply_reloads_correct_compose_path(self, mock_write, mock_reload):
        module.apply({}, {s: False for s in NAMES})
        self.assertEqual(
            mock_reload.call_args[0][0],
            module.ROOT / "targets/juiceshop/compose.yaml",
        )


class JuiceShopLifecycleTests(unittest.TestCase):
    @patch("domain.targets.juiceshop.compose.up")
    @patch("domain.targets.juiceshop.certs.ensure_certs")
    @patch("domain.targets.juiceshop.apply")
    @patch("domain.targets.juiceshop.read_state")
    @patch("domain.targets.juiceshop._wait_for_ready")
    def test_up_ensures_certs_starts_waits_and_reapplies_state(
        self, mock_wait, mock_read, mock_apply, mock_certs, mock_up
    ):
        mock_read.return_value = {s: False for s in NAMES}
        module.up()
        mock_certs.assert_called_once_with(module.ROOT / "certs")
        mock_up.assert_called_once_with(module.COMPOSE_FILE)
        mock_wait.assert_called_once()
        mock_apply.assert_called_once_with({}, {s: False for s in NAMES})

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


if __name__ == "__main__":
    unittest.main()
