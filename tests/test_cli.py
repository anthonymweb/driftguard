import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

from domain.model import Scenario, Target


def _fake_target(name="t1", base_url="https://127.0.0.1:9443"):
    return Target(
        name=name,
        base_url=base_url,
        http_base_url="http://127.0.0.1:9080",
        approved_ports=(9443, 9080),
        drift_ports=(),
        scope=("tls",),
        scenarios=(
            Scenario(name="s1", area="TLS", expected_finding="f1"),
            Scenario(name="s2", area="Network", expected_finding="f2"),
        ),
    )


def _fake_module(target, state=None, probes=None):
    mod = mock.Mock()
    mod.TARGET = target
    mod.read_state.return_value = state if state is not None else {
        s.name: False for s in target.scenarios}
    mod.probes.return_value = probes if probes is not None else {
        s.name: (lambda r="absent": lambda: r)() for s in target.scenarios}
    mod.nginx_config.return_value = None
    mod.up = mock.Mock()
    mod.down = mock.Mock()
    mod.apply = mock.Mock()
    return mod


class CliTests(unittest.TestCase):
    def test_build_parser_exposes_every_contract_subcommand(self):
        from domain.cli import build_parser
        parser = build_parser()
        # argparse stores subparsers choices on the action
        sub = [a for a in parser._actions if getattr(a, "choices", None)]
        self.assertTrue(sub)
        names = set(sub[0].choices.keys())
        self.assertEqual(
            names,
            {"status", "truth", "verify", "mark", "up", "down", "on", "off", "reset"},
        )

    def test_status_json_shape_has_targets_and_states(self):
        from domain import cli
        target = _fake_target()
        mod = _fake_module(target, state={"s1": True, "s2": False})
        targets = {target.name: target}
        modules = {target.name: mod}
        buf = io.StringIO()
        with mock.patch.object(cli, "TARGETS", targets), \
             mock.patch.object(cli, "MODULES", modules), \
             mock.patch.object(cli, "probe_port_open", return_value="present"), \
             redirect_stdout(buf):
            rc = cli.main(["status", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertIn("targets", data)
        self.assertIn(target.name, data["targets"])
        self.assertEqual(data["targets"][target.name]["s1"], True)
        self.assertEqual(data["targets"][target.name]["s2"], False)

    def test_truth_json_is_target_scenario_scan_label(self):
        from domain import cli
        target = _fake_target()
        targets = {target.name: target}
        scans = [mock.Mock(label="scan1", states={target.name: {"s1": False, "s2": False}}),
                 mock.Mock(label="scan2", states={target.name: {"s1": True, "s2": False}})]
        buf = io.StringIO()
        with mock.patch.object(cli, "TARGETS", targets), \
             mock.patch.object(cli.state, "read_scans", return_value=scans), \
             redirect_stdout(buf):
            rc = cli.main(["truth", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        # target -> scenario -> list of labels per scan
        self.assertIn(target.name, data)
        self.assertIn("s1", data[target.name])
        self.assertIsInstance(data[target.name]["s1"], list)
        self.assertEqual(len(data[target.name]["s1"]), 2)

    def test_verify_returns_zero_when_all_probes_match(self):
        from domain import cli
        target = _fake_target()
        mod = _fake_module(target, state={"s1": False, "s2": True},
                           probes={"s1": lambda: "absent", "s2": lambda: "present"})
        with mock.patch.object(cli, "TARGETS", {target.name: target}), \
             mock.patch.object(cli, "MODULES", {target.name: mod}), \
             mock.patch.object(cli, "probe_port_open", return_value="present"), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["verify"])
        self.assertEqual(rc, 0)

    def test_verify_returns_nonzero_on_mismatch(self):
        from domain import cli
        target = _fake_target()
        mod = _fake_module(target, state={"s1": True, "s2": False},
                           probes={"s1": lambda: "absent", "s2": lambda: "absent"})
        with mock.patch.object(cli, "TARGETS", {target.name: target}), \
             mock.patch.object(cli, "MODULES", {target.name: mod}), \
             mock.patch.object(cli, "probe_port_open", return_value="present"), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["verify"])
        self.assertEqual(rc, 1)

    def test_on_rejects_unknown_scenario(self):
        from domain import cli
        target = _fake_target()
        mod = _fake_module(target)
        with mock.patch.object(cli, "TARGETS", {target.name: target}), \
             mock.patch.object(cli, "MODULES", {target.name: mod}), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["on", target.name, "no-such-scenario"])
        self.assertEqual(rc, 2)

    def test_on_rejects_unknown_target(self):
        from domain import cli
        with mock.patch.object(cli, "TARGETS", {}), \
             mock.patch.object(cli, "MODULES", {}), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["on", "no-such-target", "s1"])
        self.assertEqual(rc, 2)

    def test_mark_records_every_registered_target(self):
        from domain import cli
        t1 = _fake_target("t1", "https://127.0.0.1:9443")
        t2 = _fake_target("t2", "https://127.0.0.1:9444")
        m1 = _fake_module(t1, state={"s1": True, "s2": False})
        m2 = _fake_module(t2, state={"s1": False, "s2": True})
        with mock.patch.object(cli, "TARGETS", {t1.name: t1, t2.name: t2}), \
             mock.patch.object(cli, "MODULES", {t1.name: m1, t2.name: m2}), \
             mock.patch.object(cli, "probe_port_open", return_value="present"), \
             mock.patch.object(cli.state, "record_scan") as rec, \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["mark", "scan-A"])
        self.assertEqual(rc, 0)
        rec.assert_called_once()
        label, states = rec.call_args[0]
        self.assertEqual(label, "scan-A")
        self.assertIn("t1", states)
        self.assertIn("t2", states)

    def test_mark_records_down_target_as_none(self):
        from domain import cli
        target = _fake_target()
        mod = _fake_module(target)
        with mock.patch.object(cli, "TARGETS", {target.name: target}), \
             mock.patch.object(cli, "MODULES", {target.name: mod}), \
             mock.patch.object(cli, "probe_port_open", return_value="absent"), \
             mock.patch.object(cli.state, "record_scan") as rec, \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["mark", "scan-B"])
        self.assertEqual(rc, 0)
        _, states = rec.call_args[0]
        self.assertIsNone(states[target.name])

    def test_verify_down_target_reports_unknown_without_failing(self):
        from domain import cli
        target = _fake_target()
        mod = _fake_module(target, state={"s1": True, "s2": True})
        buf = io.StringIO()
        with mock.patch.object(cli, "TARGETS", {target.name: target}), \
             mock.patch.object(cli, "MODULES", {target.name: mod}), \
             mock.patch.object(cli, "probe_port_open", return_value="absent"), \
             redirect_stdout(buf):
            rc = cli.main(["verify", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        # down target probes reported as unknown
        self.assertIn(target.name, data)
        for v in data[target.name].values():
            self.assertEqual(v["observed"], "unknown")

    def test_up_without_target_brings_up_every_registered_target(self):
        from domain import cli
        t1 = _fake_target("t1")
        t2 = _fake_target("t2")
        m1, m2 = _fake_module(t1), _fake_module(t2)
        with mock.patch.object(cli, "TARGETS", {t1.name: t1, t2.name: t2}), \
             mock.patch.object(cli, "MODULES", {t1.name: m1, t2.name: m2}), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["up"])
        self.assertEqual(rc, 0)
        m1.up.assert_called_once()
        m2.up.assert_called_once()

    def test_up_with_target_brings_up_only_that_target(self):
        from domain import cli
        t1 = _fake_target("t1")
        t2 = _fake_target("t2")
        m1, m2 = _fake_module(t1), _fake_module(t2)
        with mock.patch.object(cli, "TARGETS", {t1.name: t1, t2.name: t2}), \
             mock.patch.object(cli, "MODULES", {t1.name: m1, t2.name: m2}), \
             redirect_stdout(io.StringIO()):
            rc = cli.main(["up", "t1"])
        self.assertEqual(rc, 0)
        m1.up.assert_called_once()
        m2.up.assert_not_called()


if __name__ == "__main__":
    unittest.main()
