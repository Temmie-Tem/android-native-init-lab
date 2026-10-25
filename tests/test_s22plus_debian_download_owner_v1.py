"""Actual owner/arrival graph with simulated USB/Odin delivery only."""
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
import types
import unittest
from unittest import mock

import test_s22plus_debian_reboot_owner_v1 as prior
import s22plus_debian_reboot_access_v1 as access
import s22plus_native_adapter_v3 as native
from s22plus_native_records_v3 import clock,publish,read


@dataclass
class Ticket:
    device:str='/fixture/usb'


class FixedAccess(prior.FixtureAccess):
    def shutdown(self,step,guard,before):
        if self.device.namespace=='p460':return super().shutdown(step,guard,before)
        guard();self.device.assert_mode('Debian');now=clock()
        detail=dict(command='download',phase=2,dispatch_ns=now,deadline_ns=now+90_000_000_000)
        publish(self.device.folder(step.name,create=True)/'intent.json',detail);before(detail)
        self.device.actions.append('download-once');self.device.mode='Download'
        if self.device.fail_after=='download':raise OSError('download delivered; ACK lost')
        return self.device.proof(step)
    def rederive_control(self,command):
        assert command=='download';return self.device.proofs['debian-shutdown']
    def rederive_shutdown(self):return self.rederive_control('download')


class Device(prior.Device):
    namespace='p461'
    _transfer=native.Adapter._transfer
    def prepare(self,*args,**kw):
        value=super().prepare(*args,**kw)
        value['N']['profile']='debian-autoboot-v1'
        value['A']=dict(ap=dict(path='/fixture/A',size=1,sha256='a'*64),member={})
        return value
    def folder(self,name,*,create=False):
        path=self.directory/('io-'+name)
        if create:path.mkdir(mode=0o700,exist_ok=True)
        return path
    def configuration(self,request):return dict(odin=dict(path='/fixture/odin',size=1,sha256='b'*64),lane={})
    def original_android(self,request):return nullcontext(object())
    def native_host(self,request):return types.SimpleNamespace(holders=lambda:None)
    def transfer(self,step,request,*,guard,before_launch):
        if step.name!='install-android' or self.namespace!='p461':
            return super().transfer(step,request,guard=guard,before_launch=before_launch)
        ready=self.directory/'debian-return-ready.json'
        self.arrival_basis=read(ready)
        if self.fail_before=='renewed':
            changed=dict(self.arrival_basis,deadline_ns=self.arrival_basis['deadline_ns']+1)
            ready.unlink();publish(ready,changed)
        if self.fail_before=='expired':
            with mock.patch.object(native,'clock',return_value=self.arrival_basis['deadline_ns']):
                return native.Adapter.transfer(self,step,request,guard=guard,before_launch=before_launch)
        return native.Adapter.transfer(self,step,request,guard=guard,before_launch=before_launch)


class GraphTests(unittest.TestCase):
    setUp=prior.OwnerTests.setUp
    def operation(self,*,namespace='p461'):
        device=Device();device.namespace=namespace
        directory=prior.prior.previous.owner.prepare_operation(self.root,self.grant,
            operation='debian-autoboot',adapter=device)
        device.directory=directory
        def patch(obj,name,**kw):
            value=mock.patch.object(obj,name,**kw);result=value.start();self.addCleanup(value.stop);return result
        patch(access,'Access',new=FixedAccess)
        patch(native.inspection_session,'android_basis',return_value=None)
        patch(native.transport,'pin_regular_file',side_effect=lambda *a,**k:nullcontext(types.SimpleNamespace(path=Path('/fixture/odin'))))
        patch(native.transition,'transaction_session',side_effect=lambda *a:nullcontext(object()))
        self.arrival=patch(native.transition,'wait_for_single_live_endpoint',return_value=types.SimpleNamespace(ticket=Ticket(),timed_out=False,next_sequence=2))
        patch(native.target,'download_identity',return_value=dict(exact_fixture=True))
        patch(native.transport,'revalidate_pinned_path',return_value=None)
        patch(native.target.lane,'revalidate_binding',return_value=None)
        patch(native.transition,'revalidate_endpoint_ticket',return_value=dict(valid=True))
        patch(native.target,'transfer_completed',return_value=None)
        def execute(*args,**kwargs):
            kwargs['before_launch']();device.installed.append('A');device.mode='A'
            step=prior.prior.previous.owner.Step('install-android','transfer','A');device.proof(step)
            return dict(fixture=True),object()
        self.dispatch=patch(native.transport,'execute_odin_boot_only',side_effect=execute)
        return prior.prior.previous.owner.Session(self.root,directory,device),device

    def test_actual_coordinator_and_adapter_auto_return_without_physical_pause(self):
        selected,device=self.operation();result=selected.execute(attended=True)
        self.assertEqual(result['state'],'ANDROID_CLOSED');self.assertEqual(device.installed,['N','A'])
        self.assertEqual(device.actions.count('download-once'),1)
        self.assertEqual(self.arrival.call_count,1);self.assertEqual(self.dispatch.call_count,1)
        self.assertLessEqual(self.arrival.call_args.kwargs['timeout_sec'],90)
        self.assertEqual([r['data']['step'] for r in selected.rows() if r['event']=='effect-intent'],
            ['android-download','install-native-first','debian-reboot','debian-shutdown','install-android'])

    def test_legacy_still_pauses_for_physical_download(self):
        selected,device=self.operation(namespace='p460')
        self.assertEqual(selected.execute(attended=True)['state'],'AWAITING_PHYSICAL_DOWNLOAD')
        self.assertEqual(device.installed,['N']);self.dispatch.assert_not_called();self.arrival.assert_not_called()

    def test_expired_or_renewed_return_cannot_reach_arrival_or_a_dispatch(self):
        for fault in ('expired','renewed'):
            with self.subTest(fault=fault):
                self.setUp();selected,device=self.operation();device.fail_before=fault
                self.assertEqual(selected.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
                self.assertEqual(device.installed,['N']);self.assertEqual(device.actions.count('download-once'),1)
                self.dispatch.assert_not_called();self.arrival.assert_not_called()
                with self.assertRaises(ValueError):selected.resume(attended=True)
                self.assertEqual(device.actions.count('download-once'),1)

    def test_completed_automatic_a_then_failed_health_performs_health_only(self):
        selected,device=self.operation();device.health_failure=True
        self.assertEqual(selected.execute(attended=True)['state'],'AWAITING_ATTENDED_RECOVERY')
        self.assertEqual(device.installed,['N','A']);self.assertEqual(self.dispatch.call_count,1)
        device.health_failure=False;selected.recover(attended=True)
        self.assertEqual(device.installed,['N','A']);self.assertEqual(self.dispatch.call_count,1)
        self.assertEqual(device.actions.count('download-once'),1)


if __name__=='__main__':unittest.main()
