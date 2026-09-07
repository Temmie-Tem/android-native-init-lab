"""Fresh P367: real native console, arrival producer and scoped final consumer."""
from pathlib import Path
import contextlib
import hashlib
import json
import sys
import types
import unittest
from unittest import mock
from tests.test_s22plus_fyg8_p324_typec_lane_binding import _fixture, _write

parent=types.ModuleType('_p367_lifecycle_support')
parent.__file__=str(Path('tests/test_s22plus_fyg8_p366_lifecycle.py').resolve())
sys.modules[parent.__name__]=parent
raw=Path(parent.__file__).read_text().replace('p366','p367').replace('P366','P367')
exec(compile(raw,parent.__file__+'#p367','exec'),parent.__dict__)
live=parent.live
parent.return_host=live.p367_return_host


class JoinedBackend(parent.BaseBackend):
    _wait_final_health=live.SamsungOdinBackend._wait_final_health
    _capture_target_final=live.SamsungOdinBackend._capture_target_final
    def __init__(self,p,peer,case,*,foreign=False,ambiguous=False):
        super().__init__(p,peer,case)
        self.p=p;self.foreign=foreign;self.ambiguous=ambiguous;self.generation=1
        self.usb_root,self.typec_root=_fixture(p.root/'joined-platform')
        self.source=(self.usb_root/'2-1').resolve()/'2-1.3';self.source.mkdir()
        self.lane=live.p324_typec_lane.capture_binding(p.private_target['topology'],usb_root=self.usb_root,typec_root=self.typec_root)
        path=p.run_dir/live.P324_TYPEC_LANE_NAME;live._write_exclusive(path,self.lane)
        p.prepared['p324_typec_lane_binding']=live._receipt(path,'joined lane')
        p.prepared['execution_closure']={'sources':{'final_target_health':live._receipt(Path(live.target_final_health.__file__),'final source')}}
        self.odin=p.root/'fixture-odin'
        self.adb=p.root/'fixture-adb'
        self.receipts_dir=p.run_dir/'odin-endpoints'
        self.cut_before_eof=False
        self.adb.write_text(self.adb_source());self.adb.chmod(0o700)

    def adb_source(self):
        health=self.p.bundle.profile['final_health']
        props=dict(model='SM-S906N',device='g0q',bootloader='S906NKSS7FYG8',incremental='S906NKSS7FYG8',boot_completed='1',bootanim='stopped',verified_boot_state='orange',boot_id='12345678-1234-1234-1234-123456789abc',kernel_release='fixture-kernel')
        root=dict(root='uid=0(root) gid=0(root)',boot=health['boot_sha256'],**health['supporting_partition_sha256'])
        return f'''#!{sys.executable}
import sys
args=sys.argv[1:];joined=' '.join(args)
if args==['devices','-l']:print('List of devices attached\\n{self.p.private_target['serial']} device model:SM_S906N device:g0q transport_id:2')
elif args[-1:]==['get-devpath']:print('usb:2-1.3')
elif 'getprop ro.product.model' in joined:print({''.join(f'{k}={v}'+chr(10) for k,v in props.items())!r},end='')
elif 'sha256sum /dev/block/by-name/boot' in joined:print({''.join(f'{k}={v}'+chr(10) for k,v in root.items())!r},end='')
elif 'exec-out' in args:sys.stdout.buffer.write(bytes(2097136))
else:raise SystemExit(2)
'''

    def source_mode(self,mode):
        link=self.usb_root/'2-1.3'
        if link.is_symlink():link.unlink()
        if mode=='absent':return
        link.symlink_to(self.source)
        d=self.p.bundle.profile['target']['download']
        values=dict(idVendor='04e8',idProduct='6860' if mode=='android' else d['usb_product_id'],busnum='2',devnum=str(7+self.generation),product=d['product'],manufacturer=d['manufacturer'])
        for k,v in values.items():_write(self.source/k,v)
        serial=self.source/'serial'
        if serial.exists():serial.unlink()
        if mode=='android':_write(serial,self.p.private_target['serial'])

    def add_foreign(self):
        node=(self.usb_root/'usb2').resolve()/'2-2';node.mkdir()
        (self.usb_root/'2-2').symlink_to(node)
        d=self.p.bundle.profile['target']['download']
        for k,v in dict(idVendor=d['usb_vendor_id'],idProduct=d['usb_product_id'],product=d['product'],manufacturer=d['manufacturer'],busnum='2',devnum='99').items():_write(node/k,v)

    def inventory(self):
        result={}
        for name in ('2-1.3','2-2'):
            node=self.usb_root/name
            if node.exists() and (node/'idProduct').read_text().strip()=='685d':
                result['/dev/bus/usb/002/'+(node/'devnum').read_text().strip().zfill(3)]='a'*64
        return result

    def platform(self):
        return dict(runner=lambda *_a,**_kw:types.SimpleNamespace(returncode=0,stdout=' '.join(self.inventory()),stderr=''),
                    device_identity=lambda p:self.inventory().get(p),device_inventory=self.inventory,endpoint_observer_factory=None)

    @contextlib.contextmanager
    def endpoint_session(self,run_dir):
        self.receipts_dir=run_dir
        with live.odin_core.transaction_session(run_dir) as lease:
            self.lease=lease;yield lease

    def wait_download(self,p,run,lease,timeout):
        self.calls.append('wait-download');self.source_mode('download')
        if self.ambiguous:self.add_foreign();self.ambiguous=False
        actual_wait=live.odin_core.wait_for_single_live_endpoint
        actual_revalidate=live.odin_core.revalidate_endpoint_ticket
        def wait(*a,**kw):kw.update(self.platform());return actual_wait(*a,**kw)
        def revalidate(*a,**kw):kw.update(self.platform());return actual_revalidate(*a,**kw)
        with mock.patch.object(live.odin_core,'wait_for_single_live_endpoint',side_effect=wait),mock.patch.object(live.odin_core,'revalidate_endpoint_ticket',side_effect=revalidate):
            return live.SamsungOdinBackend.wait_download(self,p,run,lease,timeout)

    def transfer(self,p,endpoint,kind,destination,attempt,prefix):
        result=super().transfer(p,endpoint,kind,destination,attempt,prefix)
        if kind=='candidate':
            self.source_mode('absent')
            live.odin_core.wait_for_no_live_endpoint(self.odin,self.receipts_dir,
                timeout_sec=1,sequence_start=len(live.odin_core.list_snapshot_receipts(self.receipts_dir)),
                lease=self.lease,**self.platform())
            self.generation+=1
        else:
            self.source_mode('android')
            if self.foreign:self.add_foreign()
        return result

    def verify_final(self,p,run,lease,destination):
        self.calls.append('verify-final')
        return live.SamsungOdinBackend.verify_final(self,p,run,lease,destination)


