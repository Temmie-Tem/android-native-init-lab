"""Host-only tests for the later y2q stage owner and proof taxonomy."""

from contextlib import ExitStack, redirect_stdout
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
PRIVATE = ROOT / "workspace/private"
INHERITED_READER = PRIVATE / "analysis/s20plus-y2q-early-pair-20261126/retained-reader/return_stage.py"
sys.path.insert(0, str(SCRIPTS))


@unittest.skipUnless(INHERITED_READER.is_file(), "requires the retained S20+ capability")
class PID1StageOwner(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_pid1_stage_f1 as profile

        self.m = profile
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        scratch = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.run = scratch / "run-1234567890123456789"
        self.run.mkdir()
        self.prepared = {"binding_sha256": "a" * 64}
        self.final = {"rollback_transfer_completed": True}
        self.engine = self.patch(profile.owner, "engine", Mock(), create=True)
        self.acm = self.patch(profile.cstage, "observe_acm_result")
        self.return_log = self.patch(profile.stage, "first_return")

    def patch(self, obj, name, *args, **kwargs):
        return self.stack.enter_context(patch.object(obj, name, *args, **kwargs))

    def saved_return(self, state, counts):
        record = dict(state=state)
        if counts is not None:
            record.update(zip(("exec_attempt_count", "el0_getpid_count", "adjacent_pair_count"), counts))
        self.return_log.return_value = record
        self.engine.read_json.side_effect = lambda path, label: {
            "prepared.json": self.prepared,
            "final-health.json": self.final,
            self.m.stage.paths("return")[2]: record,
        }[path.name]

    def test_counts_and_execution_evidence_are_independent(self):
        m = self.m
        for state, counts, acm, classification, proofs in (
            ("complete", (4, 4, 4), "not_seen", "EL0_PID1_GETPID", (True, True)),
            ("complete", (4, 4, 1), "pid1_exact", "EL0_PID1_GETPID_AND_ACM_PID1", (True, True)),
            ("complete", (4, 4, 0), "not_seen", None, (True, False)),
            ("complete", (1, 0, 0), "observation_gap", None, (True, False)),
            ("complete", (0, 1, 0), "not_seen", None, (False, False)),
            ("no_record", (0, 0, 0), "pid1_exact", "ACM_PID1", (False, False)),
            ("capture_cut", None, "unproved", None, (False, False)),
            ("unreadable", None, "not_seen", None, (False, False)),
        ):
            with self.subTest(state=state, counts=counts, acm=acm), m.stage.bound_run(self.run):
                self.saved_return(state, counts)
                self.acm.return_value = acm
                proof = m.witness_result(self.run, self.prepared, self.final, transfer_proved=True)
                self.assertEqual((proof["exec_attempt_count"], proof["el0_getpid_count"],
                                  proof["adjacent_pair_count"]), counts or (None,) * 3)
                self.assertEqual((proof["first_return"], proof["usb_pid1"]), (state, acm))
                self.assertEqual((proof["exec_attempt_observed"], proof["el0_getpid_entry_proved"]), proofs)
                verdict, passed = m.verdict("odin_transfer_completed", "NO_PROOF", True)
                expected = ("PROVED_Y2Q_" + classification) if classification else (
                    "NO_PROOF_Y2Q_PID1_EXEC_ATTEMPT_OBSERVED" if proofs[0] else "NO_PROOF_Y2Q_PID1_STAGE"
                )
                self.assertEqual(verdict, expected + "_ORIGINAL_MAGISK_RETURNED")
                self.assertIs(passed, classification is not None)

    def test_unproved_transfer_and_original_cannot_yield_el0_proof(self):
        m = self.m
        self.saved_return("complete", (1, 1, 1))
        self.acm.return_value = "transfer_unproved"
        with m.stage.bound_run(self.run):
            self.assertFalse(m.verdict("unknown", "NO_PROOF", True)[1])
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "NO_PROOF", False)
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "PROVED", True)

    def test_gap_is_reported_without_reacquiring_any_observation(self):
        m = self.m
        self.saved_return("observation_gap", None)
        self.acm.return_value = "observation_gap"
        self.patch(m.cstage, "candidate_transfer_proved", return_value=True)
        acquire = self.patch(m.stage, "acquire")
        observer = self.patch(m.cstage, "observer")
        terminal = {"schema": "s20plus_g986n_b0_terminal_v1", "binding_sha256": "a" * 64}
        with redirect_stdout(io.StringIO()) as output:
            self.assertIs(m.render(terminal, self.run), terminal)
            report = json.loads(output.getvalue())
        self.assertEqual(report["first_return"], "observation_gap")
        self.assertIsNone(report["adjacent_pair_count"])
        acquire.assert_not_called()
        observer.assert_not_called()
        self.engine.finalize_resident.assert_not_called()

    def test_latest_original_requires_the_same_cstage_return_and_adjacency(self):
        m = self.m
        first = m.calibrated_identity()
        self.assertEqual(set(first), set(m.stage.IDENTITY))
        original = m.base.pinned

        def altered(path, pin):
            raw = original(path, pin)
            if path == m.ADJACENCY:
                record = json.loads(raw)
                record["binding"]["boot_id_sha256"] = "b" * 64
                raw = json.dumps(record).encode()
            return raw

        self.patch(m.base, "pinned", side_effect=altered)
        with self.assertRaises(m.owner.Stop):
            m.calibrated_identity()

    def test_dormant_profile_does_not_launch(self):
        m = self.m
        self.patch(m.base, "bind")
        self.patch(m, "ACTIVE", False)
        broker = self.patch(m, "observer")
        namespace = self.patch(m.owner, "namespace")
        with self.assertRaises(m.owner.Stop):
            m.main(["--execute", "--run-dir", str(self.run), "--approval", "invalid"])
        namespace.assert_not_called()
        broker.assert_not_called()

    def test_bind_reuses_cstage_cuts_with_new_reader_and_candidate_authority(self):
        child = r"""from types import SimpleNamespace
from unittest.mock import patch
import s20plus_g986n_pid1_stage_f1 as m
c,b,o,s=m.cstage,m.base,m.owner,m.stage
probe=SimpleNamespace(FILTER=m.FILTER, STAGES=m.STAGES)
with patch.object(m, 'reader', return_value=probe):
    with patch.object(m, 'PAIR', c.PAIR):
        m.bind()
assert o.SCRIPT==m.SCRIPT and o.PROFILE==m.PROFILE and o.RUN_ROOT==m.RUN_ROOT
assert o.ACTIVATION==m.RUN_ROOT/'activation.json' and o.TEST_SOURCE==m.TEST
assert o.read_pair is m.pair and o.review_identity is m.review and o.terminal_verdict is m.verdict
assert s.reader is probe and s._configure_runtime.__code__.co_filename==str(m.SCRIPT)
assert o.checked_terminal is s.publish and s.make_intent is b.scan_intent
assert b.prepare is c.prepare and b.execute is c.execute and b.restore is c.restore
assert c.observer is m.observer and c.render is m.render and o.observe_candidate is c.observe
assert s.APPROVAL=='S20PLUS-G986N-PID1-STAGE-BOUND:' and s.CONFIRM=='S20PLUS-G986N-PID1-STAGE-ARRIVAL:'
scope=o.effect_profile()
assert scope['sites']==list(m.STAGES) and scope['candidate_dwell_seconds']==180
assert scope['physical_download_only_after_candidate'] and not scope['rebind']
assert scope['candidate_and_rollback_replay'] is False and scope['candidate_host_commands']==0
assert scope['approval_seconds']==900 and scope['return_scans']==1 and scope['scan_deadline_seconds']==120
raw=o.retained_runtime_source()
assert m.SCRIPT.name.encode() in raw
assert raw.count(b'if name in ("initial-reboot", "candidate-transfer"):\n                    _early_effect_deadline(Path(capture_dir))')==1
"""
        subprocess.run([sys.executable, "-B", "-c", child], cwd=SCRIPTS, check=True, timeout=30)

    def test_outer_execute_invokes_exact_specialized_acm_broker(self):
        child = r"""from unittest.mock import MagicMock, patch
import s20plus_g986n_pid1_stage_f1 as m
m.ACTIVE=True  # Host fixture. The owner file and active receipts are unmodified.
expected=['--execute','--run-dir',str(m.RUN_ROOT/'run-1234567890123456789'),'--approval','token']
namespace=['fake-source-view']
process=MagicMock()
process.__enter__.return_value=process
process.poll.return_value=0
process.wait.return_value=17
with patch.object(m, 'PAIR', m.cstage.PAIR):
    from types import SimpleNamespace
    with patch.object(m, 'reader', return_value=SimpleNamespace(FILTER=m.FILTER,STAGES=m.STAGES)):
        acm=m.observer()
        with patch.object(m.owner,'namespace',return_value=namespace) as ns, \
                patch.object(acm.subprocess,'Popen',return_value=process) as launch:
            try:
                m.main(['--approval','token',*expected[:3]])
            except SystemExit as exc:
                assert exc.code==17
            else:
                raise AssertionError('real ACM launch did not return child outcome')
            assert ns.call_count==2 and all(call.args==(expected,) and call.kwargs=={'connected':True}
                                          for call in ns.call_args_list)
            launch.assert_called_once()
            assert launch.call_args.args==(namespace,)
            assert launch.call_args.kwargs['env']==m.base.view.clean_environment()
            assert 'stdin' in launch.call_args.kwargs
        assert acm.PROFILE==m.PROFILE and acm.RUN_ROOT==m.RUN_ROOT
        assert acm.CANDIDATE==m.CANDIDATE
"""
        subprocess.run([sys.executable, "-B", "-c", child], cwd=SCRIPTS, check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
