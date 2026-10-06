"""Actual C/PTY transport: one control intent, bounded output and raw rederive."""
import unittest
from unittest import mock
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
import s22plus_native_observation_v3 as observation
from test_s22plus_native_evidence_v1 import BINDING,fixture,profile


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        cls.image['root_evidence']=BINDING
        path=cls.folder/'native.c';source=path.read_text();marker='const char *command=text;'
        assert source.count(marker)==1
        prefix='exec /s22-root-evidence evidence '
        source=source.replace(marker,marker+f'\n if(!strncmp(command,"{prefix}",{len(prefix)}))command="cat evidence.bin";')
        path.write_text(source)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_complete_capture_intent_detach_and_raw_rederive(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'evidence.bin').write_bytes(fixture(dirty=True));intents=[]
            result=observation.observe(ctx.folder/'complete',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=intents.append,first_boot=True,profile=profile.SELECTION)
            self.assertEqual(len(intents),1);self.assertEqual(intents[0]['sequence'],5)
            self.assertEqual(result['proof']['root_evidence']['status'],'PASS_ROOT_EVIDENCE_OBSERVED')
            self.assertFalse(result['proof']['root_evidence']['source_view_clean'])
            self.assertTrue(result['proof']['detach_ack_observed']);self.assertIsNone(ctx.fd)
            self.assertEqual(result,observation.rederive(ctx.folder/'complete',self.image,ending='detach',hud=False,
                first_boot=True,profile=profile.SELECTION))

    def test_truncated_capture_cannot_become_proof_after_zero_exit(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            (ctx.folder/'evidence.bin').write_bytes(fixture().split(b'RI1_FINAL')[0])
            result=observation.observe(ctx.folder/'short',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,before_extra=lambda detail:None,first_boot=True,profile=profile.SELECTION)
            self.assertTrue(result['proof']['detach_ack_observed'])
            self.assertEqual(result['proof']['root_evidence']['status'],'NO_PROOF')

    def test_missing_control_intent_stops_before_open(self):
        with mock.patch.object(profile,'image_binding',return_value=BINDING),self.running() as ctx:
            host=base.HostFixture(ctx)
            with mock.patch.object(host,'open_native') as opening:
                with self.assertRaisesRegex(ValueError,'durable owner callback'):
                    observation.observe(ctx.folder/'missing',self.image,host,ending='detach',hud=False,
                        guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile=profile.SELECTION)
                opening.assert_not_called()
