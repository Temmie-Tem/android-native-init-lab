"""Real Samsung arrival producer + window consumer; only Odin platform is faked."""
import copy
import json
import hashlib
import types
import unittest
from pathlib import Path
from unittest import mock
from tests.test_s22plus_fyg8_p363_return_host import Fixture, live, owner
import tempfile
import contextlib


class NativeArrivalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fixture = Fixture(Path(self.tmp.name) / 'run')
        self.p = self.fixture.prepared
        self.p.private_target['topology'] = 'usb:1-1'
        self.state = {}
        self.backend = object.__new__(live.SamsungOdinBackend)
        self.backend.odin = Path(self.tmp.name) / 'fixture-odin'
        self.backend.usb_root = Path(self.tmp.name) / 'sys-usb'
        self.backend.usb_root.mkdir()
        self.node = Path(self.tmp.name) / 'controller/usb1/1-1'
        self.node.mkdir(parents=True)
        (self.backend.usb_root / '1-1').symlink_to(self.node, target_is_directory=True)
        profile = json.loads((Path(__file__).resolve().parents[1]/'workspace/public/src/device-action/profiles/s22plus_fyg8.json').read_text())['target']['download']
        self.p.bundle.profile['target']['download'] = profile
        for name, value in dict(busnum='1',devnum='2',idVendor=profile['usb_vendor_id'],
            idProduct=profile['usb_product_id'],product=profile['product'],
            manufacturer=profile['manufacturer']).items():
            (self.node/name).write_text(value+'\n')
        self.endpoint_dir = self.p.run_dir / 'odin-endpoints'
        self.endpoint_dir.mkdir()
        self.sequence = 0

    def patches(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(live,'_state',side_effect=lambda _:copy.deepcopy(self.state)))
        stack.enter_context(mock.patch.object(live,'_save_state',side_effect=lambda _,v:self.state.update(copy.deepcopy(v))))
        self.lease = stack.enter_context(live.odin_core.transaction_session(self.endpoint_dir))
        real_wait = live.odin_core.wait_for_single_live_endpoint
        real_revalidate = live.odin_core.revalidate_endpoint_ticket
        def platform():
            device = '/dev/bus/usb/001/'+(self.node/'devnum').read_text().strip().zfill(3)
            return dict(runner=lambda *_args,**_kw:types.SimpleNamespace(returncode=0,stdout=device,stderr=''),
                device_identity=lambda _: 'a'*64,device_inventory=lambda:{device:'a'*64},
                endpoint_observer_factory=None,lease=self.lease)
        def wait(*args,**kwargs):
            kwargs.update(platform())
            return real_wait(*args,**kwargs)
        def revalidate(*args,**kwargs):
            kwargs.update(platform())
            return real_revalidate(*args,**kwargs)
        stack.enter_context(mock.patch.object(live.odin_core,'wait_for_single_live_endpoint',side_effect=wait))
        stack.enter_context(mock.patch.object(live.odin_core,'revalidate_endpoint_ticket',side_effect=revalidate))
        return stack

    def test_real_backend_to_window_without_legacy_files(self):
        with self.patches():
            endpoint=live._p363_wait_for_rollback(self.p,self.backend,self.endpoint_dir,None)
            self.assertTrue(live._p363_return_success(self.p,self.state))
            value=live._read_native_download_arrival(self.p,endpoint.arrival_receipt)
        self.assertEqual(value['topology']['topology'],'1-1')
        self.assertFalse(list(self.p.run_dir.glob('p318-topology-*')))
        self.assertEqual(self.state['p363_return_window']['record']['rollback_topology_record'],endpoint.arrival_receipt)

    def test_recovery_generation_has_own_receipt_without_start_history(self):
        with self.patches():
            first=self.backend.wait_download(self.p,self.endpoint_dir,None,1)
            before={p:p.read_bytes() for pattern in ('native-*.json','receipts/*.json') for p in self.endpoint_dir.glob(pattern)}
            live.odin_core.wait_for_no_live_endpoint(self.backend.odin,self.endpoint_dir,
                timeout_sec=1,sequence_start=len(live.odin_core.list_snapshot_receipts(self.endpoint_dir)),
                lease=self.lease,runner=lambda *_args,**_kw:types.SimpleNamespace(returncode=0,stdout='',stderr=''),
                device_identity=lambda _:None,device_inventory=lambda:{})
            (self.node/'devnum').write_text('3\n')
            second=self.backend.wait_download(self.p,self.endpoint_dir,None,1)
            live._read_native_download_arrival(self.p,first.arrival_receipt)
            live._read_native_download_arrival(self.p,second.arrival_receipt)
        self.assertNotEqual(first.arrival_receipt,second.arrival_receipt)
        self.assertTrue(all(p.read_bytes()==v for p,v in before.items()))

    def test_incomplete_inventory_retained_and_rejected(self):
        (self.backend.usb_root/'2-1').mkdir() # unreadable identity cannot become absence
        with self.patches(),self.assertRaisesRegex(live.F1LiveError,'incomplete'):
            self.backend.wait_download(self.p,self.endpoint_dir,None,1)
        self.assertEqual(len(list(self.endpoint_dir.glob('native-*.raw.json'))),1)
        self.assertFalse(list(self.endpoint_dir.glob('native-*[0-9].json')))

    def test_changed_ticket_or_topology_rejects_proof(self):
        with self.patches():
            endpoint=self.backend.wait_download(self.p,self.endpoint_dir,None,1)
        value=live._read_native_download_arrival(self.p,endpoint.arrival_receipt)
        path=Path(value['revalidation']['revalidation_receipt'])
        path.chmod(0o600);path.write_text('{}')
        with self.assertRaises((live.F1LiveError,live.odin_core.OdinTransitionError)):
            live._read_native_download_arrival(self.p,endpoint.arrival_receipt)

    def test_revalidation_projection_cannot_claim_another_identity(self):
        with self.patches():
            endpoint=self.backend.wait_download(self.p,self.endpoint_dir,None,1)
        path=Path(endpoint.arrival_receipt['path'])
        value=json.loads(path.read_text())
        value['revalidation']['device_identity']='b'*64
        value['endpoint']['identity_sha256']=hashlib.sha256((hashlib.sha256(endpoint.device.encode()).hexdigest()+'b'*64).encode()).hexdigest()
        path.chmod(0o600);path.write_text(json.dumps(value))
        with self.assertRaisesRegex(live.F1LiveError,'ticket differs'):
            live._read_native_download_arrival(self.p,live._receipt(path,'test receipt'))

    def test_ambiguous_topology_is_not_an_exact_arrival(self):
        other=self.node.parent/'1-2';other.mkdir()
        for path in self.node.iterdir(): (other/path.name).write_bytes(path.read_bytes())
        (other/'devnum').write_text('3\n')
        (self.backend.usb_root/'1-2').symlink_to(other,target_is_directory=True)
        with self.patches(),self.assertRaisesRegex(live.F1LiveError,'ambiguous'):
            self.backend.wait_download(self.p,self.endpoint_dir,None,1)

    def test_revalidation_error_preserves_raw_without_arrival_publication(self):
        with self.patches(),mock.patch.object(live.odin_core,'revalidate_endpoint_ticket',side_effect=OSError('generation failed')):
            with self.assertRaisesRegex(OSError,'generation failed'):
                self.backend.wait_download(self.p,self.endpoint_dir,None,1)
        self.assertEqual(len(list(self.endpoint_dir.glob('native-*.raw.json'))),1)
        self.assertFalse(list(self.endpoint_dir.glob('native-*[0-9].json')))


if __name__ == '__main__': unittest.main()
