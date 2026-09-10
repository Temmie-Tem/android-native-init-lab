"""Actual retained endpoint inventory and shared guard lifetime composition."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import test_s22plus_fyg8_p324_cdc_acm_observer as fixture
import device_action_f1_live_v2 as live
import s22plus_native_baseline_guard_v1 as guard


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.ttys=self.root/'sys/class/tty'; self.ttys.mkdir(parents=True)
        self.usb=self.root/'usb'; self.usb.mkdir()
        (self.root/'port0/port0-partner').mkdir(parents=True)
        self.spec=live.typed_evidence._shell_observer_spec('p385')
        self.base_spec=live._p327_inherited_spec(self.spec)
        fixture._endpoint(self.root,self.usb,self.ttys,'3-1.3','ttyACM0',self.base_spec['usb_serial'])
        _,self.endpoint=guard.cdc._resolve_endpoint(self.ttys/'ttyACM0')
        self.retained=dict(context_sha256='a'*64,terminal={'path':str(self.root/'prior.json'),'size':1,'sha256':'b'*64},
                           endpoint_identity_sha256=self.endpoint.identity_sha256)
        self.run=self.root/'run'; self.run.mkdir()
        self.prepared=SimpleNamespace(run_dir=self.run, native_baseline_context={'phase':'native-start'},
            bundle=SimpleNamespace(manifest={'observation':{'candidate_observer':self.spec}}))
        self.lane={'bound':True}; self.lane_pin={'path':str(self.root/'lane.json'),'size':1,'sha256':'c'*64}

    def fake_guard(self, flags=True):
        value=mock.Mock()
        value.matches_node.return_value=flags
        value.arm_receipt=dict(schema=guard.cdc.GUARD_SCHEMA,status='armed',spec_sha256='1'*64,
            topology_sha256='2'*64,rule_sha256='3'*64,instance_sha256='5'*64,output_sha256='6'*64,
            raw_capture_receipt={},child_alive=True)
        value.release.return_value=dict(schema=guard.cdc.GUARD_SCHEMA,status='released',instance_sha256='5'*64,
                                        released=True,returncode=0)
        return value

    def patches(self, fake):
        from contextlib import ExitStack
        stack=ExitStack()
        stack.enter_context(mock.patch.object(guard,'retained',return_value=self.retained))
        stack.enter_context(mock.patch.object(guard.lane_observer.lane,'revalidate_binding',return_value=self.lane))
        stack.enter_context(mock.patch.object(guard.cdc.ModemManagerGuard,'arm',return_value=fake))
        stack.enter_context(mock.patch.object(live,'_p324_typec_lane_value',return_value=(self.lane,self.lane_pin)))
        return stack

    def session(self):
        return guard.observer_session(live,self.prepared,self.base_spec,guard.lane_observer.lane.SOURCE_TOPOLOGY,
            self.run,{'binding':'fixed'},self.lane,self.lane_pin,usb_root=self.usb,typec_root=self.root,
            class_tty=self.ttys,dev_root=self.root/'dev')

    def test_present_baseline_exact_selection_current_flags_and_reader(self):
        fake=self.fake_guard()
        with self.patches(fake):
            with self.session() as session:
                self.assertIsInstance(session,guard.guard_adapter.P325ObserverSession)
                classification, selected=session.delegate._select()
                self.assertEqual(classification,'accepted')
                self.assertEqual(selected.identity_sha256,self.endpoint.identity_sha256)
                fake.matches_node.assert_called_once_with(self.endpoint.tty_class)
                self.assertFalse(json.loads((self.run/'candidate-observer-baseline.json').read_text())['exact_candidate_absent'])
            value=dict(topology_sha256=hashlib.sha256(b'3-1.3').hexdigest(),endpoint_identity_sha256=self.endpoint.identity_sha256,
                       lane={'partner_before':guard.lane_observer._partner(self.root)})
            self.assertTrue(guard.validate_baseline(live,self.prepared,value))
            path=self.run/'candidate-observer-baseline.json'; original=path.read_bytes()
            changed=json.loads(original); changed['exact_candidate_absent']=True
            path.chmod(0o600); path.write_text(json.dumps(changed)); path.chmod(0o400)
            with self.assertRaises(live.F1LiveError): guard.validate_baseline(live,self.prepared,value)
        fake.release.assert_called_once()

    def test_missing_current_flags_releases_guard_without_opening_a_session(self):
        fake=self.fake_guard(False)
        with self.patches(fake), self.assertRaisesRegex(guard.cdc.ObserverError,'ModemManager flags'):
            with self.session(): self.fail('missing flags entered retained session')
        fake.release.assert_called_once()
        self.assertTrue((self.run/'candidate-observer-guard-release.json').exists())

    def test_foreign_candidate_and_changed_retained_identity_block_before_arm(self):
        for case in ('foreign','changed'):
            with self.subTest(case=case):
                fake=self.fake_guard()
                if case=='foreign': fixture._endpoint(self.root,self.usb,self.ttys,'3-2','ttyACM1','foreign')
                else:
                    self.retained['endpoint_identity_sha256']='f'*64
                    import shutil
                    shutil.rmtree(self.ttys/'ttyACM1')
                with self.patches(fake), self.assertRaises(guard.cdc.ObserverError):
                    with self.session(): self.fail('invalid inventory entered session')
                self.assertFalse(fake.matches_node.called)

    def test_generic_default_still_requires_candidate_absence(self):
        with mock.patch.object(guard.cdc.ModemManagerGuard,'arm') as arm:
            with self.assertRaisesRegex(guard.cdc.ObserverError,'already present'):
                with guard.cdc.observer_session(self.base_spec,'usb:3-1.3',self.run,{},class_tty=self.ttys):
                    self.fail('ordinary observer accepted present native')
            arm.assert_not_called()


if __name__=='__main__': unittest.main()
