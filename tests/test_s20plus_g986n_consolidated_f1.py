"""Host-only tests for the consolidated y2q owner and fresh ACM identity."""

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
PREVIOUS_READER = PRIVATE / "analysis/s20plus-y2q-early-pair-20261126/retained-reader/return_stage.py"
sys.path.insert(0, str(SCRIPTS))


@unittest.skipUnless(PREVIOUS_READER.is_file(), "requires the retained S20+ profiles")
class ConsolidatedOwner(unittest.TestCase):
    def setUp(self):
        import s20plus_g986n_consolidated_f1 as owner

        self.m = owner
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        scratch = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.run = scratch / "run-1234567890123456789"
        self.run.mkdir()
        self.prepared = {"binding_sha256": "a" * 64}
        self.final = {"rollback_transfer_completed": True}
        self.engine = self.patch(owner.owner, "engine", Mock(), create=True)
        self.acm = self.patch(owner.cstage, "observe_acm_result")
        self.return_log = self.patch(owner.stage, "first_return")
        self.describe = Mock()
        self.patch(owner.inherited().profile, "reader", return_value=Mock(describe=self.describe))

    def patch(self, obj, name, *args, **kwargs):
        return self.stack.enter_context(patch.object(obj, name, *args, **kwargs))

    def saved_return(self, record):
        self.return_log.return_value = record
        self.engine.read_json.side_effect = lambda path, label: {
            "prepared.json": self.prepared,
            "final-health.json": self.final,
            self.m.stage.paths("return")[2]: record,
        }[path.name]

    def test_one_bitmap_projection_and_independent_acm(self):
        m = self.m
        for state, anchor, records, milestones, usb, proof in (
            ("complete", 4, 0, [], "not_seen", "BASIC_SETUP_CALL_SITE"),
            ("complete", 0, 3, ["basic_enter", "driver_ready"], "not_seen", "KERNEL_PROGRESS"),
            ("complete", 1, 2, ["exec_attempt", "el0_getpid"], "unproved", "EL0_PID1_GETPID"),
            ("no_record", 0, 0, [], "pid1_exact", "ACM_PID1"),
            ("complete", 1, 2, ["exec_attempt", "el0_getpid"], "pid1_exact", "EL0_PID1_GETPID_AND_ACM_PID1"),
            ("no_record", 0, 0, [], "not_seen", None),
        ):
            with self.subTest(state=state, records=records, usb=usb), m.stage.bound_run(self.run):
                self.saved_return(dict(state=state, size=2097136, anchor_count=anchor,
                                       record_count=records, bitmap="10" * 40))
                self.acm.return_value = usb
                self.describe.reset_mock()
                self.describe.return_value = {"milestones": milestones, "entry_count": 7, "return_count": 6,
                                              "highest_enter": 6, "highest_return": 5}
                rendered = m.witness_result(self.run, self.prepared, self.final, transfer_proved=True)
                self.assertEqual(rendered["usb_pid1"], usb)
                self.assertIs(rendered["cumulative_trace_observed"], records > 0)
                self.assertIs(rendered["el0_getpid_entry_proved"], "el0_getpid" in milestones)
                self.assertNotIn("bitmap", rendered)
                if records:
                    self.describe.assert_called_once_with("10" * 40)
                else:
                    self.describe.assert_not_called()
                verdict, passed = m.verdict("odin_transfer_completed", "NO_PROOF", True)
                expected = ("PROVED_Y2Q_CONSOLIDATED_" + proof) if proof else "NO_PROOF_Y2Q_CONSOLIDATED"
                self.assertEqual(verdict, expected + "_ORIGINAL_MAGISK_RETURNED")
                self.assertIs(passed, proof is not None)

    def test_unproved_transfer_and_post_twrp_gap_do_not_start_another_scan(self):
        m = self.m
        self.saved_return(dict(state="complete", anchor_count=1, record_count=1, bitmap="ff" * 40))
        self.acm.return_value = "transfer_unproved"
        with m.stage.bound_run(self.run):
            self.assertFalse(m.verdict("unknown", "NO_PROOF", True)[1])
            with self.assertRaises(m.owner.Stop):
                m.verdict("odin_transfer_completed", "NO_PROOF", False)
        self.saved_return(dict(state="observation_gap"))
        self.acm.return_value = "observation_gap"
        self.patch(m.cstage, "candidate_transfer_proved", return_value=True)
        scan = self.patch(m.stage, "acquire")
        terminal = {"schema": "s20plus_g986n_b0_terminal_v1", "binding_sha256": "a" * 64}
        with redirect_stdout(io.StringIO()) as output:
            self.assertIs(m.render(terminal, self.run), terminal)
        value = json.loads(output.getvalue())
        self.assertEqual(value["first_return"], "observation_gap")
        self.assertIsNone(value["progress"])
        scan.assert_not_called()
        self.describe.assert_not_called()
        self.engine.finalize_resident.assert_not_called()

    def test_same_boot_calibration_preserves_separate_d0_attribution(self):
        m = self.m
        self.assertEqual(set(m.calibrated_identity()), set(m.stage.IDENTITY))
        pinned = m.base.pinned

        def altered(path, pin):
            raw = pinned(path, pin)
            if path == m.READBACK:
                record = json.loads(raw)
                record["first_return_attributed"] = True
                return json.dumps(record).encode()
            return raw

        self.patch(m.base, "pinned", side_effect=altered)
        with self.assertRaises(m.owner.Stop):
            m.calibrated_identity()

    def test_dormant_execute_stops_before_broker(self):
        m = self.m
        self.patch(m, "ACTIVE", False)
        self.patch(m.base, "bind")
        retained = m.inherited()
        self.patch(retained.basic, "bind")
        self.patch(retained.profile, "bind")
        broker = self.patch(retained.profile, "observer")
        namespace = self.patch(m.owner, "namespace")
        with self.assertRaises(m.owner.Stop):
            m.main(["--execute", "--run-dir", str(self.run), "--approval", "invalid"])
        namespace.assert_not_called()
        broker.assert_not_called()

    def test_actual_outer_launch_and_raw_acm_accept_only_fresh_ram_init(self):
        code = r"""from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import hashlib
import s20plus_g986n_consolidated_f1 as m
r=m.inherited()
old=m.stage.load(m.cstage.OBSERVER, '_consolidated_test_old_acm', m.cstage.OBSERVER_SHA)
old_serial, old_banner=old.witness()
nonce='1'*32
expected=['--execute','--run-dir',str(m.RUN_ROOT/'run-1234567890123456789'),'--approval','token']
m.ACTIVE=True  # Host fixture. The owner file and activation remain untouched.
namespace=['fake-source-view']
child=MagicMock()
child.__enter__.return_value=child
child.poll.return_value=0
child.wait.return_value=17
probe=SimpleNamespace(FILTER=m.FILTER,STAGES=m.STAGES)
with TemporaryDirectory() as scratch:
    header=Path(scratch)/'build-id.h'
    raw=f'#define Y2Q_BUILD_ID "{nonce}"\n'.encode()
    header.write_bytes(raw)
    header_sha=hashlib.sha256(raw).hexdigest()
    with patch.object(m,'PAIR',r.basic.PAIR), patch.object(m,'pair',return_value={'nonce':nonce}), \
            patch.object(r.profile,'reader',return_value=probe), patch.object(m,'HEADER',header), \
            patch.object(m,'HEADER_SHA',header_sha):
        m.bind()
        acm=m.observer()
        serial,banner=acm.witness()
        assert serial=='y2q-'+nonce and serial!=old_serial and banner!=old_banner
        assert acm.HEADER==header and acm.HEADER_SHA==header_sha
        intent={'binding_sha256':'2'*64,'start_us':1}
        def sample(data):
            return dict(**intent, state='pid1_exact', size=len(data), stream_hex=data.hex(),
                        stream_sha256=acm.sha(data),endpoint_before='a'*64,endpoint_after='a'*64,verified_us=10)
        assert acm.derive(sample(banner),intent)['state']=='pid1_exact'
        try:
            acm.derive(sample(old_banner),intent)
        except m.owner.Stop:
            pass
        else:
            raise AssertionError('historical banner accepted')
        with patch.object(m.owner,'namespace',return_value=namespace) as ns, \
                patch.object(acm.subprocess,'Popen',return_value=child) as launch:
            try:
                m.main(['--approval','token',*expected[:3]])
            except SystemExit as e:
                assert e.code==17
            else:
                raise AssertionError('real ACM launch did not return child outcome')
            assert ns.call_count==2 and all(c.args==(expected,) and c.kwargs=={'connected':True} for c in ns.call_args_list)
            launch.assert_called_once()
            assert launch.call_args.args==(namespace,) and 'stdin' in launch.call_args.kwargs
o,s,b=m.owner,m.stage,m.base
assert o.SCRIPT==m.SCRIPT and o.PROFILE==m.PROFILE and o.RUN_ROOT==m.RUN_ROOT
assert o.ACTIVATION==m.RUN_ROOT/'activation.json' and o.TEST_SOURCE==m.TEST
assert o.review_identity is m.review and o.terminal_verdict is m.verdict
assert acm.PROFILE==m.PROFILE and acm.RUN_ROOT==m.RUN_ROOT and acm.CANDIDATE==m.CANDIDATE
assert s.reader is probe and s._configure_runtime.__code__.co_filename==str(m.SCRIPT)
assert o.checked_terminal is s.publish and s.make_intent is b.scan_intent
assert b.prepare is m.cstage.prepare and b.execute is m.cstage.execute and b.restore is m.cstage.restore
assert s.APPROVAL=='S20PLUS-G986N-CONSOLIDATED-BOUND:' and s.CONFIRM=='S20PLUS-G986N-CONSOLIDATED-ARRIVAL:'
scope=o.effect_profile()
assert scope['diagnostic_bytes_per_kernel_entry']==240 and scope['regular_initcalls']==153
assert scope['ram_init_udc_wait_seconds']==90 and scope['candidate_dwell_seconds']==180
assert scope['physical_download_only_after_candidate'] and not scope['rebind']
assert scope['candidate_and_rollback_replay'] is False and scope['candidate_host_commands']==0
raw=o.retained_runtime_source()
assert m.SCRIPT.name.encode() in raw
assert raw.count(b'if name in ("initial-reboot", "candidate-transfer"):\n                    _early_effect_deadline(Path(capture_dir))')==1
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=SCRIPTS, check=True, timeout=30)

    def test_standalone_binds_real_package_bitmap_reader_and_init_witness(self):
        if not self.m.PAIR.is_file():
            self.skipTest("requires the exact consolidated AP pair")
        code = r"""import base64
