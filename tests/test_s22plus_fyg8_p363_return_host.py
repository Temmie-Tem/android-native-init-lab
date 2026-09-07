"""Durable intent, raw replay and timeout-only return-window qualification."""
import copy
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture,KEY,KEY_SHA256,BOOT_ID
import device_action_f1_live_v2 as live
import s22plus_fyg8_p363_return_host as owner


class Fixture(_ReceiptFixture):
    def __init__(self, run_dir):
        super().__init__(run_dir,variant='p363')

    def _session(self, ordinal):
        r=self.runtime;c=self.observer.control;nonce=b'n'*32
        rx=bytearray(r.DEVICE_BANNER)
        for stage in (0,r.DIAGNOSTIC_STAGE_OPEN_PARSED,r.DIAGNOSTIC_STAGE_RNG):
            rx.extend(self._frame(r.DIAGNOSTIC_FRAME_TYPE,0,struct.pack('<Ii',stage,0)))
        rx.extend(self._frame(r.FRAME_CHALLENGE,0,nonce))
        rx.extend(self._frame(r.FRAME_READY,1,self._tag(r.AUTH_DOMAIN_READY,nonce)))
        rx.extend(self._frame(r.FRAME_BOOT_ID,2,BOOT_ID+self.codec.compute_boot_id_tag(KEY,r.P363_RUN_ID,nonce,BOOT_ID)))
        output=b'uid=0 gid=0\n'
        rx.extend(self._frame(r.FRAME_DATA,3,output))
        rx.extend(self._frame(r.FRAME_EXIT,3,self.codec.EXIT.pack(0,0,0,len(output),1)))
        rx.extend(self._frame(c.FRAME_CONTROL_READY,5,c.READY_BODY+self._tag(c.DOMAIN_READY,nonce,5,c.READY_BODY)))
        rx.extend(self._frame(c.FRAME_CONTROL_ACK,5,c.ACK_BODY+self._tag(c.DOMAIN_ACK,nonce,5,c.ACK_BODY)))
        tx=bytearray(self._frame(r.FRAME_OPEN,0,r.P363_RUN_ID))
        tx.extend(self._frame(r.FRAME_AUTH,1,self._tag(r.AUTH_DOMAIN_OPEN,nonce)))
        for seq,cmd in ((3,r.DEFAULT_COMMANDS[0]),(4,r.DISPLAY_COMMAND)):
            tx.extend(self._frame(r.FRAME_EXEC,seq,self._tag(r.AUTH_DOMAIN_EXEC,nonce,seq,cmd)+cmd))
        tx.extend(self._frame(c.FRAME_CONTROL,5,c.CONTROL_BODY+self._tag(c.DOMAIN_CONTROL,nonce,5,c.CONTROL_BODY)))
        return bytes(rx),bytes(tx)

    def _qualification_proof(self):
        rx,tx=self._session(1)
        parsed=self.observer.parse_captured_session(self.codec,rx,tx,KEY)
        self.audits.append(parsed.session.audit);self.rx_streams.append(rx);self.tx_streams.append(tx)
        row=self.observer.validate_session_result(parsed,self.observer.DISPLAY_STEP)
        return self.observer.validate_qualification(dict(self.observer._fixed(),sessions=[row],expected_boot_sha256=row['boot_id_sha256']))

    def _lane(self):
        return dict(super()._lane(),observation_phase='before-native-return-control',post_control_observation=False)

    def _receipt_value(self):
        value=super()._receipt_value();value.pop('p363_readonly_research_shell_qualification')
        value[self.variant.proof_key]=self.proof
        value.update(session_count=1,command_count=3,pid1_framed_exec_proof=False,
            busybox_ash_command_proof=False,framed_session_closed=False,
            display_request_dispatched=True,display_response_observed=True,
            display_execution_proved=False,display_submitted_swaps=10,
            display_child_exited_before_ready=False,visible_panel_output='UNPROVED',
            control_acceptance_observed=True,control_requested_mode='download',
            control_ack_scope='acceptance-only',software_download_arrival='UNPROVED',
            kernel_boot_id_semantic=owner.spec.BOOT_ID_SEMANTIC,
            boot_receipt_semantic=owner.spec.BOOT_RECEIPT_SEMANTIC,
            proof_scope='submitted-swap-count-and-authenticated-control-acceptance',descriptor_close_error=None)
        path=self.run_dir/'p363-candidate-end.raw.json'
        raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
        receipt=live.p318_topology.publish_raw(path,raw,phase='candidate_end')
        value['p363_closure_snapshot']=dict(path=str(path),**receipt,capture_complete=True,
            error_type=None,continuity_proved=False,role='post-control-transport-diagnostic')
        row=self.proof['sessions'][0]
        request=dict(run_id_hex=owner.RUN_ID,mode='download',sequence=5,
            nonce_sha256=row['nonce_sha256'],kernel_boot_identity_sha256=row['boot_id_sha256'],
            boot_id_semantic=owner.spec.BOOT_ID_SEMANTIC,boot_receipt_semantic=owner.spec.BOOT_RECEIPT_SEMANTIC)
        value['p363_control_intent']=owner.write_intent(self.run_dir,binding=value['binding'],
            endpoint_identity_sha256=value['endpoint_identity_sha256'],lane=value['lane'],request=request)
        return value


class ReturnHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.fixture=Fixture(Path(self.tmp.name)/'run');self.prepared=self.fixture.prepared
        self.intent,self.intent_receipt=owner.read_intent(self.prepared.run_dir)
        self.state={}
        self.phase=self.prepared.run_dir/'rollback-phase.json'
        live._write_exclusive(self.phase,{'fixture':'exact backend phase'})

    def patches(self):
        stack=__import__('contextlib').ExitStack()
        stack.enter_context(mock.patch.object(live,'_state',side_effect=lambda _:copy.deepcopy(self.state)))
        stack.enter_context(mock.patch.object(live,'_save_state',side_effect=lambda _,v:self.state.update(copy.deepcopy(v))))
        stack.enter_context(mock.patch.object(live,'_p318_phase_paths',return_value=(self.phase,self.phase)))
        return stack

    def validate(self):
        with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)):
            return live._p345_validate_receipt(self.prepared,self.prepared.run_dir/'candidate-observer.json',self.fixture.spec)

    def test_raw_session_joins_sealed_intent_and_pre_control_lane(self):
        value=self.validate()
        self.assertTrue(value['valid_receipt']);self.assertTrue(value['control_acceptance_observed'])
        self.assertFalse(value['framed_session_closed'])
        self.assertEqual(value['software_download_arrival'],'UNPROVED')

    def test_missing_or_wrong_intent_cannot_qualify(self):
        path=self.prepared.run_dir/owner.INTENT_NAME
        path.unlink()
        with self.assertRaises((ValueError,OSError)):
            self.validate()
        changed=copy.deepcopy(self.intent);changed['request']['nonce_sha256']='1'*64
        live._write_exclusive(path,changed)
        with self.assertRaises(ValueError):self.validate()

    def test_intent_is_no_clobber_after_before_write_or_ack_uncertainty(self):
        for label in ('before-first-control-byte','partial-write','full-write','lost-ack'):
            with self.subTest(stage=label):
                with self.assertRaises(owner.ReturnControlError):
                    owner.write_intent(self.prepared.run_dir,binding=self.intent['binding'],
                        endpoint_identity_sha256=self.intent['endpoint_identity_sha256'],
                        lane=self.intent['lane'],request=self.intent['request'])
        self.assertEqual(owner.read_intent(self.prepared.run_dir)[1],self.intent_receipt)

    def test_partial_intent_and_fsync_failure_are_consumed(self):
        root=Path(self.tmp.name)/'partial';root.mkdir()
        (root/owner.INTENT_NAME).write_bytes(b'{')
        with self.assertRaises(owner.ReturnControlError):
            owner.write_intent(root,binding=self.intent['binding'],endpoint_identity_sha256='e'*64,
                lane=self.intent['lane'],request=self.intent['request'])
        root=Path(self.tmp.name)/'fsync';root.mkdir()
        actual=owner.core._write_exclusive
        def uncertain(path,value):
            actual(path,value)
            raise OSError('fixture failure after durable write')
        with mock.patch.object(owner.core,'_write_exclusive',side_effect=uncertain):
            with self.assertRaises(OSError):
                owner.write_intent(root,binding=self.intent['binding'],endpoint_identity_sha256='e'*64,
                    lane=self.intent['lane'],request=self.intent['request'])
        self.assertTrue(owner.exists(root))

    def test_exact_arrival_closes_window_without_physical_prompt(self):
        endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
        backend=SimpleNamespace(wait_download=mock.Mock(return_value=endpoint))
        stderr=io.StringIO()
        with self.patches(),mock.patch('sys.stderr',stderr):
            actual=live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None)
            self.assertEqual(actual,endpoint);self.assertEqual(backend.wait_download.call_count,1)
            self.assertTrue(live._p363_return_success(self.prepared,self.state))
        self.assertEqual(stderr.getvalue(),'')
        self.assertEqual(self.state['p363_return_window']['record']['software_causal_attribution'],'UNPROVED')

    def test_only_actual_timeout_selects_physical_fallback(self):
        endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
        backend=SimpleNamespace(wait_download=mock.Mock(side_effect=[live.DownloadWaitTimeout('timeout'),endpoint]))
        stderr=io.StringIO()
        with self.patches(),mock.patch('sys.stderr',stderr):
            self.assertEqual(live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None),endpoint)
            self.assertFalse(live._p363_return_success(self.prepared,self.state))
        self.assertEqual(backend.wait_download.call_count,2)
        self.assertIn('physical Download',stderr.getvalue())
        self.assertEqual(self.state['p363_return_window']['record']['outcome'],'software-window-timed-out')

    def test_usb_or_missing_ticket_failure_is_not_a_timeout(self):
        for error in (live.F1LiveError('missing ticket without timeout'),live.odin_core.OdinTransitionError('USB identity failure')):
            backend=SimpleNamespace(wait_download=mock.Mock(side_effect=error));stderr=io.StringIO()
            with self.patches(),mock.patch('sys.stderr',stderr):
                with self.assertRaises(type(error)):
                    live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None)
            self.assertEqual(backend.wait_download.call_count,1);self.assertEqual(stderr.getvalue(),'')
            self.assertFalse((self.prepared.run_dir/owner.WINDOW_NAME).exists())

    def test_orphan_window_reopens_for_observation_only(self):
        endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
        backend=SimpleNamespace(wait_download=mock.Mock(return_value=endpoint))
        with self.patches():
            live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None)
            first=owner.stable_record(self.prepared.run_dir/owner.WINDOW_NAME)[1]
            self.state.clear()  # Crash after record fsync, before state/journal update.
            with mock.patch.object(owner,'write_intent',side_effect=AssertionError('must not replay')):
                live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None)
            self.assertTrue(live._p363_return_success(self.prepared,self.state))
            self.assertEqual(first,owner.stable_record(self.prepared.run_dir/owner.WINDOW_NAME)[1])
        self.assertEqual(backend.wait_download.call_count,2)

    def test_window_timestamp_and_attribution_cannot_be_promoted(self):
        endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
        with self.patches():
            live._p363_wait_for_rollback(self.prepared,SimpleNamespace(wait_download=lambda *a:endpoint),self.prepared.run_dir,None)
            original=self.state['p363_return_window']['record']
            for key,value in (('closed_monotonic_ns',self.intent['created_monotonic_ns']+31_000_000_000),
                ('closed_monotonic_ns',self.intent['created_monotonic_ns']-1),('host_boot_sha256','f'*64),
                ('physical_intervention','NONE'),('software_causal_attribution','PROVED')):
                with self.subTest(field=key):
                    bad=copy.deepcopy(original);bad[key]=value
                    with self.assertRaises(ValueError):
                        owner.validate_window(bad,binding=self.intent['binding'],intent=self.intent,intent_receipt=self.intent_receipt)

    def test_partial_intent_or_window_cannot_block_preauthorized_rollback(self):
        for name in (owner.INTENT_NAME,owner.WINDOW_NAME):
            with self.subTest(record=name):
                path=self.prepared.run_dir/name
                if path.exists():path.unlink()
                path.write_bytes(b'{');path.chmod(0o400)
                endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
                backend=SimpleNamespace(wait_download=mock.Mock(return_value=endpoint))
                stderr=io.StringIO();self.state.clear()
                with self.patches(),mock.patch('sys.stderr',stderr):
                    self.assertEqual(live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None),endpoint)
                    self.assertFalse(live._p363_return_success(self.prepared,self.state))
                self.assertEqual(backend.wait_download.call_count,1)
                self.assertEqual(path.read_bytes(),b'{')
                self.assertIn('physical Download',stderr.getvalue())
                path.unlink()
                if name==owner.INTENT_NAME:live._write_exclusive(path,self.intent)

    def test_invalid_utf8_and_nonstring_window_outcome_preserve_recovery(self):
        path=self.prepared.run_dir/owner.WINDOW_NAME
        for payload in (b'\xff',b'{"outcome":[]}'):
            with self.subTest(payload=payload):
                if path.exists():path.unlink()
                path.write_bytes(payload);path.chmod(0o400);self.state.clear()
                endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
                backend=SimpleNamespace(wait_download=mock.Mock(return_value=endpoint))
                with self.patches(),mock.patch('sys.stderr',io.StringIO()):
                    self.assertEqual(live._p363_wait_for_rollback(self.prepared,backend,self.prepared.run_dir,None),endpoint)
                    self.assertFalse(live._p363_return_success(self.prepared,self.state))
                self.assertEqual(path.read_bytes(),payload)
                self.assertEqual(backend.wait_download.call_count,1)
        path.unlink();self.state.clear()
        endpoint=live.Endpoint('/dev/bus/usb/999/001',4,'d'*64)
        with self.patches():
            live._p363_wait_for_rollback(self.prepared,SimpleNamespace(wait_download=lambda *a:endpoint),self.prepared.run_dir,None)
        value=self.state['p363_return_window']['record']
        for bad in ([],{}):
            changed=copy.deepcopy(value);changed['outcome']=bad
            with self.assertRaises(owner.ReturnControlError):
                owner.validate_window(changed,binding=self.intent['binding'],intent=self.intent,intent_receipt=self.intent_receipt)

    def test_host_reboot_or_expired_window_does_not_renew_budget(self):
        with mock.patch.object(owner,'host_boot_sha256',return_value='f'*64):
            self.assertEqual(owner.remaining_window(self.intent),0)
        with mock.patch.object(owner.time,'monotonic_ns',return_value=self.intent['created_monotonic_ns']+31_000_000_000):
            self.assertEqual(owner.remaining_window(self.intent),0)


if __name__=='__main__':unittest.main()
