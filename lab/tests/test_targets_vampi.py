import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain.targets import vampi as module

NAMES = [s.name for s in module.TARGET.scenarios]


class VampiTargetTests(unittest.TestCase):
    def test_declares_three_scenarios(self):
        self.assertEqual(set(NAMES), {"tls-legacy", "port-open", "api-debug"})

    def test_target_metadata(self):
        self.assertEqual(module.TARGET.name, "vampi")
        self.assertEqual(module.TARGET.base_url, "https://127.0.0.1:8447")
        self.assertEqual(module.TARGET.http_base_url, "http://127.0.0.1:8086")
        self.assertEqual(module.TARGET.approved_ports, (8447, 8086))
        self.assertEqual(module.TARGET.drift_ports, (8087,))

    def test_approved_ports_exclude_drift_port(self):
        self.assertNotIn(8087, module.TARGET.approved_ports)
        self.assertIn(8087, module.TARGET.drift_ports)


class VampiRenderTests(unittest.TestCase):
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
        self.assertIn("location = /users/v1/_debug { return 403; }", cfg)

    def test_api_debug_proxies_the_debug_endpoint(self):
        cfg = module.nginx_config({**{s: False for s in NAMES}, "api-debug": True})
        self.assertNotIn("location = /users/v1/_debug { return 403; }", cfg)
        self.assertIn("location = /users/v1/_debug", cfg)
        self.assertIn("proxy_pass http://vampi/users/v1/_debug;", cfg)

    def test_upstream_points_at_vampi(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("server vampi:5000;", cfg)

    def test_expose_override_maps_8087(self):
        content = module.OVERRIDE_PATH.read_text()
        self.assertIn("127.0.0.1:8087:5000", content)

    def test_baseline_redirects_http(self):
        cfg = module.nginx_config({s: False for s in NAMES})
        self.assertIn("return 301 https://$host:8447$request_uri;", cfg)

    def test_no_placeholder_survives_rendering(self):
        for state in ({s: False for s in NAMES}, {s: True for s in NAMES}):
            cfg = module.nginx_config(state)
            self.assertNotIn("{{", cfg)


class VampiApplyTests(unittest.TestCase):
    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    @patch("domain.targets.vampi._init_db")
    @patch("domain.targets.vampi._drift_port_published", return_value=False)
    def test_apply_writes_config_and_reloads(self, mock_published, mock_init, mock_recreate, mock_write, mock_reload, mock_validate):
        state = {s: False for s in NAMES}
        module.apply(state, state)
        mock_write.assert_called_once()
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)
        mock_recreate.assert_not_called()
        mock_init.assert_not_called()

    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    @patch("domain.targets.vampi._init_db")
    @patch("domain.targets.vampi._drift_port_published", return_value=False)
    def test_apply_enables_port_open_uses_override(self, mock_published, mock_init, mock_recreate, mock_write, mock_reload, mock_validate):
        previous = {s: False for s in NAMES}
        current = {**previous, "port-open": True}
        module.apply(previous, current)
        mock_recreate.assert_called_once_with(module.COMPOSE_FILE, module.OVERRIDE_PATH)
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    @patch("domain.targets.vampi._init_db")
    @patch("domain.targets.vampi._drift_port_published", return_value=True)
    def test_apply_disables_port_open_recreates_without_override(self, mock_published, mock_init, mock_recreate, mock_write, mock_reload, mock_validate):
        previous = {**{s: False for s in NAMES}, "port-open": True}
        current = {s: False for s in NAMES}
        module.apply(previous, current)
        mock_recreate.assert_called_once_with(module.COMPOSE_FILE, None)
        mock_reload.assert_called_once_with(module.COMPOSE_FILE)

    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    @patch("domain.targets.vampi._init_db")
    @patch("domain.targets.vampi._drift_port_published", return_value=True)
    def test_apply_withdraws_the_port_when_the_recorded_state_disagrees_with_reality(
            self, mock_published, mock_init, mock_recreate, mock_write, mock_reload, mock_validate):
        # The recorded state says the port is closed but the port is still
        # published: the apply must repair that, not trust the record.
        previous = {s: False for s in NAMES}
        current = {s: False for s in NAMES}
        module.apply(previous, current)
        mock_recreate.assert_called_once_with(module.COMPOSE_FILE, None)

    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    @patch("domain.targets.vampi._init_db")
    def test_apply_reloads_correct_compose_path(self, mock_init, mock_recreate, mock_write, mock_reload, mock_validate):
        module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        self.assertEqual(
            mock_reload.call_args[0][0],
            module.ROOT / "targets/vampi/compose.yaml",
        )

    @patch("domain.targets.vampi.state.write_state")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    def test_apply_validates_before_reload_and_persists_last(
        self, mock_recreate, mock_write, mock_validate, mock_reload, mock_persist
    ):
        order = []
        mock_write.side_effect = lambda *_: order.append("write")
        mock_validate.side_effect = lambda *_: order.append("validate")
        mock_reload.side_effect = lambda *_: order.append("reload")
        mock_persist.side_effect = lambda *_: order.append("persist")
        module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        self.assertEqual(order, ["write", "validate", "reload", "persist"])

    @patch("domain.targets.vampi.state.write_state")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi._write_config")
    def test_apply_does_not_persist_state_when_validation_fails(
        self, mock_write, mock_validate, mock_reload, mock_persist
    ):
        mock_validate.side_effect = RuntimeError("nginx: [emerg] test failed")
        with self.assertRaises(RuntimeError):
            module.apply({s: False for s in NAMES}, {s: False for s in NAMES})
        mock_persist.assert_not_called()
        mock_reload.assert_not_called()

    @patch("domain.targets.vampi.state.write_state")
    @patch("domain.targets.vampi._init_db")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    def test_apply_reinitialises_db_before_persist_when_port_open_changes(
        self, mock_recreate, mock_write, mock_validate, mock_reload, mock_init, mock_persist
    ):
        order = []
        mock_recreate.side_effect = lambda *_: order.append("recreate")
        mock_reload.side_effect = lambda *_: order.append("reload")
        mock_init.side_effect = lambda *_: order.append("init_db")
        mock_persist.side_effect = lambda *_: order.append("persist")
        previous = {s: False for s in NAMES}
        current = {**previous, "port-open": True}
        module.apply(previous, current)
        mock_init.assert_called_once()
        self.assertIn("recreate", order)
        self.assertIn("init_db", order)
        self.assertIn("persist", order)
        self.assertLess(order.index("recreate"), order.index("init_db"))
        self.assertLess(order.index("init_db"), order.index("persist"))

    @patch("domain.targets.vampi._init_db")
    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    @patch("domain.targets.vampi._drift_port_published", return_value=False)
    def test_apply_does_not_reinitialise_db_when_port_open_unchanged(
        self, mock_published, mock_recreate, mock_write, mock_reload, mock_validate, mock_init
    ):
        previous = {**{s: False for s in NAMES}, "api-debug": True}
        current = {**{s: False for s in NAMES}, "api-debug": False}
        module.apply(previous, current)
        mock_recreate.assert_not_called()
        mock_init.assert_not_called()


