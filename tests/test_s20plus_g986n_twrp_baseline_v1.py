from pathlib import Path
import contextlib
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock

from tests.test_s20plus_g986n_twrp_boot_identity_d0 import S20PlusTwrpBootIdentityD0Test as Fixture
ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'workspace/public/src/scripts/revalidation'
if str(SCRIPTS) not in sys.path:sys.path.insert(0,str(SCRIPTS))
import s20plus_g986n_twrp_baseline_v1 as baseline
REAL_REQUIRE_REVIEW=baseline.require_review


class TwrpBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Fixture.setUpClass()
        cls.fixture=Fixture()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.stack=contextlib.ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(baseline,'ROOT',self.root))
        self.stack.enter_context(mock.patch.object(baseline,'require_review',return_value={}))
        self.stack.enter_context(mock.patch.object(baseline,'fingerprint',return_value={'fixture':'fixed'}))
        original_receipt=baseline.file_receipt
        self.stack.enter_context(mock.patch.object(baseline,'file_receipt',side_effect=lambda p: {'path':'review','sha256':'f'*64} if p==baseline.REVIEW else original_receipt(p)))
        self.stack.enter_context(mock.patch.object(baseline.identity,'validate_host_closure',return_value={'t2_predecessor':self.fixture.predecessor}))
        self.source={'serial':self.fixture.serial,'serial_sha256':self.fixture.predecessor['serial_sha256'],
                     'usb_topology_sha256':self.fixture.predecessor['topology_sha256'],'boot_id_sha256':'c'*64}
        self.stack.enter_context(mock.patch.object(baseline.routine,'preflight',return_value=self.source))
        self.reboots=0;self.commands=[];self.cut=False
        def command(argv,timeout,maximum):
            self.commands.append(argv)
            if argv[-2:]==['reboot','recovery']:
                self.reboots+=1
                if self.cut:raise KeyboardInterrupt()
                return 0,b'',b''
            if argv[1:]==['devices','-l']:return 0,self.fixture.inventory_output(),b''
            if argv[-1]=='get-devpath':return 0,(self.fixture.devpath+'\n').encode(),b''
            if argv[-1]==baseline.identity.t2.h0.RECOVERY_SHELL_ARGUMENT:return 0,self.fixture.identity_output(),b''
            if argv[-1]==baseline.identity.BOOT_METADATA_SCRIPT:return 0,self.fixture.metadata_output(),b''
            self.fail('unexpected fixed command')
        self.command=command
        self.stack.enter_context(mock.patch.object(baseline.routine,'bounded_command',side_effect=command))

    def test_enter_qualifies_real_fixed_collector_and_releases_guard(self):
        result=baseline.run_new(True)
        self.assertEqual(result['verdict'],'PROVED_S20PLUS_G986N_TWRP_BASELINE_HEALTHY')
        self.assertEqual(self.reboots,1)
        self.assertFalse(baseline.routine.guard_path(self.root).exists())
        self.assertEqual(result['partition_transfers'],0)
        self.assertFalse(result['boot_content_verified'])
        self.assertFalse(result['f1_authorized'])
        contents=''.join(p.read_text() for p in Path(result['run_dir']).glob('*.json'))
        self.assertNotIn(self.fixture.serial,contents)
        self.assertNotIn(self.fixture.current_boot_id,contents)
        self.assertNotIn(self.fixture.devpath,contents)

    def test_already_twrp_observation_does_not_reboot(self):
        result=baseline.run_new(False)
        self.assertEqual(self.reboots,0)
        self.assertEqual(result['entry_attempts'],0)

    def test_reporting_cut_after_entry_resumes_without_reboot(self):
        self.cut=True
        with self.assertRaises(KeyboardInterrupt):baseline.run_new(True)
        self.cut=False;result=baseline.resume()
        self.assertEqual(self.reboots,1)
        self.assertTrue(result['entry_replay_permitted'] is False)
        self.assertFalse(baseline.routine.guard_path(self.root).exists())

    def test_foreign_guard_is_never_removed_or_used(self):
        guard=baseline.routine.guard_path(self.root);guard.parent.mkdir(parents=True)
        guard.write_bytes(b'foreign')
        with self.assertRaises(Exception):baseline.run_new(True)
        self.assertEqual(guard.read_bytes(),b'foreign')
        self.assertEqual(self.commands,[])

    def test_normal_readiness_states_are_waitable_but_second_target_is_not(self):
        p=self.fixture.predecessor
        for state in ['device','offline']:
            row={'serial':self.fixture.serial,'state':state,'metadata':set()}
            self.assertFalse(baseline.recovery_ready((row,),p))
        row={'serial':self.fixture.serial,'state':'recovery','metadata':set()}
        self.assertTrue(baseline.recovery_ready((row,),p))
        foreign={'serial':'SYNTHETIC-SECOND','state':'recovery','metadata':{baseline.identity.t2.b0.EXPECTED_ADB_MODEL}}
        with self.assertRaisesRegex(RuntimeError,'ambiguous'):baseline.recovery_ready((row,foreign),p)

    def test_command_gate_blocks_other_target_and_arbitrary_root(self):
        run=self.root/'fixture';run.mkdir()
        with mock.patch.object(baseline,'require_guard'):
            gate=baseline.CommandGate(run,self.fixture.predecessor,command=lambda *a:self.fail('command dispatched'))
            for argv in [[str(baseline.identity.ADB),'-s','OTHER','get-devpath'],
                         [str(baseline.identity.ADB),'-s',self.fixture.serial,'shell','su','-c','anything'],
                         [str(baseline.identity.ADB),'-s',self.fixture.serial,'reboot','recovery']]:
                with self.assertRaises(RuntimeError):gate(argv,10,4096)

    def test_wrong_t2_identity_stops_without_replaying_entry(self):
        wrong=self.fixture.identity_output().replace(b'uid=0\n',b'uid=2000\n')
        def command(argv,timeout,maximum):
            if argv[-1]==baseline.identity.t2.h0.RECOVERY_SHELL_ARGUMENT:return 0,wrong,b''
            return self.command(argv,timeout,maximum)
        with mock.patch.object(baseline.routine,'bounded_command',side_effect=command):
            with self.assertRaises(Exception):baseline.run_new(True)
        self.assertEqual(self.reboots,1)
        with self.assertRaisesRegex(RuntimeError,'cause-specific'):baseline.resume()
        self.assertEqual(self.reboots,1)
        run=Path(baseline.routine.read_guard(self.root)['run_dir'])
        traces=[baseline.read_json(p) for p in run.glob('command-*.json')]
        self.assertTrue(any(x.get('fixed_property_fields',{}).get('uid')=='2000' for x in traces))

    def test_same_source_boot_cannot_close_entry(self):
        self.source['boot_id_sha256']=hashlib.sha256(self.fixture.current_boot_id.encode()).hexdigest()
        with self.assertRaisesRegex(RuntimeError,'did not change'):baseline.run_new(True)
        self.assertTrue(baseline.routine.guard_path(self.root).exists())

    def test_terminal_publication_cut_closes_without_new_commands(self):
        original=baseline.routine.release_guard
        with mock.patch.object(baseline.routine,'release_guard',side_effect=RuntimeError('host publication cut')):
            with self.assertRaises(RuntimeError):baseline.run_new(True)
        count=len(self.commands);result=baseline.resume()
        self.assertEqual(len(self.commands),count)
        self.assertEqual(result['verdict'],'PROVED_S20PLUS_G986N_TWRP_BASELINE_HEALTHY')

    def test_corrupt_terminal_cannot_release_guard(self):
        with mock.patch.object(baseline.routine,'release_guard',side_effect=RuntimeError('cut')):
            with self.assertRaises(RuntimeError):baseline.run_new(True)
        run=Path(baseline.routine.read_guard(self.root)['run_dir']);p=run/'baseline.json'
        value=baseline.read_json(p);value['recovery_health']['recovery']['t2_identity_without_boot_id']['uid']='2000'
        p.chmod(0o600);p.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');p.chmod(0o400)
        with self.assertRaisesRegex(RuntimeError,'terminal health'):baseline.resume()
        self.assertTrue(baseline.routine.guard_path(self.root).exists())

    def test_failed_reboot_stops_before_readiness_and_retains_guard(self):
        def failed(argv,timeout,maximum):
            if argv[-2:]==['reboot','recovery']:
                self.reboots+=1;return 1,b'',b'reboot failed'
            self.fail('unexpected read after failed reboot')
        with mock.patch.object(baseline.routine,'bounded_command',side_effect=failed):
            with self.assertRaises(Exception):baseline.run_new(True)
        self.assertEqual(self.reboots,1)
        self.assertTrue(baseline.routine.guard_path(self.root).exists())
        with self.assertRaisesRegex(RuntimeError,'cause-specific'):baseline.resume()

    def test_failed_resume_is_durable_and_next_resume_has_zero_commands(self):
        self.cut=True
        with self.assertRaises(KeyboardInterrupt):baseline.run_new(True)
        self.cut=False
        wrong=self.fixture.identity_output().replace(b'uid=0\n',b'uid=2000\n')
        def failed(argv,timeout,maximum):
            if argv[-1]==baseline.identity.t2.h0.RECOVERY_SHELL_ARGUMENT:return 0,wrong,b''
            return self.command(argv,timeout,maximum)
        with mock.patch.object(baseline.routine,'bounded_command',side_effect=failed):
            with self.assertRaises(Exception):baseline.resume()
        count=len(self.commands)
        with self.assertRaisesRegex(RuntimeError,'cause-specific'):baseline.resume()
        self.assertEqual(len(self.commands),count)
        self.assertEqual(self.reboots,1)

    def test_qualification_drift_is_refused_without_commands(self):
        review=self.root/'qualification.json';log=self.root/'tests.log'
        log.write_text('Ran 13 tests in 0.01s\n\nOK\n');log.chmod(0o400)
        with mock.patch.object(baseline,'REVIEW',review), mock.patch.object(baseline,'TEST_LOG',log):
            value={'schema':baseline.SCHEMA+'-qualification',
                   'review':{'verdict':'PASS_GO','high':0,'medium':0,'low':0},
                   'fingerprint':{'fixture':'changed'},'tests':baseline.identity.file_receipt(log,label='test')}
            baseline.publish(review,value)
            with self.assertRaisesRegex(RuntimeError,'review differs'):REAL_REQUIRE_REVIEW()
        self.assertEqual(self.commands,[])


if __name__=='__main__':unittest.main()
