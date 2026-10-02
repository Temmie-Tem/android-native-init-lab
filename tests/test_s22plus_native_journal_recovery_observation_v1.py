"""Actual C/PTY health, 300-second admission, one EXEC intent and strict replay."""
import struct
import unittest
from unittest import mock
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
from test_s22plus_native_journal_recovery_v1 import fixture,BINDING,profile
import s22plus_native_observation_v3 as observation
import s22plus_root_console_v1 as wire
import s22plus_native_baseline_protocol_v1 as protocol


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';source=path.read_text();marker='const char *command=text;'
        assert source.count(marker)==1
        prefix='exec /s22-journal-recovery '
        source=source.replace(marker,marker+f'\n char sp[4096]; if(!strncmp(command,"{prefix}",{len(prefix)}))'
            '{snprintf(sp,sizeof(sp),"cat %s/journal.bin; sleep 1",getenv("RC1_WORK"));command=sp;}')
        path.write_text(source)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_real_stream_complete_and_strict_replay(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'journal.bin').write_bytes(fixture());intents=[]
            result=observation.observe(ctx.folder/'complete',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=intents.append,first_boot=True,profile=profile.SELECTION)
            self.assertEqual(len(intents),1)
            self.assertTrue(result['proof']['journal_recovery']['recovery_proved'])
            self.assertEqual(result,observation.rederive(ctx.folder/'complete',self.image,ending='detach',hud=False,
                first_boot=True,profile=profile.SELECTION))



if __name__=='__main__':unittest.main()
