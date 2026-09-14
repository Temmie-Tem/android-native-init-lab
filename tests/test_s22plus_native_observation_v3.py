"""Real resident C and fixed V3 raw acquisition; USB geometry is a fixture."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import sys
import termios
import time
import tty
from unittest import mock
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_observation_v3 as observation
import s22plus_native_records_v3 as records
import test_s22plus_native_resident_v1 as producer


class HostFixture:
    config={'topology':'3-7.9'}
    def __init__(self,ctx): self.ctx=ctx

    @contextmanager
    def open_native(self,run_id,*,before_open):
        before_open()
        if self.ctx.fd is None:
            self.ctx.fd=os.open(self.ctx.name,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_CLOEXEC)
        fd=self.ctx.fd; tty.setraw(fd); fcntl.ioctl(fd,termios.TIOCEXCL)
        acquisition=dict(endpoint={'fixture':True},close=None)
        try: yield fd,acquisition
        finally:
            fcntl.ioctl(fd,termios.TIOCNXCL); os.close(fd); self.ctx.fd=None
            acquisition['close']=dict(descriptor_closed=True,exclusive_release_errno=None,boottime_ns=records.clock())


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        producer.Resident.setUpClass.__func__(cls)
        key=cls.folder/'auth-key'; key.write_bytes(b'k'*32)
        cls.image=dict(namespace=producer.IDENTITY.namespace,run_id_hex=producer.IDENTITY.run_id_hex,key=records.pin(key))

    running=producer.Resident.running

    def test_real_raw_capture_reentry_and_no_optional_hud(self):
        with self.running() as ctx:
            host=HostFixture(ctx); first_dir=ctx.folder/'first'
            first=observation.observe(first_dir,self.image,host,ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True)
            self.assertTrue(first['proof']['native_health_proved']); self.assertFalse(first['proof']['hud_requested'])
            self.assertEqual(first,observation.rederive(first_dir,self.image,ending='detach',hud=False,first_boot=True))
            before=dict(fixture=True)
            with mock.patch.object(observation.target_io,'usb_snapshot',return_value=before),\
                    mock.patch.object(observation.target_io,'wait_departure',return_value=dict(before=before,departed=True)):
                terminal=[]
                second=observation.observe(ctx.folder/'second',self.image,host,ending='download',hud=False,
                    guard=lambda:None,before_terminal=terminal.append,previous=first['proof'],
                    seen_nonces=(first['proof']['nonce_sha256'],))
            self.assertEqual(second['proof']['baseline_info']['authentication_ordinal'],2)
            self.assertEqual(len(terminal),1)
            self.assertEqual(first['proof']['kernel_boot_identity_sha256'],second['proof']['kernel_boot_identity_sha256'])
            self.assertNotEqual(first['proof']['nonce_sha256'],second['proof']['nonce_sha256'])

    def test_stale_previous_tail_stops_before_control_and_retains_raw(self):
        with self.running() as ctx:
            host=HostFixture(ctx)
            first=observation.observe(ctx.folder/'first',self.image,host,ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True)
            wrong=dict(first['proof'],kernel_boot_identity_sha256='0'*64)
            dispatch=mock.Mock()
            with self.assertRaises(ValueError):
                observation.observe(ctx.folder/'stale',self.image,host,ending='download',hud=False,
                    guard=lambda:None,before_terminal=dispatch,previous=wrong)
            dispatch.assert_not_called()
            attempt=records.read(ctx.folder/'stale/attempt.json')
            self.assertIsNotNone(attempt['error_type'])
            self.assertGreater((ctx.folder/'stale/rx.bin').stat().st_size,0)
            self.assertTrue(attempt['acquisition']['close']['descriptor_closed'])

    def test_malformed_optional_hud_has_explicit_unproved_result(self):
        value=observation.IO.decode_hud(b'broken optional collector output',producer.IDENTITY.run_id_hex)
        self.assertEqual(value['status'],'NO_PROOF_OPTIONAL_HUD')
        self.assertIn('sha256',value)

    def test_host_suspend_clock_expires_real_open_without_auth_or_control_retry(self):
        with self.running() as ctx:
            current=[records.clock()]; original=observation.IO.send; terminal=mock.Mock()
            def send(io,kind,sequence,payload):
                result=original(io,kind,sequence,payload)
                if kind==1: current[0]+=120_000_000_000
                return result
            with mock.patch.object(observation,'clock',side_effect=lambda:current[0]), \
                    mock.patch.object(observation.IO,'send',send),self.assertRaises(TimeoutError):
                observation.observe(ctx.folder/'suspended',self.image,HostFixture(ctx),ending='detach',hud=False,
                    guard=lambda:None,before_terminal=terminal,first_boot=True)
            terminal.assert_not_called()
            attempt=records.read(ctx.folder/'suspended/attempt.json')
            handle=observation.raw.load_handle(records.verify(attempt['raw']))
            self.assertTrue(handle.timed_out)
            self.assertEqual(len(observation.raw.read_stderr(handle,maximum=65536)),32)

    def test_completed_detach_publication_fault_is_identified_without_another_request(self):
        with self.running() as ctx:
            host=HostFixture(ctx); original=observation.publish
            def unavailable(path,value):
                if Path(path).name=='attempt.json': raise OSError('host disk publication failure')
                return original(path,value)
            with mock.patch.object(observation,'publish',side_effect=unavailable),\
                    self.assertRaises(observation.NativeClosePublicationError) as stopped:
                observation.observe(ctx.folder/'closed',self.image,host,ending='detach',hud=False,
                    guard=lambda:None,before_terminal=lambda:None,first_boot=True)
            self.assertTrue(stopped.exception.protocol_completed)
            self.assertIsNone(ctx.fd)
            capture=observation.raw.load_handle(ctx.folder/'closed/session.capture.json')
            self.assertEqual(capture.returncode,0)


if __name__=='__main__': unittest.main()