import s20plus_g986n_consolidated_f1 as m
m.bind()
pair=m.owner.read_pair()
assert pair['candidate']['ap']['sha256']==m.CANDIDATE and pair['rollback']['ap']['sha256']==m.ORIGINAL
probe=m.stage.reader
assert probe.STAGES==m.STAGES and probe.MILESTONES==m.MILESTONES
assert len(probe.frames(pair['nonce'])['basic_enter'])==80
zero=probe.parse(0,b'C1,2097136,0,0,-\n',b'')
assert zero['state']=='no_record' and zero['bitmap']=='00'*40
data=((1<<0)|(1<<1)|(1<<306)|(1<<315)).to_bytes(40,'little')
out=probe.parse(0,b'C1,2097136,4,3,'+base64.urlsafe_b64encode(data).rstrip(b'=')+b'\n',b'')
assert out['state']=='complete' and out['bitmap']==data.hex() and out['anchor_count']==4 and out['record_count']==3
assert probe.describe(out['bitmap'])==dict(entry_count=1,return_count=1,highest_enter=0,highest_return=0,
                                          milestones=['basic_enter','el0_getpid'])
acm=m.observer()
serial,banner=acm.witness()
assert acm.HEADER==m.HEADER and acm.HEADER_SHA==m.HEADER_SHA
assert serial=='y2q-'+pair['nonce'] and pair['nonce'].encode() in banner
for path,digest in ((m.INIT_ELF,m.INIT_ELF_SHA),(m.INITRD,m.INITRD_SHA),(m.BOARD,m.BOARD_SHA)):
    m.base.pinned(path,digest)
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=SCRIPTS, check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