class VampiLifecycleTests(unittest.TestCase):
    @patch("domain.targets.vampi.compose.up")
    @patch("domain.targets.vampi.certs.ensure_certs")
    @patch("domain.targets.vampi.apply")
    @patch("domain.targets.vampi.read_state")
    @patch("domain.targets.vampi._wait_for_ready")
    @patch("domain.targets.vampi._init_db")
    def test_up_ensures_certs_starts_applies_waits_then_initializes(
        self, mock_init, mock_wait, mock_read, mock_apply, mock_certs, mock_up
    ):
        mock_read.return_value = {s: False for s in NAMES}
        order = []
        mock_certs.side_effect = lambda *_: order.append("certs")
        mock_up.side_effect = lambda *_: order.append("up")
        mock_apply.side_effect = lambda *_: order.append("apply")
        mock_init.side_effect = lambda *_: order.append("init_db")
        mock_wait.side_effect = lambda *_: order.append("wait")
        module.up()
        mock_certs.assert_called_once_with(module.ROOT / "certs")
        mock_up.assert_called_once_with(module.COMPOSE_FILE)
        mock_init.assert_called_once()
        mock_wait.assert_called_once()
        mock_apply.assert_called_once_with({}, {s: False for s in NAMES})
        self.assertEqual(order, ["certs", "up", "apply", "wait", "init_db"])

    @patch("domain.targets.vampi.compose.down")
    def test_down_calls_compose_down(self, mock_down):
        module.down()
        mock_down.assert_called_once_with(module.COMPOSE_FILE)


