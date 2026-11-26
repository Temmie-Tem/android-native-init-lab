"""Host-only S20+ C-stage reader and single-grant owner regressions."""

from contextlib import ExitStack, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/mainline-handoff"
PRIVATE = ROOT / "workspace/private"
RETAINED_READER = PRIVATE / "analysis/s20plus-y2q-early-pair-20261126/retained-reader/return_stage.py"
sys.path.insert(0, str(SCRIPTS))


class CStageReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("cstage_reader_fixture", SOURCE / "return_stage.py")
        cls.reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.reader)

    def test_reader_keeps_counts_and_ambiguity(self):
        self.assertEqual(self.reader.STAGES, ("fdt", "unflatten"))
        for first, second, paired, status in (
            (0, 0, 0, "no_record"), (1, 0, 0, "fdt_only"), (0, 1, 0, "unflatten_only"),
            (1, 1, 1, "paired"), (1, 1, 0, "ambiguous"), (2, 2, 0, "ambiguous"),
        ):
            with self.subTest(first=first, second=second, paired=paired):
                raw = f"y2q_log_v1=512,{first},{second},{paired}\n".encode()
                result = self.reader.parse(0, raw, b"")
                self.assertEqual((result["fdt_count"], result["unflatten_count"], result["state"]),
                                 (first, second, status))
        self.assertEqual(self.reader.parse(0, b"y2q_log_missing\n", b""), {"state": "missing"})
        with self.assertRaises(ValueError):
            self.reader.parse(0, b"y2q_early_v2=512,1,1,1\n", b"")


