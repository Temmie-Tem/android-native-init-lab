"""Host-only tests for the y2q basic-setup owner and result semantics."""

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
OLD_READER = PRIVATE / "analysis/s20plus-y2q-early-pair-20261126/retained-reader/return_stage.py"
sys.path.insert(0, str(SCRIPTS))


@unittest.skipUnless(OLD_READER.is_file(), "requires the retained S20+ profiles")
class BasicSetupOwner(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_basic_setup_f1 as profile

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
            record.update(zip(self.m.COUNTS, counts, strict=True))
        self.return_log.return_value = record
        self.engine.read_json.side_effect = lambda path, label: {
            "prepared.json": self.prepared,
            "final-health.json": self.final,
            self.m.stage.paths("return")[2]: record,
        }[path.name]

    def test_milestones_and_acm_remain_independent_of_layout_counts(self):
        m = self.m
        for state, counts, acm, labels in (
            ("complete", (4, 4, 4, 4, 4, 4), "not_seen", ("DT_READY", "BASIC_SETUP_CALL_SITE", "BASIC_SETUP_RETURN")),
            ("complete", (4, 4, 4, 0, 0, 0), "not_seen", ("DT_READY", "BASIC_SETUP_CALL_SITE", "BASIC_SETUP_RETURN")),
            ("complete", (0, 0, 1, 0, 0, 0), "observation_gap", ("BASIC_SETUP_RETURN",)),
            ("complete", (0, 1, 0, 0, 0, 0), "pid1_exact", ("BASIC_SETUP_CALL_SITE", "ACM_PID1")),
            ("no_record", (0, 0, 0, 0, 0, 0), "pid1_exact", ("ACM_PID1",)),
            ("no_record", (0, 0, 0, 0, 0, 0), "not_seen", ()),
            ("capture_cut", None, "unproved", ()),
        ):
            with self.subTest(state=state, counts=counts, acm=acm), m.stage.bound_run(self.run):
                self.saved_return(state, counts)
                self.acm.return_value = acm
                proof = m.witness_result(self.run, self.prepared, self.final, transfer_proved=True)
                self.assertEqual(tuple(proof[key] for key in m.COUNTS), counts or (None,) * len(m.COUNTS))
                self.assertEqual(proof["usb_pid1"], acm)
                self.assertEqual(proof["first_return"], state)
                self.assertEqual(tuple(proof[key + "_observed"] for key in m.STAGES),
                                 tuple(value > 0 for value in counts[:3]) if counts else (False,) * 3)
                verdict, passed = m.verdict("odin_transfer_completed", "NO_PROOF", True)
                prefix = "PROVED_Y2Q_" + "_AND_".join(labels) if labels else "NO_PROOF_Y2Q_BASIC_SETUP"
                self.assertEqual(verdict, prefix + "_ORIGINAL_MAGISK_RETURNED")
                self.assertIs(passed, bool(labels))

    def test_unproved_transfer_and_rollback_do_not_yield_a_stage_proof(self):
        m = self.m
        self.saved_return("complete", (1, 1, 1, 1, 1, 1))
        self.acm.return_value = "transfer_unproved"
        with m.stage.bound_run(self.run):
            self.assertFalse(m.verdict("unknown", "NO_PROOF", True)[1])
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "NO_PROOF", False)
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "PROVED", True)

    def test_archive_render_retains_gap_without_reopening_acm_or_return_scan(self):
        m = self.m
        self.saved_return("observation_gap", None)
        self.acm.return_value = "observation_gap"
        self.patch(m.cstage, "candidate_transfer_proved", return_value=True)
        capture = self.patch(m.stage, "acquire")
        acm = self.patch(m.cstage, "observer")
        terminal = {"schema": "s20plus_g986n_b0_terminal_v1", "binding_sha256": "a" * 64}
        with redirect_stdout(io.StringIO()) as output:
            self.assertIs(m.render(terminal, self.run), terminal)
            value = json.loads(output.getvalue())
        self.assertEqual(value["first_return"], "observation_gap")
        self.assertTrue(all(value[key] is None for key in m.COUNTS))
        capture.assert_not_called()
        acm.assert_not_called()
        self.engine.finalize_resident.assert_not_called()

    def test_calibration_checks_both_prior_scans_and_the_original_rollback(self):
        m = self.m
        self.assertEqual(set(m.calibrated_identity()), set(m.stage.IDENTITY))
        pinned = m.base.pinned
        target = "mainline-baseline-evidence.json"

        def altered(path, pin):
            raw = pinned(path, pin)
            if path.name == target:
                record = json.loads(raw)
                record["adjacent_pair_count"] = 1
                raw = json.dumps(record).encode()
            return raw

        self.patch(m.base, "pinned", side_effect=altered)
        for target in ("mainline-baseline-evidence.json", "mainline-return-evidence.json"):
            with self.subTest(target=target), self.assertRaises(m.owner.Stop):
                m.calibrated_identity()

    def test_dormant_never_invokes_the_namespace_or_broker(self):
        m = self.m
        self.patch(m, "ACTIVE", False)
        self.patch(m.base, "bind")
        profile, _, _ = m.inherited()
        self.patch(profile, "bind")
        launch = self.patch(profile, "observer")
        namespace = self.patch(m.owner, "namespace")
        with self.assertRaises(m.owner.Stop):
            m.main(["--execute", "--run-dir", str(self.run), "--approval", "invalid"])
        namespace.assert_not_called()
        launch.assert_not_called()

    def test_exact_retained_outer_launch_uses_new_acm_and_device_effect_profile(self):
        code = r"""from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import s20plus_g986n_basic_setup_f1 as m
import s20plus_g986n_pid1_stage_f1 as historical
from pathlib import Path
profile,_,_=m.inherited()
assert profile is not historical
expected=['--execute','--run-dir',str(m.RUN_ROOT/'run-1234567890123456789'),'--approval','token']
m.ACTIVE=True  # Host fixture. Owner bytes and activation are untouched.
namespace=['fake-source-view']
child=MagicMock()
child.__enter__.return_value=child
child.poll.return_value=0
child.wait.return_value=17
probe=SimpleNamespace(FILTER=m.FILTER,STAGES=m.STAGES)
with patch.object(m,'PAIR',profile.PAIR), patch.object(profile,'reader',return_value=probe):
    m.bind()
    acm=profile.observer()
    with patch.object(m.owner,'namespace',return_value=namespace) as ns, \
            patch.object(acm.subprocess,'Popen',return_value=child) as launch:
        try:
            m.main(['--approval','token',*expected[:3]])
        except SystemExit as e:
            assert e.code==17
        else:
            raise AssertionError('real ACM launch did not return child outcome')
        assert ns.call_count==2 and all(call.args==(expected,) and call.kwargs=={'connected':True}
                                       for call in ns.call_args_list)
        launch.assert_called_once()
        assert launch.call_args.args==(namespace,) and 'stdin' in launch.call_args.kwargs
        assert launch.call_args.kwargs['env']==m.base.view.clean_environment()
o,s,b=m.owner,m.stage,m.base
assert o.SCRIPT==m.SCRIPT and o.PROFILE==m.PROFILE and o.RUN_ROOT==m.RUN_ROOT
assert o.ACTIVATION==m.RUN_ROOT/'activation.json' and o.TEST_SOURCE==m.TEST
assert o.read_pair is m.pair and o.review_identity is m.review and o.terminal_verdict is m.verdict
assert acm.PROFILE==m.PROFILE and acm.RUN_ROOT==m.RUN_ROOT and acm.CANDIDATE==m.CANDIDATE
assert historical.PROFILE==m.PREDECESSOR_PROFILE and historical.SCRIPT==m.PREDECESSOR
assert s.reader is probe and s._configure_runtime.__code__.co_filename==str(m.SCRIPT)
assert o.checked_terminal is s.publish and s.make_intent is b.scan_intent
assert b.prepare is m.cstage.prepare and b.execute is m.cstage.execute and b.restore is m.cstage.restore
assert s.APPROVAL=='S20PLUS-G986N-BASIC-SETUP-BOUND:' and s.CONFIRM=='S20PLUS-G986N-BASIC-SETUP-ARRIVAL:'
scope=o.effect_profile()
assert scope['sites']==list(m.STAGES) and scope['diagnostic_bytes_per_kernel_entry']==240
assert scope['candidate_dwell_seconds']==180 and scope['approval_seconds']==900
assert scope['return_scans']==1 and scope['scan_deadline_seconds']==120
assert scope['physical_download_only_after_candidate'] and not scope['rebind']
assert scope['candidate_and_rollback_replay'] is False and scope['candidate_host_commands']==0
raw=o.retained_runtime_source()
assert m.SCRIPT.name.encode() in raw
assert raw.count(b'if name in ("initial-reboot", "candidate-transfer"):\n                    _early_effect_deadline(Path(capture_dir))')==1
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=SCRIPTS, check=True, timeout=30)

    def test_standalone_owner_consumes_actual_three_slot_package(self):
        if not self.m.PAIR.is_file():
            self.skipTest("requires the exact basic-setup candidate package")
        code = """import s20plus_g986n_basic_setup_f1 as m
m.bind()
package=m.owner.read_pair()
assert package['candidate']['ap']['sha256']==m.CANDIDATE and package['rollback']['ap']['sha256']==m.ORIGINAL
probe=m.stage.reader
frames=probe.frames(package['nonce'])
assert probe.STAGES==m.STAGES==tuple(frames) and set(map(len,frames.values()))=={80}
output=probe.parse(0,b'y2q_basic_v1=2097136,1,2,1,1,1,0\\n',b'')
assert output['state']=='complete' and tuple(output[key] for key in m.COUNTS)==(1,2,1,1,1,0)
empty=probe.parse(0,b'y2q_basic_v1=2097136,0,0,0,0,0,0\\n',b'')
assert empty['state']=='no_record' and all(empty[key]==0 for key in m.COUNTS)
assert m.inherited()[0].reader() is probe
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=SCRIPTS, check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
