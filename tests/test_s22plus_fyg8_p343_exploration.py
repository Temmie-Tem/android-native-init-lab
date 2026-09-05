"""Actual private lease journal and host-first action codec; host fixtures only."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import threading
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'workspace/public/src/scripts/revalidation'),str(ROOT/'tests')]
import s22plus_fyg8_p343_exploration_session as resident
import s22plus_fyg8_p343_exploration_action as actions
import test_s22plus_fyg8_p335_resident_session as lease_fixture
import test_s22plus_fyg8_p335_retained_listener_acm_observer as fixture
import test_s22plus_fyg8_host_first_open as pty
import device_action_f1_live_v2 as live


def binding():
    value = lease_fixture.binding()
    value['candidate']['run_id'] = 'c343'+'ab'*14
    value['catalog'] = resident.catalog_for(value['candidate']['run_id'])
    value['recovery']['owner'] = resident.OWNER
    return value


class ExplorationIntegrationTests(unittest.TestCase):
    def test_actual_command_results_publish_and_reopen_summary(self):
        cases=[(name,False) for name in resident.ACTION_NAMES]+[('kernel',True)]
        for action, publication_cut in cases:
            with self.subTest(action=action, publication_cut=publication_cut), tempfile.TemporaryDirectory() as temporary:
                record, base, codec, selected = self.exercise_codec(action=action)
                self.assertFalse(hasattr(record.result.commands[1], 'signal_number'))
                root=Path(temporary); base.ROOT=root
                value=binding()
                value['candidate']['run_id']=live.p343_open_read_runtime.P343_RUN_ID_HEX
                value['catalog']=resident.catalog_for(value['candidate']['run_id'])
                value['per_boot_id']=hashlib.sha256(record.boot_id).hexdigest()
                lease_root=root/resident.DIRECTORY;lease_root.mkdir(mode=0o700)
                lease=resident.ResidentLease.publish(lease_root,value,lease_fixture.observation())
                endpoint=types.SimpleNamespace(identity_sha256='fixture',tty_class=Path('/no-device'))
                base._select_endpoint=lambda *args:(endpoint,{'fixture':'same'})
                real_write=base._write_once
                def write(path,payload):
                    if publication_cut and path.name=='result.json':
                        raise OSError('fixture result publication failure')
                    return real_write(path,payload)
                base._write_once=write
                prepared=types.SimpleNamespace(run_dir=root)
                def exchange(*args):
                    args[8].write_stdout(bytes(record.result.audit.rx))
                    return record
                with mock.patch.object(actions,'context',return_value=(lease,value,fixture.TEST_KEY,set())), \
                     mock.patch.object(actions,'action_codec',return_value=(base,codec,selected)), \
                     mock.patch.object(actions,'_exchange',side_effect=exchange), \
                     mock.patch.object(live.cdc_acm_observer,'_udev_properties',return_value={
                         'ID_MM_DEVICE_IGNORE':'1','ID_MM_PORT_IGNORE':'1','ID_USB_INTERFACE_NUM':'00'}):
                    if publication_cut:
                        with self.assertRaisesRegex(live.F1LiveError,'only exact rollback'):
                            actions._run_locked(live,prepared,action)
                    else:
                        result=actions._run_locked(live,prepared,action)
                if publication_cut:
                    reopened=resident.ResidentLease.open(lease_root)
                    self.assertTrue(reopened.snapshot()['rollback_required'])
                    with self.assertRaises(resident.RollbackRequired):
                        reopened.begin_action(action,value)
                    directory=root/actions.EVIDENCE_DIRECTORY/'action-01'
                    self.assertTrue((directory/'failure.json').exists())
                    self.assertEqual((directory/'session.tx.bin').read_bytes(),record.raw_tx)
                    self.assertEqual((directory/'selected.stdout.bin').read_bytes(),record.result.commands[1].output)
                    with mock.patch.object(resident,'binding_for',return_value=value), \
                         mock.patch.object(live,'_reopen_candidate_observation',return_value={}):
                        self.assertFalse(resident.action_summary(live,prepared)['proved'])
                    continue
                self.assertEqual(result['verdict'],'PASS_P343_NAMED_READONLY_ACTION')
                path=root/actions.EVIDENCE_DIRECTORY/'action-01/result.json'
                published=live._read_json(path,'actual action publication')
                self.assertEqual([c['signal_number'] for c in published['commands']],[0,0,0])
                self.assertEqual((path.parent/'selected.stdout.bin').read_bytes(),record.result.commands[1].output)
                self.assertEqual(resident.ResidentLease.open(lease_root).snapshot()['actions_completed'],1)
                with mock.patch.object(resident,'binding_for',return_value=value), \
                     mock.patch.object(live,'_reopen_candidate_observation',return_value={}):
                    summary=resident.action_summary(live,prepared)
                self.assertTrue(summary['proved'])
                self.assertEqual(summary['completed_actions'],1)

    def test_close_summary_distinguishes_zero_ok_pending_failed_and_malformed(self):
        for case in ('zero','ok','pending','failed','malformed'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary); lease_root=root/resident.DIRECTORY;lease_root.mkdir(mode=0o700)
                value=binding()
                lease=resident.ResidentLease.publish(lease_root,value,lease_fixture.observation(),now_ns=1)
                if case!='zero':
                    intent=lease.begin_action('memory',value,now_ns=2)
                    if case!='pending':
                        base=actions._base();base.ROOT=root
                        parent=root/actions.EVIDENCE_DIRECTORY;base._mkdir(parent)
                        directory=parent/'action-01';base._mkdir(directory)
                        commands=[{'name':name,'ok':True,'exit_code':0,'signal_number':0,
                                   'command':base.identity(command)} for name,command in zip(
                            ('identity','memory','session-nonce'),
                            actions.exploration.session_commands('memory',value['candidate']['run_id']))]
                        if case=='malformed':commands[1]=None
                        result={'schema':actions.SCHEMA,'action':'memory','ordinal':1,
                                'classification':'accepted' if case!='failed' else 'uncertain',
                                'boot_id_sha256':value['per_boot_id'],'commands':commands}
                        name='failure.json' if case=='failed' else 'result.json'
                        receipt=base._write_once(directory/name,base.canonical(result))
                        lease.record_action_result(intent,{'status':'uncertain' if case=='failed' else 'ok',
                            'receipt_bytes':receipt['size'],'receipt_sha256':receipt['sha256']},value,now_ns=3)
                prepared=types.SimpleNamespace(run_dir=root)
                with mock.patch.object(resident,'binding_for',return_value=value), \
                     mock.patch.object(live,'_reopen_candidate_observation',return_value={}):
                    summary=resident.action_summary(live,prepared)
                self.assertEqual(summary['proved'],case=='ok')

    def test_capture_finalize_failure_still_preserves_tx_and_consumed_result(self):
        class Lease:
            lease={'expires_monotonic_ns':actions.time.monotonic_ns()+60_000_000_000}
            actions=[]
            results=[]
            def snapshot(self):
                return {'rollback_required':False,'actions_started':0}
            def begin_action(self,*args):
                return {'ordinal':1,'action':'memory'}
            def record_action_result(self,intent,value,binding):
                self.results.append(value)
        lease=Lease()
        base=actions._base()
        endpoint=types.SimpleNamespace(identity_sha256='fixed',tty_class=Path('/unused-host-fixture'))
        base._select_endpoint=lambda *args:(endpoint,{'fixture':'same'})
        error=OSError('fixture exchange failed')
        error.audit=types.SimpleNamespace(tx=bytearray(b'fixture-OPEN'),current_stage='boot-id-read',failure_stage='boot-id-read')
        real_writer=actions.raw_capture.RawCaptureWriter
        class FinalizeCut(real_writer):
            def finalize(self,**kwargs):
                super().finalize(**kwargs)
                raise OSError('fixture post-finalize publication cut')
        with tempfile.TemporaryDirectory() as temporary:
            prepared=types.SimpleNamespace(run_dir=Path(temporary))
            base.ROOT = prepared.run_dir
            facade=types.SimpleNamespace(F1LiveError=live.F1LiveError,
                cdc_acm_observer=types.SimpleNamespace(_udev_properties=lambda *args:{
                    'ID_MM_DEVICE_IGNORE':'1','ID_MM_PORT_IGNORE':'1','ID_USB_INTERFACE_NUM':'00'}))
            with mock.patch.object(actions,'context',return_value=(lease,binding(),fixture.TEST_KEY,set())), \
                 mock.patch.object(actions,'action_codec',return_value=(base,None,())), \
                 mock.patch.object(actions,'_exchange',side_effect=error), \
                 mock.patch.object(actions.raw_capture,'RawCaptureWriter',FinalizeCut):
                with self.assertRaises(live.F1LiveError):
                    actions._run_locked(facade,prepared,'memory')
            directory=prepared.run_dir/actions.EVIDENCE_DIRECTORY/'action-01'
            self.assertEqual((directory/'failure.tx.bin').read_bytes(),b'fixture-OPEN')
            result=json.loads((directory/'failure.json').read_bytes())
            self.assertEqual(result['retention_errors'],['OSError'])
            self.assertEqual(lease.results[0]['status'],'uncertain')

    def test_five_names_reuse_one_shot_journal_and_expiry(self):
        self.assertEqual(resident.MAX_ACTIONS,16)
        self.assertEqual(resident.MAX_LEASE_SECONDS,3600)
        self.assertEqual(len(resident.ACTION_NAMES),5)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lease = resident.ResidentLease.publish(root,binding(),lease_fixture.observation(),now_ns=100,duration_seconds=10)
            intent = lease.begin_action('memory',binding(),now_ns=101)
            with self.assertRaises(resident.RollbackRequired):
                lease.begin_action('kernel',binding(),now_ns=102)
            lease.record_action_result(intent,lease_fixture.result(),binding(),now_ns=103)
            reopened = resident.ResidentLease.open(root)
            self.assertEqual(reopened.snapshot(now_ns=104)['actions_completed'],1)
            with self.assertRaises(resident.RollbackRequired):
                reopened.begin_action('processes',binding(),now_ns=11_000_000_100)
            self.assertTrue(resident.ResidentLease.open(root).snapshot(now_ns=105)['rollback_required'])
            with self.assertRaises(lease_fixture.p335.LeaseError):
                lease_fixture.p335.ResidentLease.open(root)

    def test_durable_failed_action_has_no_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            lease=resident.ResidentLease.publish(root,binding(),lease_fixture.observation(),now_ns=1)
            intent=lease.begin_action('usb-state',binding(),now_ns=2)
            lease.record_action_result(intent,lease_fixture.result('uncertain'),binding(),now_ns=3)
            with self.assertRaises(resident.RollbackRequired):
                lease.begin_action('usb-state',binding(),now_ns=4)
            self.assertEqual(len(lease.actions),1)

    def exercise_codec(self, wrong_boot=False, action='memory'):
        # Actual P343 codec on a local PTY, with no device authority.
        facade=types.SimpleNamespace(_open_header_initial_observer_module=live._open_header_initial_observer_module,
            p343_open_read_runtime=live.p343_open_read_runtime,p343_open_read_observer=live.p343_open_read_observer,
            host_first_open=live.host_first_open)
        base,module,selected=actions.action_codec(facade,action,2)
        self.assertEqual(base.runtime.DEFAULT_COMMANDS,selected)
        helper=fixture.P335RetainedListenerObserverTests()
        source=textwrap.dedent(inspect.getsource(helper._serve_sessions))
        old='            peer.sendall(runtime.DEVICE_BANNER)\n            opened = self._receive_frame(peer)'
        self.assertEqual(source.count(old),1)
        source=source.replace(old,'            opened = self._receive_frame(peer)\n            peer.sendall(runtime.DEVICE_BANNER)')
        if action != 'kernel':
            source=source.replace('b"Linux p335 5.10.198 aarch64 GNU/Linux\\n"', 'b"bounded selected query output"')
        scope=dict(vars(fixture),observer=module,runtime=base.runtime)
        exec(compile(source,'<P343 action fixture>','exec'),scope)
        def receive(peer):
            header=helper._receive_exact(peer,module.HEADER.size)
            length=module.HEADER.unpack(header)[3]
            return module.decode_frame(header+helper._receive_exact(peer,length))
        helper._receive_frame=receive
        serve=types.MethodType(scope['_serve_sessions'],helper)
        master,slave=os.openpty(); errors=[]
        thread=threading.Thread(target=serve,args=(pty.Peer(master),fixture.NONCES[:1],errors))
        with tempfile.TemporaryDirectory() as temporary:
            writer=actions.raw_capture.RawCaptureWriter(Path(temporary),'action',stdout_maximum=512*1024,stderr_maximum=4096)
            try:
                live.cdc_acm_observer.ObserverSession._raw_tty(None,slave)
                os.set_blocking(slave,False)
                thread.start()
                expected='0'*64 if wrong_boot else hashlib.sha256(fixture.BOOT_ID).hexdigest()
                if wrong_boot:
                    with self.assertRaises(module.AuthObserverError) as caught:
                        base._exchange_before_exec_bound(slave,fixture.TEST_KEY,writer,expected,set())
                    audit=caught.exception.audit
                    self.assertEqual(audit.failure_stage,'boot-id-read')
                    self.assertNotIn(selected[1],bytes(audit.tx))
                    handle=writer.finalize(returncode=None,producer_error_type='AuthObserverError')
                    self.assertTrue(actions.raw_capture.read_stdout(handle,maximum=512*1024))
                else:
                    result=base._exchange_before_exec_bound(slave,fixture.TEST_KEY,writer,expected,set())
                    self.assertEqual(tuple(c.command for c in result.commands),selected)
                    self.assertTrue(result.audit.done_seen)
                    record=module._record_success(0,1,slave,result)
                    module._validate_one_session(record,fixture.BOOT_ID)
                    handle=writer.finalize(returncode=0)
                    self.assertEqual(actions.raw_capture.read_stdout(handle,maximum=512*1024),bytes(result.audit.rx))
            finally:
                if not writer.finished:
                    writer.finalize(returncode=None,producer_error_type='TestFailure')
                os.close(slave);thread.join(3);os.close(master)
            self.assertFalse(thread.is_alive())
            if not wrong_boot:
                self.assertEqual(errors,[])
                return record, base, module, selected

    def test_actual_selected_action_authentication_and_raw_capture(self):
        for action in resident.ACTION_NAMES:
            self.exercise_codec(action=action)

    def test_wrong_boot_stops_before_selected_exec_and_retains_raw(self):
        self.exercise_codec(wrong_boot=True)


if __name__=='__main__':
    unittest.main()
