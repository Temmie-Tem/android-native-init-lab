"""Actual C/PTY transport for the inspector profile; ARM64 mounts are separate."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_observation_v3 as observation
import s22plus_native_root_inspect_profile_v1 as profile
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
from test_s22plus_native_root_inspect_v1 import BINDING, fixture


class RootInspectionObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';source=path.read_text();marker='const char *command=text;'
        assert source.count(marker)==1
        source=source.replace(marker,marker+'\n if(!strncmp(command,"exec /s22-root-inspect inspect ",30))command="cat inspection.bin";')
        path.write_text(source)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_real_c_output_fixed_control_intent_detach_and_raw_rederivation(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'inspection.bin').write_bytes(fixture())
            intents=[];directory=ctx.folder/'inspection'
            value=observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=intents.append,first_boot=True,
                profile=profile.SELECTION)
            proof=value['proof']
            self.assertTrue(proof['native_health_proved']);self.assertTrue(proof['detach_ack_observed'])
            self.assertFalse(proof['control_acceptance_observed']);self.assertIsNone(ctx.fd)
            self.assertEqual(proof['root_inspection']['status'],'PASS_INSPECTION_COMPLETED')
            self.assertEqual(len(intents),1);self.assertEqual(intents[0]['sequence'],5)
            self.assertEqual(intents[0]['nonce_sha256'],proof['nonce_sha256'])
            self.assertEqual(value,observation.rederive(directory,self.image,ending='detach',hud=False,
                first_boot=True,profile=profile.SELECTION))
            with self.assertRaisesRegex(ValueError,'profile changed'):
                observation.rederive(directory,self.image,ending='detach',hud=False,first_boot=True)

    def test_truncated_science_stays_unproved_despite_completed_zero_exit_and_detach(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'inspection.bin').write_bytes(fixture().split(b'RI1_UNMOUNT')[0])
            value=observation.observe(ctx.folder/'negative',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=lambda detail:None,first_boot=True,
                profile=profile.SELECTION)
            self.assertTrue(value['proof']['native_health_proved']);self.assertTrue(value['proof']['detach_ack_observed'])
            self.assertEqual(value['proof']['root_inspection']['status'],'NO_PROOF')

    def test_partition_control_requires_owner_callback_before_open(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            host=base.HostFixture(ctx);before=ctx.fd
            with mock.patch.object(host,'open_native') as opening:
                with self.assertRaisesRegex(ValueError,'durable owner callback'):
                    observation.observe(ctx.folder/'missing-intent',self.image,host,ending='detach',hud=False,
                        guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile=profile.SELECTION)
                opening.assert_not_called()
            self.assertEqual(ctx.fd,before)


if __name__=='__main__':unittest.main()
