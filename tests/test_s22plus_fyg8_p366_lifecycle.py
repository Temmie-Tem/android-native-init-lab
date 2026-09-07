"""Reuse the qualified lifecycle corpus with P366's real generated C and writers.

Only platform device identities/ADB/Odin and the C fixture's kernel calls are
synthetic. The new binding, departure witness, CONTROL join, raw parser, state,
result, and CLOSED recovery consumers execute unchanged production code.
"""
from pathlib import Path
import sys
import types
from unittest import mock
import unittest
from s22plus_native_departure_h0_support import Fixture, departure, return_host


def load_fixture(name,path):
    module=types.ModuleType(name);module.__file__=str(path.resolve())
    sys.modules[name]=module
    raw=path.read_text().replace('p365','p366').replace('P365','P366')
    exec(compile(raw,str(path)+'#p366', 'exec'),module.__dict__)
    return module

support=load_fixture('s22plus_p366_h0_support',Path('tests/s22plus_p365_h0_support.py'))
fixture=load_fixture('_p366_lifecycle_fixture',Path('tests/test_s22plus_fyg8_p365_persistence.py'))
live=fixture.live
BaseReceipt=fixture.Receipt


class DepartureReceipt(BaseReceipt):
    def _lane(self):
        lane=super()._lane()
        if getattr(self,'departure_receipt',None) is not None:
            lane['native_usb_departure_binding']=self.departure_receipt
        return lane
    def observe(self,**kwargs):
        platform=Fixture(self.run_dir/'fixture-platform')
        write=live.p366_return_host.write_intent
        def bind(run_dir,**args):
            self.departure_receipt=platform.capture(run_dir,args['binding'],args['request'])
            args['lane']=self._lane()
            return write(run_dir,**args)
        with mock.patch.object(live.p366_return_host,'write_intent',side_effect=bind):
            return super().observe(**kwargs)

fixture.Receipt=DepartureReceipt
BaseBackend=fixture.Backend

class OrderedBackend(BaseBackend):
    def wait_download(self,prepared,run_dir,lease,timeout_sec):
        intent_path=prepared.run_dir/return_host.INTENT_NAME
        observation_path=prepared.run_dir/departure.OBSERVATION_NAME
        if intent_path.exists():
            intent,ir=return_host.read_intent(prepared.run_dir)
            if observation_path.exists():
                witness,_=departure.read_observation(prepared.run_dir,intent,ir)
                if witness['status']=='absent' and timeout_sec<=30:
                    assert return_host.remaining_window(intent)>0
                elif timeout_sec<=30:
                    raise AssertionError('Odin software window opened without departure')
            elif timeout_sec<=30:
                raise AssertionError('Odin called before native departure witness')
        return super().wait_download(prepared,run_dir,lease,timeout_sec)

fixture.Backend=OrderedBackend


class P366Lifecycle(fixture.PersistenceTests):
    def patches(self):
        stack=super().patches()
        def absent(path,capture_dir):
            raise departure.usbfs.UsbfsEndpointDeparture(path)
        stack.enter_context(mock.patch.object(departure,'_snapshot',side_effect=absent))
        return stack

    def test_barrier_io_error_stops_then_same_journal_recovers_without_control_replay(self):
        p=self.prepared();backend=fixture.Backend(p,self.peer,'normal')
        with self.patches():
            with mock.patch.object(departure,'_snapshot',side_effect=PermissionError(13,'fixture barrier')):
                # Receipt.capture uses its own scoped snapshot fixture before
                # CONTROL; this failure is reached only by the real barrier.
                with self.assertRaisesRegex(live.F1LiveError,'departure observation failed'):
                    live.execute_prepared(p,p.approval_token,backend)
            journal=live.core.Journal(p.run_dir/'transaction',p.binding_sha256)
            self.assertEqual(journal.state(),'OBSERVED')
            self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate'])
            # This existing error witness dispatches physical recovery outside
            # the local-record catch. A backend OSError must never be retried.
            with mock.patch.object(backend,'wait_download',side_effect=OSError('USB backend failure')) as wait:
                with self.assertRaisesRegex(OSError,'USB backend failure'):
                    live._p363_wait_for_rollback(p,backend,p.run_dir/'odin-endpoints',None)
                self.assertEqual(wait.call_count,1)
            intent_before=(p.run_dir/return_host.INTENT_NAME).read_bytes()
            with mock.patch.object(self.peer,'run',side_effect=AssertionError('no CONTROL replay')):
                result=live.recover_prepared(p,backend)
            self.assertEqual(result['current_state'],'CLOSED')
            self.assertFalse(result['recovery_required'])
            self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
            self.assertEqual((p.run_dir/return_host.INTENT_NAME).read_bytes(),intent_before)
            self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])

    def test_native_helper_delta_is_identity_only(self):
        import s22plus_fyg8_p365_research_shell_runtime as previous_runtime
        old=previous_runtime.P365_HELPER_TEMPLATE
        new=support.runtime.P366_HELPER_TEMPLATE.replace(b'p366',b'p365').replace(b'P366',b'P365')
        escaped=lambda raw: ''.join('\\x%02x'%byte for byte in raw).encode()
        new=new.replace(escaped(b'c366f1e0a90b5e6d7c8a9b0c1d2e3f0b'),escaped(b'c365f1e0a90b5e6d7c8a9b0c1d2e3f0b'))
        self.assertEqual(new,old)

    def test_production_before_control_hook_binds_exact_endpoint(self):
        p=self.prepared();platform=Fixture(p.run_dir/'hook-platform')
        session=live._P363ObserverSession.__new__(live._P363ObserverSession)
        session.namespace='p366';session.run_dir=p.run_dir;session.endpoint=platform.endpoint
        session.base=types.SimpleNamespace(binding=live._candidate_observer_binding(p))
        session.auth_key=support.KEY;session.qualification_observer=support.observer
        session._endpoint_exact=mock.Mock(return_value=True)
        request=dict(run_id_hex=return_host.RUN_ID,mode='download',sequence=5,
            boot_id_semantic=return_host.spec.BOOT_ID_SEMANTIC,
            boot_receipt_semantic=return_host.spec.BOOT_RECEIPT_SEMANTIC,
            nonce_sha256='1'*64,kernel_boot_identity_sha256='2'*64)
        def qualify(*args,**kwargs):
            kwargs['before_control'](request)
            return 'qualified-fixture'
        with mock.patch.object(live._P345ObserverSession,'_lane_supplement',return_value={'accepted_for_p324':True}),mock.patch.object(support.observer,'qualify',side_effect=qualify),mock.patch.object(departure,'_snapshot',return_value=platform.snapshot):
            result=session._qualify_on_descriptor(None,123,None,99999)
        self.assertEqual(result,'qualified-fixture')
        self.assertEqual(session._endpoint_exact.call_count,2)
        intent,receipt=return_host.read_intent(p.run_dir,binding=live._candidate_observer_binding(p))
        self.assertEqual(receipt,session.control_intent_receipt)
        departure.read_binding(p.run_dir,intent)

arm64_fixture=load_fixture('_p366_arm64_fixture',Path('tests/test_s22plus_fyg8_p365_arm64_flags.py'))
P366Arm64Flags=arm64_fixture.Arm64FlagTests

if __name__=='__main__':unittest.main()
