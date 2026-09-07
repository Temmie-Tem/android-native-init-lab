"""Completed-rollback final verifier with real ADB capture and sysfs producers."""
import contextlib
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from tests import test_device_action_f1_live_v2 as generic
from tests.test_s22plus_fyg8_p324_typec_lane_binding import _fixture, _write


class FinalTargetHealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.module=generic.load_module()

    def setUp(self):
        tmp,self.p=generic.DeviceActionF1LiveV2Test.prepared(self)
        self.addCleanup(tmp.cleanup)
        self.p.private_target['topology']='usb:2-1.3'
        self.p.prepared['execution_closure']={'sources':{'final_target_health':self.module._receipt(Path(self.module.target_final_health.__file__),'fixture source')}}
        self.usb,self.typec=_fixture(self.p.root/'platform')
        self.lane=self.module.p324_typec_lane.capture_binding('usb:2-1.3',usb_root=self.usb,typec_root=self.typec)
        path=self.p.run_dir/self.module.P324_TYPEC_LANE_NAME
        self.module._write_exclusive(path,self.lane)
        self.p.prepared['p324_typec_lane_binding']=self.module._receipt(path,'fixture lane')
        self.android=(self.usb/'2-1').resolve()/'2-1.3';self.android.mkdir()
        (self.usb/'2-1.3').symlink_to(self.android)
        for k,v in dict(idVendor='04e8',idProduct='6860',serial=self.p.private_target['serial'],busnum='2',devnum='7').items():_write(self.android/k,v)
        self.adb=self.p.root/'fixture-final-adb'
        props=dict(model='SM-S906N',device='g0q',bootloader='S906NKSS7FYG8',incremental='S906NKSS7FYG8',boot_completed='1',bootanim='stopped',verified_boot_state='orange',boot_id='12345678-1234-1234-1234-123456789abc',kernel_release='fixture-kernel')
        expected=self.p.bundle.profile['final_health']
        root=dict(root='uid=0(root) gid=0(root)',boot=expected['boot_sha256'],**expected['supporting_partition_sha256'])
        payload='\n'+self.p.bundle.manifest['observation']['acceptance']['marker']+'\n'
        self.adb.write_text(f'''#!{sys.executable}
import sys
args=sys.argv[1:];joined=' '.join(args)
if args == ['devices','-l']:print('List of devices attached\\n{self.p.private_target['serial']} device model:SM_S906N device:g0q transport_id:2')
elif args[-1:] == ['get-devpath']:print('usb:2-1.3')
elif 'getprop ro.product.model' in joined:print({''.join(f'{k}={v}' + chr(10) for k,v in props.items())!r},end='')
elif 'sha256sum /dev/block/by-name/boot' in joined:print({''.join(f'{k}={v}' + chr(10) for k,v in root.items())!r},end='')
elif 'exec-out' in args:print({payload!r},end='')
else:raise SystemExit(2)
''');self.adb.chmod(0o700)
        self.backend=object.__new__(self.module.SamsungOdinBackend)
        self.backend.adb=self.adb;self.backend.usb_root=self.usb;self.backend.typec_root=self.typec
        self.backend.odin=self.p.root/'forbidden-odin'

    def completed(self):
        fake=generic.FakeBackend(self.module,final_failures=1)
        with self.assertRaisesRegex(RuntimeError,'final health'):
            self.module.execute_prepared(self.p,self.p.approval_token,fake)
        self.assertEqual(self.module.core.Journal(self.p.run_dir/'transaction',self.p.binding_sha256).state(),'ROLLBACK_FLASHED')

    def scoped(self):
        stack=contextlib.ExitStack()
        # Generic marker fixture selects the new native-return final branch.
        stack.enter_context(mock.patch.object(self.module,'_native_return_bundle',return_value=True))
        original=self.module._p324_typec_lane_value
        def lane(*args,**kwargs):
            with mock.patch.object(self.module,'_p324_bundle',return_value=True):return original(*args,**kwargs)
        stack.enter_context(mock.patch.object(self.module,'_p324_typec_lane_value',side_effect=lane))
        stack.enter_context(mock.patch.object(self.module.odin_core,'wait_for_no_live_endpoint',side_effect=AssertionError('global Odin final gate called')))
        stack.enter_context(mock.patch.object(self.module.d0,'usb_snapshot',side_effect=AssertionError('global D0 final gate called')))
        return stack

    def download(self,name='2-2'):
        bus='usb'+name.split('-')[0]
        node=(self.usb/bus).resolve()/name;node.mkdir()
        (self.usb/name).symlink_to(node)
        d=self.p.bundle.profile['target']['download']
        for k,v in dict(idVendor=d['usb_vendor_id'],idProduct=d['usb_product_id'],product=d['product'],manufacturer=d['manufacturer'],busnum=name.split('-')[0],devnum='9').items():_write(node/k,v)
        return node

    def test_foreign_download_allows_exact_android_and_is_not_global_absence(self):
        self.completed();self.download()
        with self.scoped():
            result=self.backend.verify_final(self.p,self.p.run_dir/'old-odin-history',None,self.p.run_dir)
            self.module._validate_final_observer(self.p,{'final_evidence':result,'marker_accepted':result['observer']['accepted']})
            self.assertTrue(result['health']['target_odin_endpoint_absent'])
            self.assertFalse(result['health']['odin_endpoint_absent'])
            self.assertEqual(len(result['target_download_absence']['foreign_download_after']),1)
            forged=copy.deepcopy(result);forged['health']['odin_endpoint_absent']=True
            with self.assertRaises(self.module.F1LiveError):self.module._validate_final_observer(self.p,{'final_evidence':forged,'marker_accepted':forged['observer']['accepted']})
            for mode in ('duplicate','swap','downgrade'):
                forged=copy.deepcopy(result)
                scoped=forged['target_download_absence']
                if mode=='duplicate':scoped['after']=copy.deepcopy(scoped['before'])
                elif mode=='swap':scoped['before'],scoped['after']=scoped['after'],scoped['before']
                else:
                    del forged['target_download_absence']
                    del forged['health']['target_odin_endpoint_absent']
                    forged['health']['odin_endpoint_absent']=True
                with self.subTest(mode=mode),self.assertRaises((self.module.F1LiveError,self.module.target_final_health.FinalHealthError)):
                    self.module._validate_final_observer(self.p,{'final_evidence':forged,'marker_accepted':forged['observer']['accepted']})

    def test_no_foreign_download_records_both_absences(self):
        self.completed()
        with self.scoped():
            result=self.backend.verify_final(self.p,self.p.run_dir/'old-odin-history',None,self.p.run_dir)
            self.module._validate_final_observer(self.p,{'final_evidence':result,'marker_accepted':result['observer']['accepted']})
        self.assertTrue(result['health']['odin_endpoint_absent'])
        self.assertEqual(result['target_download_absence']['foreign_download_before'],[])

    def test_not_available_before_durable_rollback(self):
        with self.scoped(),mock.patch.object(self.module.d0,'adb_client_for_bundle',side_effect=AssertionError('ADB before completed rollback')):
            with self.assertRaises(self.module.F1LiveError):self.backend.verify_final(self.p,self.p.run_dir,None,self.p.run_dir)

    def test_target_companion_download_is_blocking(self):
        self.completed();self.download('3-1.3')
        with self.scoped(),self.assertRaisesRegex(self.module.target_final_health.FinalHealthError,'bound target lane'):
            self.backend.verify_final(self.p,self.p.run_dir,None,self.p.run_dir)

    def test_incomplete_census_remains_blocking_with_raw_evidence(self):
        self.completed();(self.usb/'2-9').mkdir()
        with self.scoped(),self.assertRaisesRegex(self.module.target_final_health.FinalHealthError,'incomplete'):
            self.backend.verify_final(self.p,self.p.run_dir,None,self.p.run_dir)
        self.assertEqual(len(list((self.p.run_dir/'final-target-health').glob('*.capture.json'))),1)

    def test_wrong_android_sysfs_serial_cannot_be_ignored(self):
        self.completed();_write(self.android/'serial','other-device')
        with self.scoped(),self.assertRaises(self.module.target_final_health.FinalHealthError):
            self.backend.verify_final(self.p,self.p.run_dir,None,self.p.run_dir)
        capture=next((self.p.run_dir/'final-target-health').glob('*.capture.json'))
        handle=self.module.raw_capture.load_handle(capture)
        raw=json.loads(self.module.raw_capture.read_stdout(handle,maximum=256*1024))
        self.assertEqual([item['values']['serial'] for item in raw['android']['reads']],['other-device','other-device'])

    def test_real_native_bundle_requires_prepared_source_capability(self):
        from tests.test_s22plus_fyg8_p363_return_host import Fixture
        native=Fixture(self.p.root/'native-fixture').prepared
        self.assertTrue(self.module._native_return_bundle(native.bundle))
        self.assertFalse(self.module._target_final_enabled(native))
        native.prepared['execution_closure']={'sources':{'final_target_health':
            self.module._receipt(Path(self.module.target_final_health.__file__),'fixture source')}}
        self.assertTrue(self.module._target_final_enabled(native))
        self.assertFalse(self.module._target_final_enabled(self.p))

    def test_failed_partition_health_is_not_excused_by_foreign_download(self):
        self.completed();self.download()
        self.adb.write_text(self.adb.read_text().replace(self.p.bundle.profile['final_health']['boot_sha256'],'0'*64))
        with self.scoped(),mock.patch.object(self.module,'ANDROID_WAIT_SEC',0.01),mock.patch.object(self.module.time,'sleep',return_value=None):
            with self.assertRaisesRegex(self.module.F1LiveError,'health wait expired'):
                self.backend.verify_final(self.p,self.p.run_dir,None,self.p.run_dir)

if __name__=='__main__':unittest.main()