class VampiReadinessTests(unittest.TestCase):
    def test_init_db_calls_createdb_through_controlled_host(self):
        called = {}

        class FakeResp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req, context=None, timeout=None):
            called["url"] = req.full_url
            return FakeResp()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"), \
             patch("time.monotonic", side_effect=[0, 1]):
            module._init_db()
        self.assertEqual(called["url"], "https://127.0.0.1:8447/createdb")

    def test_init_db_retries_until_request_succeeds(self):
        import urllib.error

        attempts = {"count": 0}

        class FakeResp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False

        def fake_urlopen(req, context=None, timeout=None):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise urllib.error.URLError("refused")
            return FakeResp()

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep") as mock_sleep, \
             patch("time.monotonic", side_effect=[0, 1, 2, 3, 4, 5]):
            module._init_db(timeout=60)
        self.assertEqual(attempts["count"], 3)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_init_db_raises_runtime_error_with_url_after_timeout(self):
        import urllib.error

        def fake_urlopen(req, context=None, timeout=None):
            raise urllib.error.URLError("refused")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"), \
             patch("time.monotonic", side_effect=[0, 1, 61]):
            with self.assertRaises(RuntimeError) as ctx:
                module._init_db(timeout=60)
        self.assertIn("https://127.0.0.1:8447/createdb", str(ctx.exception))
        self.assertIn("vampi", str(ctx.exception).lower())

    def test_wait_for_ready_polls_root_until_status_below_500(self):
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
            self.assertEqual(req.full_url, "https://127.0.0.1:8447/")
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
        self.assertIn("vampi", str(ctx.exception).lower())


class VampiStateTests(unittest.TestCase):
    def test_read_state_defaults_false_when_missing(self):
        with patch.object(module, "STATE_PATH", Path("/nonexistent/state.json")):
            state = module.read_state()
        self.assertEqual(state, {s: False for s in NAMES})

    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    def test_apply_persists_state_so_read_state_returns_current(
        self, mock_recreate, mock_write, mock_reload, mock_validate
    ):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(module, "STATE_PATH", Path(tmp) / "state.json"):
                current = {**{s: False for s in NAMES}, "tls-legacy": True}
                module.apply({s: False for s in NAMES}, current)
                self.assertEqual(module.read_state(), current)

    @patch("domain.targets.vampi.compose.validate_nginx_config")
    @patch("domain.targets.vampi.compose.reload_nginx")
    @patch("domain.targets.vampi._write_config")
    @patch("domain.targets.vampi.compose.recreate")
    def test_successive_toggles_accumulate(
        self, mock_recreate, mock_write, mock_reload, mock_validate
    ):
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


class VampiAtomicWriteTests(unittest.TestCase):
    def test_write_config_writes_atomically_via_replace(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "conf.d" / "default.conf"
            with patch.object(module, "CONFIG_PATH", target), \
                 patch("domain.targets.vampi.os.replace", wraps=os.replace) as mock_replace, \
                 patch("domain.targets.vampi.tempfile.mkstemp", wraps=tempfile.mkstemp) as mock_mkstemp:
                module._write_config("hello")
            mock_mkstemp.assert_called_once()
            mock_replace.assert_called_once()
            self.assertEqual(target.read_text(), "hello")
            self.assertFalse(list(target.parent.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
