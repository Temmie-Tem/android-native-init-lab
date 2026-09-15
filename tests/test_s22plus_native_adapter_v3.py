"""Concrete V3 joins: real boot-only subprocess/raw producer and native C/PTY."""
from contextlib import contextmanager
import copy
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_adapter_v3 as adapter
import s22plus_native_records_v3 as records
import s22plus_native_session_v3 as owner
import s22plus_native_task_v3 as task
import test_s22plus_native_observation_v3 as observation_test
from test_s22plus_boot_only_f1_transport import make_ap


class AdapterTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name); self.private=self.root/'workspace/private'; self.private.mkdir(parents=True)
        self.directory=self.private/'operation'; self.directory.mkdir()
        self.client=adapter.Adapter(self.root,self.directory)
        self.odin=self.private/'odin-fixture'
        self.odin.write_text('#!/bin/sh\nprintf "Setup Connection\\nUpload Binaries\\nboot.img.lz4 100%%\\nClose Connection\\n"\n')
        self.odin.chmod(0o700)
        ap=self.private/'AP.tar.md5'; make_ap(ap)
        with adapter.transport.pin_boot_only_ap(ap,label='fixture',expected_size=ap.stat().st_size,
                expected_sha256=records.digest(ap.read_bytes())) as opened:
            member=adapter.transport.boot_only_member_receipt(opened,label='fixture')
        self.image=dict(ap=records.pin(ap),member=member)
        self.request=dict(A=self.image,N=self.image,E=self.image)
        self.configuration=dict(odin=records.pin(self.odin),lane={'fixture':True})

    def environment(self):
        @contextmanager
        def setup():
            ticket=adapter.transition.EndpointTicket('/dev/bus/usb/002/007','fixture-generation',1,0,'fixture-receipt','a'*64)
            with mock.patch.object(self.client,'configuration',return_value=self.configuration), \
                    mock.patch.object(self.client,'native_host',return_value=SimpleNamespace(holders=lambda:None)), \
                    mock.patch.object(adapter.target.lane,'revalidate_binding'), \
                    mock.patch.object(adapter.target,'download_identity',return_value={'fixture':True}), \
                    mock.patch.object(adapter.transition,'wait_for_single_live_endpoint',return_value=
                        adapter.transition.WaitResult(ticket,1,False)), \
                    mock.patch.object(adapter.transition,'revalidate_endpoint_ticket',return_value={'fixture':True}):
                yield
        return setup()

    def dispatch(self, step):
        def record(detail):
            records.Journal(self.directory/'journal').append('effect-intent',step=step.name,
                role=step.role,action=step.action,detail=detail)
        return record

    def test_actual_boot_only_subprocess_and_raw_recovery_after_result_cut(self):
        step=owner.Step('recover-android','transfer','A'); publish=adapter.publish
        def failure(path,value):
            if Path(path).name=='transport.json': raise OSError('publication cut')
            return publish(path,value)
        with self.environment(),mock.patch.object(adapter,'publish',side_effect=failure),self.assertRaises(OSError):
            self.client.transfer(step,self.request,guard=lambda:None,before_launch=self.dispatch(step))
        result=self.client.recover_transfer_result(step,self.request)
        self.assertTrue(result['completed'])
        with mock.patch.object(adapter.raw,'acquire_command',side_effect=AssertionError('H0 repair must not dispatch')):
            self.client.validate_result(step,result,self.request)
        self.assertEqual(len(list(self.client.folder(step.name).glob('attempt-*'))),1)

    def test_pc_readiness_failure_never_creates_a_transfer_intent(self):
        step=owner.Step('recover-android','transfer','A'); dispatch=mock.Mock()
        with self.environment(),mock.patch.object(self.client,'native_host',return_value=
                SimpleNamespace(holders=mock.Mock(side_effect=ValueError('root census unavailable')))), \
                self.assertRaises(ValueError):
            self.client.transfer(step,self.request,guard=lambda:None,before_launch=dispatch)
        dispatch.assert_not_called()
        self.assertFalse(list(self.client.folder(step.name).glob('attempt-*/odin.capture.json')))
        # A new original-recovery preparation is permitted before dispatch,
        # while keeping the failed attempt's evidence directory.
        with self.environment():
            result=self.client.transfer(step,self.request,guard=lambda:None,before_launch=self.dispatch(step))
        self.assertTrue(result['completed'])
        self.assertEqual(len(list(self.client.folder(step.name).glob('attempt-*'))),2)

    def test_expired_original_download_window_does_not_renew_at_transfer(self):
        step=owner.Step('install-experiment','transfer','E')
        records.Journal(self.directory/'journal').append('effect-intent',step='native-start',action='observe',
            role='N',detail=dict(departure_deadline_ns=1))
        dispatch=mock.Mock()
        with self.environment(),self.assertRaisesRegex(ValueError,'window expired'):
            self.client.transfer(step,self.request,guard=lambda:None,before_launch=dispatch)
        dispatch.assert_not_called()

    def test_slow_durable_intent_cannot_extend_download_dispatch_deadline(self):
        step=owner.Step('recover-android','transfer','A');current=[records.clock()]
        original=self.dispatch(step)
        def delayed(detail):
            original(detail);current[0]+=100_000_000_000
        with self.environment(),mock.patch.object(adapter,'clock',side_effect=lambda:current[0]), \
                self.assertRaisesRegex(ValueError,'during intent publication'):
            self.client.transfer(step,self.request,guard=lambda:None,before_launch=delayed)
        intents=[row for row in records.Journal(self.directory/'journal').rows() if row['event']=='effect-intent']
        self.assertEqual(len(intents),1)
        self.assertFalse(list(self.client.folder(step.name).glob('attempt-*/odin.capture.json')))

    def test_prior_tail_attempt_is_shared_across_operation_directories(self):
        prior=self.private/'terminal.json'; records.publish(prior,dict(fixture=True))
        request=dict(prior_terminal=records.pin(prior))
        records.publish(self.directory/'operation.json',request)
        with mock.patch.object(adapter.registry,'begin_f1_owner'):
            self.client.claim_tail(request)
        another=self.private/'operation-2'; another.mkdir(); records.publish(another/'operation.json',request)
        with mock.patch.object(adapter.registry,'begin_f1_owner'),self.assertRaises(FileExistsError):
            adapter.Adapter(self.root,another).claim_tail(request)
        self.assertFalse((another/'tail-attempt.json').exists())

    def test_storage_tail_claim_preserves_its_already_consumed_recovery_owner(self):
        prior=self.private/'terminal.json';records.publish(prior,dict(fixture=True))
        request=dict(prior_terminal=records.pin(prior))
        operation=records.publish(self.directory/'operation.json',request)
        adapter.registry.begin_f1_owner(self.root,self.directory,operation['sha256'])
        self.client.claim_tail(request)
        adapter.registry.require_f1_owner(self.root,self.directory,operation['sha256'])
        self.assertTrue(self.client.native_attempt_started(request))
        another=self.private/'different-operation';another.mkdir()
        with self.assertRaises(adapter.registry.RegistryError):
            adapter.registry.require_f1_owner(self.root,another,operation['sha256'])

    def test_original_a_must_still_exist_at_native_transfer_but_is_not_read_for_completed_a(self):
        step=owner.Step('install-experiment','transfer','E')
        other=self.private/'native.tar.md5';make_ap(other)
        self.request['E']=dict(ap=records.pin(other),member=self.image['member'])
        records.Journal(self.directory/'journal').append('effect-intent',step='native-start',action='observe',
            role='N',detail=dict(departure_deadline_ns=records.clock()+30_000_000_000))
        Path(self.image['ap']['path']).unlink()
        dispatch=mock.Mock()
        with self.environment(),self.assertRaises((OSError,adapter.transport.F1TransportError)):
            self.client.transfer(step,self.request,guard=lambda:None,before_launch=dispatch)
        dispatch.assert_not_called()
        make_ap(Path(self.image['ap']['path']))
        recover=owner.Step('recover-android','transfer','A')
        with self.environment():self.client.transfer(recover,self.request,guard=lambda:None,before_launch=self.dispatch(recover))
        Path(self.image['ap']['path']).unlink()
        self.assertTrue(self.client.android_transfer_completed(self.request))

    def test_completed_a_remains_completed_after_the_gpt_ordinary_reboot_intent(self):
        step=owner.Step('recover-android','transfer','A')
        with self.environment():self.client.transfer(step,self.request,guard=lambda:None,before_launch=self.dispatch(step))
        self.request['operation']='gpt-reserve'
        records.Journal(self.directory/'journal').append('effect-intent',step='android-reboot',action='reboot',role='A',detail={})
        Path(self.image['ap']['path']).unlink()
        self.assertTrue(self.client.android_transfer_completed(self.request))
        records.Journal(self.directory/'journal').append('effect-intent',step='recover-native',action='transfer',role='N',detail={})
        self.assertFalse(self.client.android_transfer_completed(self.request))

    def test_grant_cannot_expand_task_clock_capacity_or_recovery(self):
        value=dict(seconds=600,operation_budget=2,recovery_mode='attended')
        path=self.directory/'task.json'; records.publish(path,value); receipt=records.pin(path)
        grant=dict(schema=records.SCHEMA,task=receipt,directory=str(self.directory),host_boot=records.host_boot(),
            opened_ns=1,deadline_ns=600_000_000_001,operation_budget=2,recovery_mode='attended',
            operator_statement='fixture returned statement',returned_approval=task.approval_text(value,receipt))
        task.validate_grant(value,grant,self.directory/'grant.json')
        for changes in (dict(deadline_ns=grant['deadline_ns']+1),dict(operation_budget=3),dict(recovery_mode='deferred')):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                task.validate_grant(value,dict(grant,**changes),self.directory/'grant.json')

    def test_same_task_census_requires_completed_bootstrap_admission_and_unused_tail(self):
        directory=self.private/'task';directory.mkdir()
        value=dict(operations=['bootstrap','storage-census'],N=self.image,A=self.image,
            admission=None,prior_terminal=None,reentry=False,hud=False,usb_reconnect=False)
        grant=dict(task=records.publish(directory/'task.json',value),directory=str(directory))
        with self.assertRaisesRegex(ValueError,'no V3 admission and closed tail'):
            self.client.prepare('storage-census',grant)
        completed=directory/'operation-0001';completed.mkdir()
        tail=records.publish(completed/'terminal.json',dict(terminal_state='NATIVE_CLOSED_HEALTHY'))
        with self.assertRaisesRegex(ValueError,'no V3 admission and closed tail'):
            self.client.prepare('storage-census',grant)
        admission=records.publish(completed/'admission.json',dict(fixture=True))
        with mock.patch.object(self.client,'admission') as verify_admission, \
                mock.patch.object(self.client,'tail') as verify_tail:
            request=self.client.prepare('storage-census',grant)
            self.assertEqual(request['prior_terminal'],tail);self.assertEqual(request['admission'],admission)
            verify_admission.assert_called_once_with(admission,self.image,value)
            verify_tail.assert_called_once_with(tail,self.image,value)
            claim=self.client.tail_claim_path(tail);claim.parent.mkdir(parents=True,exist_ok=True)
            records.publish(claim,dict(fixture=True))
            with self.assertRaisesRegex(ValueError,'already has an authentication attempt'):
                self.client.prepare('storage-census',grant)

    def test_native_bootstrap_requires_predecessor_admission_and_unattempted_tail(self):
        directory=self.private/'task';directory.mkdir()
        tail=records.publish(self.private/'predecessor-terminal.json',dict(fixture='old native tail'))
        admission=records.publish(self.private/'predecessor-admission.json',dict(fixture='old N admission'))
        start=dict(N=dict(self.image,run_id_hex='a'*32),admission=admission,prior_terminal=tail)
        value=dict(operations=['bootstrap'],N=self.image,A=self.image,
            admission=None,prior_terminal=None,reentry=False,hud=False,usb_reconnect=False,
            bootstrap_start=start)
        grant=dict(task=records.publish(directory/'task.json',value),directory=str(directory))
        with mock.patch.object(self.client,'admission') as verify_admission, \
                mock.patch.object(self.client,'tail') as verify_tail:
            request=self.client.prepare('bootstrap',grant)
            self.assertEqual(request['S'],start['N'])
            self.assertEqual(request['prior_terminal'],tail)
            verify_admission.assert_called_once_with(admission,start['N'],value)
            verify_tail.assert_called_once_with(tail,start['N'],value)
            claim=self.client.tail_claim_path(tail);claim.parent.mkdir(parents=True,exist_ok=True)
            records.publish(claim,dict(fixture=True))
            with self.assertRaisesRegex(ValueError,'already attempted'):self.client.prepare('bootstrap',grant)

    def test_native_bootstrap_context_keeps_predecessor_tail_distinct_from_fresh_n(self):
        predecessor=dict(run_id_hex='a'*32)
        request=dict(operation='bootstrap',reentry=False,hud=False,N=self.image,S=predecessor,
            prior_terminal={'fixture':'tail'})
        prior=dict(nonce_sha256='1'*64,kernel_boot_identity_sha256='2'*64)
        last=dict(nonce_sha256='3'*64,kernel_boot_identity_sha256='2'*64)
        with mock.patch.object(self.client,'configuration',return_value={}), \
                mock.patch.object(self.client,'tail',return_value=prior) as tail, \
                mock.patch.object(self.client,'recover_step_result',return_value={'proof':last}):
            first=self.client.context(owner.operation_steps(request)[0],request)
            self.assertEqual(first['previous'],prior);self.assertFalse(first['first_boot'])
            tail.assert_called_with(request['prior_terminal'],predecessor,{})
            new=self.client.context(owner.operation_steps(request)[2],request)
            self.assertIsNone(new['previous']);self.assertTrue(new['first_boot'])
            self.assertEqual(new['seen_nonces'],['1'*64,'3'*64])


class NativeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        observation_test.ObservationTests.setUpClass.__func__(cls)

    running=observation_test.ObservationTests.running

    def test_completed_detach_aggregate_cut_reconstructs_through_concrete_adapter(self):
        with tempfile.TemporaryDirectory() as temporary,self.running() as ctx:
            root=Path(temporary); directory=root/'workspace/private/operation'; directory.mkdir(parents=True)
            client=adapter.Adapter(root,directory); step=owner.steps('bootstrap')[2]
            request=dict(operation='bootstrap',reentry=False,hud=False,usb_reconnect=False,prior_terminal=None,N=self.image)
            publish=adapter.native.publish
            def unavailable(path,value):
                if Path(path).name=='attempt.json': raise OSError('aggregate publication cut')
                return publish(path,value)
            with mock.patch.object(client,'wait_native'),mock.patch.object(client,'native_host',return_value=
                    observation_test.HostFixture(ctx)),mock.patch.object(adapter.native,'publish',side_effect=unavailable), \
                    self.assertRaises(adapter.native.NativeClosePublicationError):
                client.observe(step,request,guard=lambda:None,before_terminal=lambda:None)
            self.assertIsNone(ctx.fd)
            self.assertTrue(client.final_protocol_completed(step,request))
            with mock.patch.object(adapter.native,'observe',side_effect=AssertionError('no native replay')):
                result=client.recover_step_result(step,request)
                client.validate_result(step,result,request)
            self.assertTrue(result['proof']['native_health_proved'])
            self.assertTrue((client.folder(step.name)/'attempt.json').exists())


if __name__=='__main__': unittest.main()
