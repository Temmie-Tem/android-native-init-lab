"""Real C/PTY streaming and authentication survive a host read interruption."""
import struct
import unittest
from unittest import mock
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
from test_s22plus_native_staged_preflight_v1 import fixture,BINDING,profile
import s22plus_native_observation_v3 as observation
import s22plus_native_staged_preflight_evidence_v1 as evidence
import s22plus_root_console_v1 as wire
import s22plus_native_baseline_protocol_v1 as protocol


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';source=path.read_text();marker='const char *command=text;'
        assert source.count(marker)==1
        prefix='exec /s22-staged-preflight '
        source=source.replace(marker,marker+f'\n char sp[4096]; if(!strncmp(command,"{prefix}",{len(prefix)}))'
            '{snprintf(sp,sizeof(sp),"cat %s/staged.bin; sleep 1",getenv("RC1_WORK"));command=sp;}')
        path.write_text(source)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_real_stream_complete_and_strict_replay(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'staged.bin').write_bytes(fixture());intents=[]
            result=observation.observe(ctx.folder/'complete',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=intents.append,first_boot=True,profile=profile.SELECTION)
            self.assertEqual(len(intents),1)
            self.assertTrue(result['proof']['staged_preflight']['preparation_proved'])
            self.assertEqual(result,observation.rederive(ctx.folder/'complete',self.image,ending='detach',hud=False,
                first_boot=True,profile=profile.SELECTION))

    def test_fsynced_prefix_survives_read_failure_and_bad_raw_tail(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            body=fixture();prefix=body[:body.index(b'UP1_OUTPUT')]
            (ctx.folder/'staged.bin').write_bytes(prefix);intents=[];terminal=mock.Mock()
            original=protocol.Session.poll
            def interrupted(session):
                frames=original(session)
                if any((kind,seq)==(wire.OUTPUT,5) for kind,seq,_ in frames):
                    raise OSError('fixture read interruption after raw fsync')
                return frames
            folder=ctx.folder/'cut'
            with mock.patch.object(protocol.Session,'poll',interrupted),self.assertRaises(OSError):
                observation.observe(folder,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                    guard=lambda:None,before_terminal=terminal,before_extra=intents.append,first_boot=True,profile=profile.SELECTION)
            terminal.assert_not_called();self.assertEqual(len(intents),1)
            rx=(folder/'rx.bin').read_bytes();tx=(folder/'tx.bin').read_bytes()
            result=evidence.from_bytes(self.image,rx,tx,intents[0])
            self.assertEqual(result['status'],'DIAGNOSTIC_ONLY');self.assertFalse(result['cleanup_proved'])
            self.assertFalse(result['session_completion_proved']);self.assertGreater(len(result['progress']['stages']),0)
            for tail in (b'S3',b'BAD!'+bytes(12),struct.pack('<4sBBHII',b'S328',1,wire.OUTPUT,40,5,0)+bytes(40)):
                damaged=evidence.from_bytes(self.image,rx+tail,tx,intents[0])
                self.assertEqual(damaged['progress'],result['progress'])
                self.assertIn('rx',damaged['framing']['tails'])
            wrong=dict(intents[0],nonce_sha256='0'*64)
            with self.assertRaises(ValueError):evidence.from_bytes(self.image,rx,tx,wrong)
            bound=observation.identity(self.image)
            io=observation.io_class(profile.SELECTION,self.image)(observation.Codec(bound.namespace),
                observation.key_bytes(self.image),bound,rx=rx,tx=tx)
            io.handshake();offset=io.rpos
            while offset<len(rx):
                _,_,kind,size,seq,_=struct.unpack_from('<4sBBHII',rx,offset)
                if (kind,seq)==(wire.STATUS_REPLY,4):break
                offset+=16+size
            self.assertLess(offset,len(rx))
            for cut in (offset,offset+17):
                with self.assertRaisesRegex(ValueError,'lacks complete fixed health'):
                    evidence.from_bytes(self.image,rx[:cut],tx,intents[0])
            with self.assertRaises(ValueError):
                protocol.replay_one(observation.Codec(self.image['namespace']),observation.identity(self.image),
                    observation.key_bytes(self.image),rx,tx,io_class=observation.io_class(profile.SELECTION,self.image))


if __name__=='__main__':unittest.main()
