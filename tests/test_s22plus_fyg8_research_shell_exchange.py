"""Real local framed exchange, cancellation race and raw receipts; no device."""
import hashlib
import hmac
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import device_action_f1_live_v2 as live
import device_action_raw_capture_v1 as raw
import s22plus_fyg8_research_shell_exchange as shell

KEY=b'k'*32
BOOT=b'b'*32


class ShellExchangeTests(unittest.TestCase):
    def run_stream(self,modes, bad_ack=False, replay=False, bad_nonce=False, initial=False):
        observer=live._open_header_initial_observer_module(live.p344_open_read_runtime,live.p344_open_read_observer,'shell-h0')
        runtime=observer.runtime;codec=observer._CODEC
        host,peer=socket.socketpair();host.setblocking(False);peer.settimeout(3)
        cancel=threading.Event();errors=[]
        commands=[f"v=$(printf 'hello {i}'); printf '%s\\n' \"$v\" | /bin/busybox head -c 20".encode() for i in range(len(modes))]
        nonces=[hashlib.sha256(f'nonce-{i}'.encode()).digest() for i in range(len(modes))]
        def receive():
            def exact(n):
                b=b''
                while len(b)<n:
                    chunk=peer.recv(n-len(b))
                    if not chunk:raise EOFError()
                    b+=chunk
                return b
            header=exact(codec.HEADER.size)
            return codec.decode_frame(header+exact(codec.HEADER.unpack(header)[3]))
        def send(kind,seq,payload):peer.sendall(codec.encode_frame(kind,seq,payload))
        def serve():
            try:
                for index,mode in enumerate(modes):
                    nonce=nonces[index]
                    opened=receive();self.assertEqual(opened.frame_type,runtime.FRAME_OPEN);self.assertEqual(opened.payload,runtime.P335_RUN_ID)
                    peer.sendall(runtime.DEVICE_BANNER)
                    for stage in (0,1,2):send(runtime.DIAGNOSTIC_FRAME_TYPE,0,observer.DIAGNOSTIC.pack(stage,0))
                    send(runtime.FRAME_CHALLENGE,0,nonce)
                    auth=receive();self.assertEqual(auth.payload,observer.compute_open_tag(KEY,runtime.P335_RUN_ID,nonce))
                    send(runtime.FRAME_READY,1,observer.compute_ready_tag(KEY,runtime.P335_RUN_ID,nonce))
                    send(runtime.P335_FRAME_BOOT_ID,2,BOOT+observer.compute_boot_id_tag(KEY,runtime.P335_RUN_ID,nonce,BOOT))
                    for seq in (3,4,5):
                        frame=receive();self.assertEqual((frame.frame_type,frame.sequence),(runtime.FRAME_EXEC,seq))
                        command=commands[index] if seq==4 else runtime.DEFAULT_COMMANDS[0 if seq==3 else 2]
                        self.assertEqual(frame.payload[32:],command)
                        tag=hmac.new(KEY,runtime.AUTH_DOMAIN_EXEC+runtime.P335_RUN_ID+nonce+struct.pack('<I',seq)+command,hashlib.sha256).digest()
                        self.assertEqual(frame.payload[:32],tag)
                        flags,code,signal=(0,0,0)
                        if seq==4:
                            output=b'abc'
                            if mode in ('cancelled','late'):
                                cancel.set()
                                if mode=='cancelled':
                                    request=receive();self.assertEqual((request.frame_type,request.sequence),(5,4));self.assertEqual(request.payload,shell.cancel_tag(KEY,runtime.P335_RUN_ID,nonce))
                                    flags,code,signal=8,-1,9
                            elif mode=='timeout':flags,code,signal=1,-1,9
                            elif mode=='truncated':flags=2
                            elif mode=='command-failed':code=7
                        else:output=b'uid=0(root) gid=0(root)\n' if seq==3 else b'P328-NONCE '+runtime.P335_RUN_ID.hex().encode()+b'\n'
                        if seq==5 and bad_nonce:output=runtime.P335_RUN_ID.hex().encode()+b'\n'
                        send(runtime.FRAME_DATA,seq,output)
                        send(runtime.FRAME_EXIT,seq,codec.EXIT.pack(flags,code,signal,len(output),1))
                        if seq==4 and mode in ('cancelled','late'):
                            if mode=='late':
                                request=receive();self.assertEqual(request.payload,shell.cancel_tag(KEY,runtime.P335_RUN_ID,nonce))
                            send(shell.FRAME_CANCEL_ACK,4,struct.pack('<I',2 if bad_ack else 0 if mode=='cancelled' else 1))
                    closed=receive();self.assertEqual((closed.frame_type,closed.sequence),(runtime.FRAME_CLOSE,6))
                    self.assertEqual(closed.payload,observer.compute_close_tag(KEY,runtime.P335_RUN_ID,nonce,6))
                    send(runtime.FRAME_DONE,6,observer.DONE.pack(3))
            except EOFError:
                if not (bad_ack or replay or bad_nonce):errors.append(AssertionError('unexpected EOF'))
            except BaseException as exc:errors.append(exc)
        thread=threading.Thread(target=serve);thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                seen=set();fd=host.fileno()
                if replay:seen.add(hashlib.sha256(nonces[0]).hexdigest())
                for i,mode in enumerate(modes):
                    writer=raw.RawCaptureWriter(Path(directory),f'rx-{i}',stdout_maximum=512*1024,stderr_maximum=4096)
                    if bad_ack or replay or bad_nonce:
                        message='ACK outcome' if bad_ack else 'nonce replay' if replay else 'nonce witness'
                        with self.assertRaisesRegex(codec.AuthObserverError,message) as caught:
                            shell.exchange(observer,fd,KEY,commands[i],hashlib.sha256(BOOT).hexdigest(),seen,writer,deadline=time.monotonic()+2,cancel_requested=cancel.is_set)
                        handle=writer.finalize(returncode=None,producer_error_type='AuthObserverError')
                        self.assertTrue(raw.read_stdout(handle,maximum=512*1024))
                        if bad_ack:self.assertTrue(caught.exception.cancel_sent)
                        if replay:
                            self.assertEqual(len(caught.exception.audit.tx),32)
                            self.assertFalse(caught.exception.audit.authenticated)
                        break
                    expected_boot=None if initial and i==0 else hashlib.sha256(BOOT).hexdigest()
                    result=shell.exchange(observer,fd,KEY,commands[i],expected_boot,seen,writer,deadline=time.monotonic()+2,cancel_requested=cancel.is_set)
                    cancel.clear()
                    self.assertEqual(result.outcome,'ok' if mode=='late' else mode)
                    self.assertEqual(result.cancel_ack,1 if mode=='late' else 0 if mode=='cancelled' else None)
                    self.assertTrue(result.session.audit.done_seen)
                    self.assertEqual(host.fileno(),fd)
                    seen.add(hashlib.sha256(result.session.audit.nonce).hexdigest())
                    handle=writer.finalize(returncode=0)
                    self.assertEqual(raw.read_stdout(handle,maximum=512*1024),bytes(result.session.audit.rx))
        finally:
            host.close();thread.join(4);peer.close()
        self.assertFalse(thread.is_alive());self.assertEqual(errors,[])

    def test_same_descriptor_normal_nonzero_timeout_truncated_then_next(self):
        self.run_stream(['ok','command-failed','timeout','truncated','ok'])

    def test_cancel_and_completion_race_then_next(self):
        self.run_stream(['cancelled','late','ok'])

    def test_first_authenticated_candidate_boot_then_bound_followup(self):
        self.run_stream(['ok','ok'],initial=True)

    def test_outer_window_never_extends_one_logical_session(self):
        observer=live._open_header_initial_observer_module(
            live.p344_open_read_runtime,live.p344_open_read_observer,'shell-deadline-h0')
        def stop_before_io(fd,kind,seq,payload,deadline,audit):
            self.assertEqual(deadline,130.0)
            raise RuntimeError('fixture stops before I/O')
        with mock.patch.object(shell.time,'monotonic',return_value=100.0), \
             mock.patch.object(observer._CODEC,'_send',side_effect=stop_before_io):
            with self.assertRaisesRegex(RuntimeError,'fixture stops'):
                shell.exchange(observer,-1,KEY,'true',None,set(),object(),deadline=400.0)

    def test_bad_cancel_ack_retains_raw_and_stops(self):
        self.run_stream(['cancelled'],bad_ack=True)

    def test_replayed_challenge_stops_before_auth_and_exec(self):
        self.run_stream(['ok'],replay=True)

    def test_nonce_witness_is_exact_not_a_substring(self):
        self.run_stream(['ok'],bad_nonce=True)

    def test_arbitrary_syntax_is_not_a_write_permission(self):
        self.assertEqual(shell.command_bytes("x=$(printf hi); printf '%s' \"$x\" | head -c 2"),b"x=$(printf hi); printf '%s' \"$x\" | head -c 2")
        self.assertEqual(shell.command_bytes('echo one\necho two'),b'echo one\necho two')
        # Filesystem isolation, not this text parser, must deny the write.
        self.assertEqual(shell.command_bytes('echo x > /file'),b'echo x > /file')
        for value in ('',b'x\x00y',b'a'*1024):
            with self.assertRaises(ValueError):shell.command_bytes(value)


if __name__=='__main__':unittest.main()
