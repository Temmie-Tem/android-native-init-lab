"""Extracted wire algorithms against retained codec and real resident C/PTY."""
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_wire_v3 as wire
import s22plus_native_baseline_protocol_v1 as baseline
import s22plus_native_resident_protocol_v1 as resident
import test_s22plus_native_resident_v1 as producer


class CodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        producer.Resident.setUpClass.__func__(cls)
        cls.old_codec = cls.codec
        cls.codec = wire.Codec(producer.IDENTITY.namespace)

    running = producer.Resident.running
    reopen = producer.Resident.reopen

    def test_frame_and_authentication_equivalence(self):
        old = self.old_codec
        key, run, nonce = b'k'*32, bytes.fromhex(producer.IDENTITY.run_id_hex), b'n'*32
        for kind, sequence, payload in ((1,0,run),(4,1,b't'*32),(135,2,b'b'*64),(139,256,b'p'*40)):
            encoded = wire.encode_frame(kind, sequence, payload)
            self.assertEqual(encoded, old._CODEC.encode_frame(kind, sequence, payload))
            decoded = wire.decode_frame(encoded)
            previous = old._CODEC.decode_frame(encoded)
            self.assertEqual((decoded.frame_type,decoded.sequence,decoded.payload),
                             (previous.frame_type,previous.sequence,previous.payload))
            for bad in (encoded[:-1], encoded+b'x', encoded[:12]+bytes([encoded[12]^1])+encoded[13:]):
                with self.assertRaises(ValueError): wire.decode_frame(bad)
        self.assertEqual(wire.compute_open_tag(key,run,nonce),old.compute_open_tag(key,run,nonce))
        self.assertEqual(wire.compute_ready_tag(key,run,nonce),old.compute_ready_tag(key,run,nonce))
        boot = b'b'*32
        payload = boot+old.compute_boot_id_tag(key,run,nonce,boot)
        self.assertEqual(self.codec.decode_boot_id_frame(wire.Frame(135,2,payload),key,run,nonce),boot)
        for codec, other_nonce in ((wire.Codec('p999'),nonce),(self.codec,b'z'*32)):
            with self.assertRaises(ValueError): codec.decode_boot_id_frame(wire.Frame(135,2,payload),key,run,other_nonce)
        for stage,code in ((0,0),(1,0),(2,0),(2,64),(2,-4095)):
            encoded = wire.encode_frame(134,0,struct.pack('<Ii',stage,code))
            new = wire.parse_diagnostic_frame(wire.decode_frame(encoded),stage)
            previous = old._P333.parse_diagnostic_frame(old._CODEC.decode_frame(encoded),stage)
            self.assertEqual((new.stage,new.code),(previous.stage,previous.code))

    def test_real_producer_fixed_health_reentry_and_raw_replay(self):
        with self.running() as ctx:
            previous = None
            for ending in ('detach','download'):
                io = resident.IO(self.codec,b'k'*32,producer.IDENTITY,fd=ctx.fd,
                    deadline=time.monotonic()+10, writer=SimpleNamespace(write_stdout=lambda data:None),
                    before_write=lambda:None)
                proof = baseline.qualify_one(io,ending=ending,evidence=ctx.folder/str(time.monotonic_ns()),
                    before_terminal=lambda request:None,hud=False)
                rx,tx = bytes(io.audit.rx),bytes(io.audit.tx)
                old_proof,rend,tend = baseline.replay_one(self.old_codec,producer.IDENTITY,b'k'*32,rx,tx,io_class=resident.IO)
                self.assertEqual(proof,old_proof)
                self.assertEqual((rend,tend),(len(rx),len(tx)))
                self.assertTrue(proof['native_health_proved'])
                self.assertFalse(proof['hud_requested'])
                if previous: baseline.fresh_same_boot(previous,proof)
                previous=proof
                if ending=='detach': self.reopen(ctx)

    def test_clean_import_does_not_load_legacy_owners(self):
        script = 'import sys; import s22plus_native_wire_v3; assert not any(n in sys.modules for n in '+repr([
            'device_action_f1_live_v2','device_action_f1_v2','s22plus_native_baseline_owner_v1',
            's22plus_fyg8_p335_retained_listener_acm_observer'])+')'
        subprocess.run([sys.executable,'-c',script],check=True,timeout=5,
            env=dict(os.environ,PYTHONPATH=str(Path(wire.__file__).parent)))


if __name__ == '__main__': unittest.main()