@unittest.skipUnless(RETAINED_READER.is_file(), "requires the retained S20+ owner source")
class CStageOwner(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_cstage_list_f1 as profile

        self.m = profile
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.run = Path(self.stack.enter_context(tempfile.TemporaryDirectory())) / "run-1234567890123456789"
        self.run.mkdir()
        self.ticket = self.run.with_name("ticket-1234567890123456789")
        self.ticket.mkdir()
        self.prepared = {"binding_sha256": "a" * 64}
        self.final = {"rollback_transfer_completed": True}
        self.engine = Mock()
        self.acm = Mock()
        self.patch(profile.owner, "engine", self.engine, create=True)
        self.patch(profile, "observer", return_value=self.acm)
        self.patch(profile.base, "ticket_dir", return_value=self.ticket)

    def patch(self, obj, name, *args, **kwargs):
        return self.stack.enter_context(patch.object(obj, name, *args, **kwargs))

    def test_transfer_is_proved_by_raw_receipt(self):
        proof = self.patch(self.m.owner, "transfer_receipt")
        self.assertFalse(self.m.candidate_transfer_proved(self.run, self.prepared))
        (self.run / "candidate-result.json").touch()
        self.engine.read_json.return_value = {"classification": "uncertain"}
        self.assertFalse(self.m.candidate_transfer_proved(self.run, self.prepared))
        proof.assert_not_called()
        self.engine.read_json.return_value = {"classification": "odin_transfer_completed"}
        self.assertTrue(self.m.candidate_transfer_proved(self.run, self.prepared))
        proof.assert_called_once_with(self.run, "candidate", self.prepared["binding_sha256"])
        proof.side_effect = self.m.owner.Stop("missing raw receipt")
        with self.assertRaises(self.m.owner.Stop):
            self.m.candidate_transfer_proved(self.run, self.prepared)

    def test_acm_read_runs_once_only_on_verified_execute(self):
        proof = self.patch(self.m, "candidate_transfer_proved", return_value=True)
        now = self.patch(self.m.time, "monotonic", side_effect=[10, 20, 210, 210])
        pause = self.patch(self.m.time, "sleep")
        lease = self.patch(self.m.owner, "runtime", Mock(), create=True)
        lease._require_live_transaction.return_value = {"entrypoint": "execute", "run_dir": str(self.run)}
        outcome, serial = self.m.observe(self.run, self.prepared)
        self.acm.observe.assert_called_once_with(self.run, self.prepared)
        pause.assert_called_once_with(170)
        self.assertEqual(outcome["environment"], "mainline-physical-return")
        self.assertEqual(outcome["claim_verdict"], "NO_PROOF")
        self.assertFalse(outcome["transport_authorized"])
        self.assertIsNone(serial)
        lease._require_live_transaction.return_value["entrypoint"] = "resume_run"
        self.m.observe(self.run, self.prepared)
        self.acm.observe.assert_called_once()
        self.assertEqual(pause.call_args.args, (180,))
        proof.return_value = False
        self.m.observe(self.run, self.prepared)
        self.acm.observe.assert_called_once()
        self.assertEqual(now.call_count, 4)

    def test_wrong_lease_cannot_request_acm(self):
        self.patch(self.m, "candidate_transfer_proved", return_value=True)
        lease = self.patch(self.m.owner, "runtime", Mock(), create=True)
        lease._require_live_transaction.return_value = {"entrypoint": "execute", "run_dir": str(self.ticket)}
        with self.assertRaises(self.m.owner.Stop):
            self.m.observe(self.run, self.prepared)
        self.acm.observe.assert_not_called()

    def test_prepare_checks_host_serial_policy_before_creating_ticket(self):
        m = self.m
        calls = Mock()
        calls.attach_mock(self.acm.host_serial_policy, "host_serial_policy")
        prepare = self.patch(m, "retained_prepare", calls.prepare)
        self.assertIs(m.prepare(), prepare.return_value)
        self.assertEqual([call[0] for call in calls.mock_calls], ["host_serial_policy", "prepare"])
        self.acm.host_serial_policy.side_effect = m.owner.Stop("unsafe host serial policy")
        with self.assertRaises(m.owner.Stop):
            m.prepare()
        prepare.assert_called_once()

    def test_effect_time_checks_retained_authority_then_current_host_policy(self):
        m = self.m
        calls = Mock()
        calls.attach_mock(self.acm.host_serial_policy, "host_serial_policy")
        accept = self.patch(m.base, "accepted", calls.retained_grant)
        accept.return_value = ({"expires": 905}, "grant")
        clock = self.patch(m.time, "time", calls.effect_time)
        clock.return_value = 904
        module = Mock()
        configure = self.patch(m.previous, "configure_pair")
        m._configure_runtime(module)
        configure.assert_called_once_with(module)
        self.assertIs(module._early_effect_deadline, m.raw_deadline)
        module._early_effect_deadline(self.run)
        self.assertEqual([call[0] for call in calls.mock_calls],
                         ["retained_grant", "host_serial_policy", "effect_time"])
        accept.assert_called_once_with(self.run, fresh=True)
        accept.side_effect = m.owner.Stop("expired original grant")
        with self.assertRaises(m.owner.Stop):
            module._early_effect_deadline(self.run)
        self.acm.host_serial_policy.assert_called_once()
        accept.side_effect = None
        clock.return_value = 905
        with self.assertRaisesRegex(m.owner.Stop, "expired during host serial policy"):
            module._early_effect_deadline(self.run)
        self.assertEqual(self.acm.host_serial_policy.call_count, 2)

    def test_gap_and_persisted_observation_are_distinct(self):
        classify = self.m.observe_acm_result
        self.assertEqual(classify(self.run, self.prepared, transfer_proved=True), "observation_gap")
        self.assertEqual(classify(self.run, self.prepared, transfer_proved=False), "transfer_unproved")
        receipt = self.ticket / self.m.ACM_SUMMARY
        receipt.touch()
        value = dict(schema="s20plus_cstage_acm_evidence_v1", state="not_seen",
                     binding_sha256=self.prepared["binding_sha256"])
        raw = self.patch(self.m.owner, "strict_private", return_value=value)
        self.assertEqual(classify(self.run, self.prepared, transfer_proved=True), "not_seen")
        raw.assert_called_once_with(receipt, compact=True)
        self.acm.validate.assert_called_once_with(value, self.run, self.prepared)
        with self.assertRaises(self.m.owner.Stop):
            classify(self.run, self.prepared, transfer_proved=False)
        value["binding_sha256"] = "b" * 64
        with self.assertRaises(self.m.owner.Stop):
            classify(self.run, self.prepared, transfer_proved=True)
        self.acm.validate.assert_called_once()

    def test_terminal_counts_and_usb_are_independent(self):
        stage = self.patch(self.m.stage, "first_return")
        acm = self.patch(self.m, "observe_acm_result")
        for state, counts, usb, expected, flags in (
            ("ambiguous", (4, 4), "pid1_exact", "ACM_PID1", (False, False)),
            ("paired", (1, 1), "observation_gap", "FDT_AND_POPULATED_ROOT", (True, True)),
            ("unflatten_only", (0, 1), "not_seen", "POPULATED_ROOT", (False, True)),
            ("fdt_only", (1, 0), "pid1_exact", "FDT_AND_ACM_PID1", (True, False)),
            ("capture_cut", (None, None), "unproved", None, (False, False)),
        ):
            with self.subTest(state=state, usb=usb), self.m.stage.bound_run(self.run):
                log = {"state": state}
                if counts != (None, None):
                    log.update(fdt_count=counts[0], unflatten_count=counts[1])
                stage.return_value = log
                acm.return_value = usb
                self.engine.read_json.side_effect = [log, self.prepared, self.final, log]
                result = self.m.witness_result(self.run, self.prepared, self.final, transfer_proved=True)
                self.assertEqual((result["fdt_count"], result["unflatten_count"]), counts)
                self.assertEqual((result["fdt_proved"], result["populated_root_proved"]), flags)
                self.assertEqual((result["usb_pid1"], result["first_return"]), (usb, state))
                verdict, passed = self.m.verdict("odin_transfer_completed", "NO_PROOF", True)
                prefix = "NO_PROOF_Y2Q_CSTAGE" if expected is None else "PROVED_Y2Q_CSTAGE_" + expected
                self.assertEqual(verdict, prefix + "_ORIGINAL_MAGISK_RETURNED")
                self.assertIs(passed, expected is not None)

    def test_result_wrapper_does_not_refinalize_an_inner_terminal(self):
        result = {"schema": "s20plus_g986n_b0_terminal_v1", "binding_sha256": "a" * 64}
        execute = self.patch(self.m.previous, "execute", return_value=result)
        restore = self.patch(self.m.previous, "restore", return_value=result)
        render = self.patch(self.m, "render", side_effect=lambda result, run: result)
        self.assertIs(self.m.execute(self.run, "approval"), result)
        execute.assert_called_once_with(self.run, "approval")
        restore.assert_not_called()
        self.assertIs(self.m.restore(self.run), result)
        restore.assert_called_once_with(self.run)
        self.assertEqual(render.call_count, 2)
        self.engine.finalize_resident.assert_not_called()

    def test_archived_restore_reports_both_results_and_keeps_the_terminal(self):
        m = self.m
        self.patch(m.base, "accepted")
        self.patch(m.owner, "GUARD", self.run / "not-present")
        self.patch(m, "candidate_transfer_proved", return_value=True)
        observations = {"state": "ambiguous", "fdt_count": 2, "unflatten_count": 2}
        self.patch(m.stage, "first_return", return_value=observations)
        ticket_receipt = self.ticket / m.ACM_SUMMARY
        value = dict(schema="s20plus_cstage_acm_evidence_v1", state="pid1_exact",
                     binding_sha256=self.prepared["binding_sha256"])
        self.patch(m.owner, "strict_private", return_value=value)
        self.engine.read_json.side_effect = lambda path, label: {
            "prepared.json": self.prepared, "final-health.json": self.final,
            m.stage.paths("return")[2]: observations,
        }[path.name]

        def archived(run):
            with m.stage.bound_run(run):
                verdict, passed = m.verdict("odin_transfer_completed", "NO_PROOF", True)
            return dict(schema="s20plus_g986n_b0_terminal_v1", binding_sha256=self.prepared["binding_sha256"],
                        verdict=verdict, experiment_pass=passed)

        # The retained immutable archive is covered separately by its original integration test.
        terminal_validator = self.patch(m.previous, "archived_terminal", side_effect=archived)
        (self.run / "terminal.json").touch()
        for state, passed in (("observation_gap", False), ("pid1_exact", True)):
            with self.subTest(state=state), redirect_stdout(io.StringIO()) as output:
                if passed:
                    ticket_receipt.touch()
                result = m.restore(self.run)
                self.assertIs(result["experiment_pass"], passed)
                self.assertEqual(json.loads(output.getvalue()), {
                    "status": "CSTAGE_WITNESSES", "usb_pid1": state, "first_return": "ambiguous",
                    "fdt_count": 2, "unflatten_count": 2, "fdt_proved": False, "populated_root_proved": False,
                })
        self.assertEqual(terminal_validator.call_count, 2)
        self.assertEqual(self.acm.validate.call_count, 2)
        self.acm.observe.assert_not_called()
        self.acm.host_serial_policy.assert_not_called()
        self.engine.finalize_resident.assert_not_called()

    def test_dormant_cli_cannot_launch_broker(self):
        self.patch(self.m.base, "bind")
        self.patch(self.m, "ACTIVE", False)
        with self.assertRaises(self.m.owner.Stop):
            self.m.main(["--execute", "--run-dir", str(self.run), "--approval", "invalid"])
        self.acm.launch.assert_not_called()

    def test_real_binding_picks_cstage_reader_and_retained_rollback(self):
        if not self.m.PAIR.is_file():
            self.skipTest("requires the retained candidate pair")
        child = r"""import s20plus_g986n_cstage_list_f1 as m
m.bind()
assert m.stage.reader.STAGES == ('fdt', 'unflatten')
assert m.owner.PAIR == m.PAIR and m.owner.PROFILE == m.PROFILE
assert m.owner.observe_candidate is m.observe and m.owner.terminal_verdict is m.verdict
assert m.base.prepare is m.prepare
assert m.stage._configure_runtime.__code__.co_filename == str(m.SCRIPT)
assert m.owner.checked_terminal is m.stage.publish and m.stage.make_intent is m.base.scan_intent
scope = m.owner.effect_profile()
assert scope['sites'] == ['fdt', 'unflatten'] and scope['candidate_dwell_seconds'] == 180
assert scope['approval_seconds'] == 900 and scope['scan_deadline_seconds'] == 120
assert scope['candidate_host_commands'] == 0 and scope['candidate_and_rollback_replay'] is False
assert scope['physical_download_only_after_candidate'] and not scope['rebind']
assert scope['host_serial_policy_checks'] == ['prepare', 'initial-reboot', 'candidate-transfer']
assert m.owner.read_pair()['rollback']['ap']['sha256'] == m.ORIGINAL
raw = m.owner.retained_runtime_source()
assert m.SCRIPT.name.encode() in raw
boundary = b'if name in ("initial-reboot", "candidate-transfer"):\n                    _early_effect_deadline(Path(capture_dir))\n                result = original(argv, capture_dir, name, **kwargs)'
assert raw.count(boundary)==1 and raw.count(b'_early_effect_deadline(Path(capture_dir))')==1
"""
        subprocess.run([sys.executable, "-B", "-c", child], cwd=SCRIPTS, check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
