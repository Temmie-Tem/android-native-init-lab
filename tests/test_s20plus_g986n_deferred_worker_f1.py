"""Offline business and normal-entry tests. No device transport is opened."""
from contextlib import ExitStack
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
import s20plus_g986n_deferred_worker_f1 as m


class DeferredWorkerProfile(unittest.TestCase):
    def test_distinct_verdicts_and_original_only(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            run = Path(folder)
            stack.enter_context(m.stage.bound_run(run))
            engine = stack.enter_context(patch.object(m.owner, "engine", create=True))
            engine.read_json.return_value = {}
            witness = stack.enter_context(patch.object(m, "witness_result"))
            for operation, flush, user, usb, expected in (
                (None, False, False, "observation_gap", []),
                ("enter", False, False, "not_seen", ["WORKER_ENTER"]),
                ("return", True, False, "not_seen", ["WORKER_RETURN", "FLUSH1_RETURN"]),
                (None, True, True, "pid1_exact", ["FLUSH1_RETURN", "EL0_PID1", "ACM_PID1"]),
            ):
                witness.return_value = dict(worker_sample=dict(operation=operation) if operation else None,
                                            first_flush_return_observed=flush, el0_getpid_entry_observed=user, usb_pid1=usb)
                verdict, accepted = m.verdict("odin_transfer_completed", "NO_PROOF", True)
                self.assertEqual(accepted, bool(expected))
                for label in expected:
                    self.assertIn(label, verdict)
                self.assertNotIn("LAST_BOOT", verdict)
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "NO_PROOF", False)

    def test_return_evidence_must_match_and_transfer_must_be_proved(self):
        reader = m.stage.load(m.READER, "_deferred_reader_test", m.READER_SHA)
        log = {"state": "run_window", "pid_sample": {"milestones": 8},
               "worker_sample": {"device_id": "81234567", "operation": "enter"}}
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            run = Path(folder)
            engine = stack.enter_context(patch.object(m.owner, "engine", create=True))
            stack.enter_context(patch.object(m.stage, "reader", reader))
            stack.enter_context(patch.object(m.stage, "first_return", return_value=log))
            stack.enter_context(patch.object(m.cstage, "observe_acm_result", return_value="observation_gap"))
            engine.read_json.return_value = {"state": "capture_cut"}
            with self.assertRaises(m.owner.Stop):
                m.witness_result(run, {}, {}, transfer_proved=True)
            engine.read_json.return_value = log
            result = m.witness_result(run, {}, {}, transfer_proved=False)
            self.assertIsNone(result["worker_sample"])
            self.assertFalse(result["first_flush_return_observed"])
            with patch.object(m.base, "pinned", return_value=b'{"direct_soc_names":{}}'):
                result = m.witness_result(run, {}, {}, transfer_proved=True)
            self.assertEqual(result["worker_name_candidates"], [])
            self.assertEqual(result["cohort"], "individual_run_samples")

    def test_actual_dispatch_and_fresh_witness(self):
        if not m.PAIR.exists():
            self.skipTest("requires the private packaged candidate")
        program = """
from unittest.mock import patch, MagicMock
import s20plus_g986n_deferred_worker_f1 as m
m.ACTIVE=True
m.bind()
assert m.stage.reader.FILTER==m.FILTER and m.owner.review_identity is m.review
assert m.stage._configure_runtime.__code__.co_filename==str(m.SCRIPT) and m.stage._configure_runtime.__name__=="_configure_runtime"
assert m.owner.checked_terminal is m.stage.publish and m.owner.terminal_verdict is m.verdict
assert m.base.prepare is m.cstage.prepare and m.base.restore is m.cstage.restore
assert m.owner.ACTIVATION==m.RUN_ROOT/'activation.json' and m.owner.SCRIPT==m.SCRIPT
assert m.owner.effect_profile()['byte_stores_max']==21976 and m.stage.reader.STAGES==('run_anchor',)
acm=m.parent.observer()
serial,banner=acm.witness()
assert serial=='y2q-'+m.pair()['nonce'] and serial.encode()[4:] in banner
assert acm.PROFILE==m.PROFILE and acm.CANDIDATE==m.CANDIDATE and acm.RUN_ROOT==m.RUN_ROOT
assert m.calibrated_identity() and m.SCRIPT.name.encode() in m.owner.retained_runtime_source()
expected=['--execute','--run-dir',str(m.RUN_ROOT/'run-1234567890123456789'),'--approval','fake']
child=MagicMock()
child.__enter__.return_value=child
child.poll.return_value=0
child.wait.return_value=17
with patch.object(m.owner,'namespace',return_value=['fixture-namespace']) as ns, patch.object(acm.subprocess,'Popen',return_value=child) as launch:
    try: m.main(expected)
    except SystemExit as e: assert e.code==17
    else: raise AssertionError('production launch path omitted')
    assert ns.call_count==2 and all(c.args==(expected,) and c.kwargs=={'connected':True} for c in ns.call_args_list)
    launch.assert_called_once()
"""
        subprocess.run([sys.executable, "-B", "-c", program], cwd=SCRIPTS, check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