class P367JoinedLifecycle(parent.fixture.PersistenceTests):
    # Only the joined cases below run here; the predecessor is a fixture factory.
    test_complete_success_and_late_failure_roundtrip=None
    test_closed_publication_cut_never_replays_backend=None
    test_exact_record_limits_and_unrelated_variants=None

    def patches(self):
        stack=super().patches()
        stack.enter_context(mock.patch.object(parent.departure,'_snapshot',side_effect=parent.departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/077')))
        return stack

    def test_actual_joined_success_and_diagnostic_failure_with_foreign_download(self):
        for case in ('normal','writer'):
            with self.subTest(case=case):
                p=self.prepared();backend=JoinedBackend(p,self.peer,case,foreign=True)
                with self.patches():
                    self.assertTrue(live._target_final_enabled(p))
                    result=live.execute_prepared(p,p.approval_token,backend)
                    live.validate_live_result(json.loads((p.run_dir/'live-result.json').read_text()),p)
                self.assertEqual(result['current_state'],'CLOSED')
                self.assertFalse(result['recovery_required'])
                self.assertEqual(result['verdict'],'PASS_F1_V2_P367_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK' if case=='normal' else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                final=result['live_state']['final_evidence']
                self.assertFalse(final['health']['odin_endpoint_absent'])
                self.assertTrue(final['health']['target_odin_endpoint_absent'])
                self.assertFalse(list(p.run_dir.glob('p318-topology-rollback*')))
                self.assertTrue(list((p.run_dir/'odin-endpoints').glob('native-download-arrival-*.json')))
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])

    def test_global_ambiguity_still_blocks_before_candidate(self):
        p=self.prepared();backend=JoinedBackend(p,self.peer,'normal',ambiguous=True)
        with self.patches(),self.assertRaisesRegex(live.F1LiveError,'BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY'):
            live.execute_prepared(p,p.approval_token,backend)
        self.assertFalse([c for c in backend.calls if c.startswith('transfer-')])

    def test_client_restart_before_eof_resumes_without_transfer_replay(self):
        p=self.prepared();backend=JoinedBackend(p,self.peer,'normal',foreign=True)
        with self.patches():
            with mock.patch.object(live.d0.AdbReadOnlyClient,'capture',side_effect=RuntimeError('cut before EOF')):
                with self.assertRaisesRegex(RuntimeError,'cut before EOF'):live.execute_prepared(p,p.approval_token,backend)
            result=live.recover_prepared(p,backend)
        self.assertEqual(result['current_state'],'CLOSED')
        self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])

    def test_after_eof_cut_preserves_fixed_outputs_and_fails_closed(self):
        p=self.prepared();backend=JoinedBackend(p,self.peer,'normal',foreign=True)
        original=live.d0.AdbReadOnlyClient.one_serial;calls=[]
        def cut(client):
            calls.append(1)
            if len(calls)==2:raise RuntimeError('cut after EOF')
            return original(client)
        with self.patches():
            with mock.patch.object(live.d0.AdbReadOnlyClient,'one_serial',new=cut):
                with self.assertRaisesRegex(RuntimeError,'cut after EOF'):live.execute_prepared(p,p.approval_token,backend)
            retained={path:path.read_bytes() for path in p.run_dir.glob('*observer*') if path.is_file()}
            with self.assertRaises(FileExistsError):live.recover_prepared(p,backend)
        self.assertTrue(all(path.read_bytes()==raw for path,raw in retained.items()))
        self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
        self.assertEqual(live.core.Journal(p.run_dir/'transaction',p.binding_sha256).state(),'ROLLBACK_FLASHED')

    def test_native_payload_is_p366_identity_only(self):
        import s22plus_fyg8_p366_research_shell_runtime as previous
        raw=parent.support.runtime.P367_HELPER_TEMPLATE.replace(b'p367',b'p366').replace(b'P367',b'P366')
        escape=lambda x:''.join('\\x%02x'%b for b in x).encode()
        raw=raw.replace(escape(b'c367f1e0a90b5e6d7c8a9b0c1d2e3f0b'),escape(b'c366f1e0a90b5e6d7c8a9b0c1d2e3f0b'))
        self.assertEqual(raw,previous.P366_HELPER_TEMPLATE)

P367Arm64Flags=parent.P367Arm64Flags
if __name__=='__main__':unittest.main()
