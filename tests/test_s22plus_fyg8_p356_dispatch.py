"""Real authenticated prefix/replay and durable P356 dispatch-only evidence."""
import copy
import hashlib
import io
import json
from pathlib import Path
import socket
import struct
import runpy
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256, BOOT_ID
import device_action_f1_live_v2 as live


class Fixture(_ReceiptFixture):
    def __init__(self, run_dir):
        super().__init__(run_dir, variant='p356')

    def _session(self, ordinal):
        r=self.runtime;nonce=b'n'*32
        rx=bytearray(r.DEVICE_BANNER)
        for stage in (0,r.DIAGNOSTIC_STAGE_OPEN_PARSED,r.DIAGNOSTIC_STAGE_RNG):
            rx.extend(self._frame(r.DIAGNOSTIC_FRAME_TYPE,0,struct.pack('<Ii',stage,0)))
        rx.extend(self._frame(r.FRAME_CHALLENGE,0,nonce))
        rx.extend(self._frame(r.FRAME_READY,1,self._tag(r.AUTH_DOMAIN_READY,nonce)))
        rx.extend(self._frame(r.FRAME_BOOT_ID,r.P335_BOOT_ID_SEQUENCE,BOOT_ID+self.codec.compute_boot_id_tag(KEY,r.P356_RUN_ID,nonce,BOOT_ID)))
        output=b'uid=0 gid=0\n'
        rx.extend(self._frame(r.FRAME_DATA,3,output))
        rx.extend(self._frame(r.FRAME_EXIT,3,self.codec.EXIT.pack(0,0,0,len(output),1)))
        tx=bytearray(self._frame(r.FRAME_OPEN,0,r.P356_RUN_ID))
        tx.extend(self._frame(r.FRAME_AUTH,1,self._tag(r.AUTH_DOMAIN_OPEN,nonce)))
        for seq,cmd in [(3,r.DEFAULT_COMMANDS[0]),(4,r.DISPLAY_COMMAND)]:
            tx.extend(self._frame(r.FRAME_EXEC,seq,self._tag(r.AUTH_DOMAIN_EXEC,nonce,seq,cmd)+cmd))
        return bytes(rx),bytes(tx)

    def _qualification_proof(self):
        rx,tx=self._session(1)
        parsed=self.observer.parse_captured_session(self.codec,rx,tx,KEY)
        self.audits.append(parsed.session.audit);self.rx_streams.append(rx);self.tx_streams.append(tx)
        row=self.observer.validate_session_result(parsed,self.observer.DISPLAY_STEP)
        return self.observer.validate_qualification(dict(self.observer._fixed(),sessions=[row],expected_boot_sha256=hashlib.sha256(BOOT_ID).hexdigest()))

    def _lane(self):
        return dict(super()._lane(),observation_phase='before-static-display-dispatch',post_dispatch_observation=False)

    def _receipt_value(self):
        v=super()._receipt_value()
        v.pop('p356_readonly_research_shell_qualification')
        v[self.variant.proof_key]=self.proof
        v.update(session_count=1,command_count=2,pid1_framed_exec_proof=False,
            busybox_ash_command_proof=False,framed_session_closed=False,
            display_request_dispatched=True,display_response_observed=False,
            display_execution_proved=False,visible_panel_output='UNPROVED',
            proof_scope='authenticated-host-dispatch-only')
        path=self.run_dir/'p356-candidate-end.raw.json'
        raw=live.p318_topology.raw_snapshot(phase='candidate_end',capture_complete=True,endpoints=[])
        receipt=live.p318_topology.publish_raw(path,raw,phase='candidate_end')
        v['p356_closure_snapshot']=dict(path=str(path),**receipt,capture_complete=True,
            error_type=None,continuity_proved=False,role='post-dispatch-transport-diagnostic')
        return v


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.f=Fixture(Path(self.tmp.name)/'run');self.o=self.f.observer

    def test_exact_partial_prefix_reopens_without_display_response(self):
        with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)):
            value=live._p345_validate_receipt(self.f.prepared,self.f.run_dir/'candidate-observer.json',self.f.spec)
        self.assertTrue(value['valid_receipt'])
        self.assertFalse(value['framed_session_closed'])
        self.assertFalse(value['display_execution_proved'])
        self.assertEqual(value['proof']['completed_command_count'],1)

    def test_wire_truncation_tamper_and_extra_frames_rejected(self):
        rx,tx=self.f.rx_streams[0],self.f.tx_streams[0]
        for broken_rx,broken_tx in [(rx[:-1],tx),(rx,tx[:-1]),(rx,tx[:-1]+bytes([tx[-1]^1])),(rx+b'x',tx),(rx,tx+b'x')]:
            with self.subTest(rx=len(broken_rx),tx=len(broken_tx)):
                with self.assertRaises(ValueError):self.o.parse_captured_session(self.f.codec,broken_rx,broken_tx,KEY)

    def test_machine_proof_cannot_be_promoted_to_display_or_session_completion(self):
        for key,val in [('display_execution_proved',True),('visible_panel_output','PROVED'),('framed_session_closed',True),('total_command_count',3)]:
            bad=copy.deepcopy(self.f.proof);bad[key]=val
            with self.assertRaises(ValueError):self.o.validate_qualification(bad)
        bad=copy.deepcopy(self.f.value);bad['framed_session_closed']=True;self.f.publish(bad)
        with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)):
            with self.assertRaises(live.F1LiveError):live._p345_validate_receipt(self.f.prepared,self.f.run_dir/'candidate-observer.json',self.f.spec)

    def test_live_socket_stops_after_full_dispatch_without_peer_response(self):
        host,peer=socket.socketpair();self.addCleanup(host.close);self.addCleanup(peer.close)
        host.setblocking(False);received=[];errors=[];rx,tx=self.f.rx_streams[0],self.f.tx_streams[0]
        def device():
            try:
                peer.sendall(rx)
                buf=bytearray()
                while len(buf)<len(tx):
                    b=peer.recv(len(tx)-len(buf))
                    if not b:break
                    buf.extend(b)
                received.append(bytes(buf))
                # No sequence-4 DATA/EXIT is ever provided.
            except BaseException as e:errors.append(e)
        thread=threading.Thread(target=device);thread.start()
        capture=bytearray()
        writer=type('Writer',(),{'write_stdout':lambda self,b:capture.extend(b)})()
        result=self.o.qualify(self.f.codec,host.fileno(),KEY,None,set(),writer,deadline=time.monotonic()+2)
        thread.join(2);self.assertFalse(thread.is_alive());self.assertFalse(errors)
        self.assertEqual(received,[tx]);self.assertEqual(bytes(capture),rx)
        self.assertTrue(result.receipt['display_request_dispatched'])
        self.assertFalse(result.receipt['display_response_observed'])

    def test_partial_dispatch_send_failure_never_retries(self):
        rx=self.f.rx_streams[0];host,peer=socket.socketpair();self.addCleanup(host.close);self.addCleanup(peer.close)
        peer.sendall(rx);host.setblocking(False);original=self.f.codec._CODEC._send;calls=[]
        def send(fd,kind,seq,payload,deadline,audit):
            calls.append(seq)
            if seq==4:
                audit.tx.extend(self.f.codec.encode_frame(kind,seq,payload)[:7])
                raise OSError('injected partial write')
            return original(fd,kind,seq,payload,deadline,audit)
        writer=type('Writer',(),{'write_stdout':lambda self,b:None})()
        with mock.patch.object(self.f.codec._CODEC,'_send',side_effect=send):
            with self.assertRaises(self.o.QualificationError) as error:
                self.o.qualify(self.f.codec,host.fileno(),KEY,None,set(),writer,deadline=time.monotonic()+2)
        self.assertEqual(calls,[0,1,3,4]);self.assertFalse(error.exception.partial_receipt['proved'])
        self.assertTrue(error.exception.partial_receipt['display_replay_forbidden'])

    def test_invalid_parent_duration_is_rejected_before_display_write(self):
        output=b'uid=0 gid=0\n'
        old=self.f._frame(self.f.runtime.FRAME_EXIT,3,self.f.codec.EXIT.pack(0,0,0,len(output),1))
        new=self.f._frame(self.f.runtime.FRAME_EXIT,3,self.f.codec.EXIT.pack(0,0,0,len(output),60001))
        rx=self.f.rx_streams[0].replace(old,new)
        self.assertNotEqual(rx,self.f.rx_streams[0])
        host,peer=socket.socketpair();self.addCleanup(host.close);self.addCleanup(peer.close)
        peer.sendall(rx);host.setblocking(False);calls=[];original=self.f.codec._CODEC._send
        def send(fd,kind,seq,payload,deadline,audit):
            calls.append(seq);return original(fd,kind,seq,payload,deadline,audit)
        writer=type('Writer',(),{'write_stdout':lambda self,b:None})()
        with mock.patch.object(self.f.codec._CODEC,'_send',side_effect=send):
            with self.assertRaises(self.o.QualificationError):
                self.o.qualify(self.f.codec,host.fileno(),KEY,None,set(),writer,deadline=time.monotonic()+2)
        self.assertEqual(calls,[0,1,3])

    def test_post_dispatch_reporting_failure_preserves_audit(self):
        host,peer=socket.socketpair();self.addCleanup(host.close);self.addCleanup(peer.close)
        peer.sendall(self.f.rx_streams[0]);host.setblocking(False)
        writer=type('Writer',(),{'write_stdout':lambda self,b:None})()
        with mock.patch.object(self.o,'validate_session_result',side_effect=ValueError('report cut')):
            with self.assertRaises(self.o.QualificationError) as error:
                self.o.qualify(self.f.codec,host.fileno(),KEY,None,set(),writer,deadline=time.monotonic()+2)
        self.assertEqual(bytes(error.exception.failed_audit.tx),self.f.tx_streams[0])
        self.assertTrue(error.exception.partial_receipt['display_request_dispatched'])

    def test_dispatch_scope_survives_final_projection(self):
        variant=live._host_first_variant(self.f.prepared.bundle)
        value=variant.proof_state(self.f.value)
        self.assertTrue(value['display_request_dispatched'])
        self.assertFalse(value['display_execution_proved'])
        self.assertEqual(value['proof_scope'],'authenticated-host-dispatch-only')

    def test_host_close_error_does_not_lose_written_dispatch(self):
        from types import SimpleNamespace
        session=object.__new__(live._P353ObserverSession)
        session.base=SimpleNamespace(dev_root=Path('/fixture'),_raw_tty=lambda fd:None)
        session.namespace='p356';session.auth_runtime=self.f.runtime
        session.qualification_observer=self.o;session.auth_key=KEY
        session.qualification=None;session.qualification_error=None;session.owned_descriptor=None
        parsed=self.o.parse_captured_session(self.f.codec,self.f.rx_streams[0],self.f.tx_streams[0],KEY)
        result=self.o.QualificationResult(self.f.proof,(parsed,))
        with mock.patch.object(session,'_settle_guard_properties',return_value=None), \
             mock.patch.object(session,'_endpoint_exact',return_value=True), \
             mock.patch.object(session,'_qualify_on_descriptor',return_value=result), \
             mock.patch.object(live,'_open_header_initial_observer_module',return_value=self.f.codec), \
             mock.patch.object(live.os,'open',return_value=23), \
             mock.patch.object(live.os,'close',side_effect=OSError('close cut')), \
             mock.patch.object(live.fcntl,'ioctl'):
            classification=session._read_endpoint(SimpleNamespace(tty_name='tty'),time.monotonic()+2,object())
        self.assertEqual(classification,'accepted')
        self.assertEqual(session.descriptor_close_error,'OSError')
        self.assertEqual(session.proof,self.f.proof)
        self.assertEqual(bytes(session.exchange.audit.tx),self.f.tx_streams[0])

    def test_closure_snapshot_is_required_and_hash_bound(self):
        value=copy.deepcopy(self.f.value)
        value['p356_closure_snapshot']['sha256']='0'*64
        self.f.publish(value)
        with mock.patch.object(live,'_p328_read_auth_key',return_value=(KEY,KEY_SHA256)):
            with self.assertRaises(live.F1LiveError):
                live._p345_validate_receipt(self.f.prepared,self.f.run_dir/'candidate-observer.json',self.f.spec)

    def test_snapshot_failure_is_recorded_without_fake_continuity(self):
        session=object.__new__(live._P353ObserverSession)
        session.namespace='p356'
        session.run_dir=Path(self.tmp.name)/'closure';session.run_dir.mkdir()
        value={'display_request_dispatched':True}
        with mock.patch.object(live.p318_topology,'capture_candidate_raw',side_effect=OSError('snapshot unavailable')), \
             mock.patch.object(live._P345ObserverSession,'_publish_value'):
            session._publish_value(value,{},label='fixture')
        snapshot=value['p356_closure_snapshot']
        self.assertTrue(value['display_request_dispatched'])
        self.assertFalse(snapshot['capture_complete']);self.assertFalse(snapshot['continuity_proved'])
        self.assertEqual(snapshot['error_type'],'OSError')
        self.assertFalse(live.p318_topology.parse_raw_snapshot(Path(snapshot['path']).read_bytes(),phase='candidate_end')['capture_complete'])

    def test_real_preparation_entry_applies_settings_before_main(self):
        from types import SimpleNamespace
        root=Path(__file__).resolve().parents[1]
        sys.path.insert(0,str(root/'workspace/public/src/scripts/analysis'))
        import prepare_s22plus_fyg8_p356_process_v2 as preparation
        static_path=root/'workspace/private/outputs/s22plus_fyg8_p356/process-v2-candidate-static-20260907-01.json'
        static=json.loads(static_path.read_text())
        observed=[]
        def verify(root, path):
            manifest=json.loads(Path(path).read_text());observed.append(manifest)
            return SimpleNamespace(sha256='a'*64,receipt={'observation_contract':{'verification':{'verified':True,'run_id':self.o.RUN_ID_HEX}},'candidate_ap':manifest['candidate_ap']})
        with mock.patch.object(preparation.candidate_static,'build_result',return_value=static), \
             mock.patch.object(preparation.core,'verify_bundle',side_effect=verify), \
             mock.patch.object(sys,'argv',[preparation.__file__,'--audit-only']), \
             mock.patch.object(sys,'stdout',new_callable=io.StringIO) as output:
            with self.assertRaises(SystemExit) as exit_status:
                runpy.run_path(preparation.__file__,run_name='__main__')
        self.assertEqual(exit_status.exception.code,0)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0]['observation']['timeout_sec'],60)
        self.assertEqual(observed[0]['observation']['candidate_observer']['proof_command_count'],2)
        self.assertEqual(len(observed[0]['observation']['candidate_observer']['commands']),2)
        self.assertFalse(json.loads(output.getvalue())['published'])


if __name__=='__main__':unittest.main()
