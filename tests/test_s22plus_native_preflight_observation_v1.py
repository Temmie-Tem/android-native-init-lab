"""Actual C/PTY fixed result reader, health, DETACH and raw rederivation."""
import unittest
from unittest import mock
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
from test_s22plus_native_preflight_v1 import fixture,profile
import s22plus_native_observation_v3 as observation


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';source=path.read_text();marker='const char *command=text;'
        assert source.count(marker)==1
        prefix='exec /s22-prehandoff-read '
        source=source.replace(marker,marker+f'\n char pf[4096]; if(!strncmp(command,"{prefix}",{len(prefix)}))'
            '{snprintf(pf,sizeof(pf),"cat %s/preflight.bin",getenv("RC1_WORK"));command=pf;}')
        path.write_text(source)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_actual_bounded_binary_output_detach_and_read_only_replay(self):
        with mock.patch.object(profile,'image_binding',return_value={}),self.running() as ctx:
            (ctx.folder/'preflight.bin').write_bytes(fixture(run=self.image['run_id_hex']))
            directory=ctx.folder/'preflight'
            value=observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile=profile.SELECTION)
            self.assertEqual(value['proof']['preflight']['status'],'PASS_PREFLIGHT_OBSERVED',value['proof']['preflight'])
            self.assertTrue(value['proof']['native_health_proved']);self.assertTrue(value['proof']['detach_ack_observed'])
            self.assertIsNone(ctx.fd)
            self.assertEqual(value,observation.rederive(directory,self.image,ending='detach',hud=False,
                first_boot=True,profile=profile.SELECTION))

    def test_truncated_record_is_no_proof_despite_healthy_native_and_zero_exit(self):
        with mock.patch.object(profile,'image_binding',return_value={}),self.running() as ctx:
            (ctx.folder/'preflight.bin').write_bytes(fixture(run=self.image['run_id_hex'])[:-1])
            value=observation.observe(ctx.folder/'truncated',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile=profile.SELECTION)
            self.assertTrue(value['proof']['native_health_proved'])
            self.assertEqual(value['proof']['preflight']['status'],'NO_PROOF')
            self.assertEqual(value['proof']['preflight']['stdout']['size'],211)
            self.assertEqual(value['proof']['preflight']['stderr']['size'],0)


if __name__=='__main__':unittest.main()
