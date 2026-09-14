"""Actual C command output, V3 framing, metadata parser and DETACH closure.

The target block device and census shell are a fixed synthetic output file in
this PTY test. The separate census tests execute ARM64 BusyBox decoding and
metadata-sized regular-file reads. Neither fixture claims live GPT recovery.
"""
from pathlib import Path
import sys
from unittest import mock
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import s22plus_native_observation_v3 as observation
import test_s22plus_native_observation_v3 as base
import test_s22plus_native_resident_v1 as producer
from test_s22plus_native_storage_census_v1 import fixture


class StorageObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.ObservationTests.setUpClass.__func__(cls)
        path=cls.folder/'native.c';source=path.read_text();marker='const char *command=text;'
        assert source.count(marker)==1
        source=source.replace(marker,marker+'\n if(!strncmp(command,"B=/bin/busybox;echo ",19))command="cat census.bin";')
        path.write_text(source)
        producer.compile_c(path,cls.binary,'-Wno-unused-function','-Wno-unused-const-variable','-Wno-misleading-indentation')

    running=base.ObservationTests.running

    def test_complete_binary_census_rederives_after_real_c_output_and_detach(self):
        with self.running() as ctx:
            (ctx.folder/'census.bin').write_bytes(fixture())
            directory=ctx.folder/'census'
            value=observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='storage-census')
            proof=value['proof']
            self.assertTrue(proof['native_health_proved']);self.assertTrue(proof['detach_ack_observed'])
            self.assertFalse(proof['hud_requested']);self.assertFalse(proof['control_acceptance_observed'])
            self.assertEqual(proof['storage_census']['status'],'PASS_METADATA_ONLY')
            self.assertEqual(proof['storage_census']['geometry']['capacity_bytes'],256_000_000_000)
            self.assertIsNone(ctx.fd)
            self.assertEqual(value,observation.rederive(directory,self.image,ending='detach',hud=False,
                first_boot=True,profile='storage-census'))
            with self.assertRaisesRegex(ValueError,'profile changed'):
                observation.rederive(directory,self.image,ending='detach',hud=False,first_boot=True)

    def test_complete_negative_dataset_keeps_health_and_does_not_change_mode(self):
        with self.running() as ctx:
            (ctx.folder/'census.bin').write_bytes(b'not a complete GPT snapshot')
            value=observation.observe(ctx.folder/'negative',self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='storage-census')
            self.assertTrue(value['proof']['native_health_proved'])
            self.assertEqual(value['proof']['storage_census']['status'],'NO_PROOF')
            self.assertTrue(value['proof']['detach_ack_observed'])

    def test_census_publication_cut_repairs_from_same_raw_without_another_read(self):
        with self.running() as ctx:
            (ctx.folder/'census.bin').write_bytes(fixture());directory=ctx.folder/'publication-cut'
            original=observation.publish
            def fail(path,value):
                if Path(path).name=='attempt.json':raise OSError('fixture publication cut')
                return original(path,value)
            with mock.patch.object(observation,'publish',side_effect=fail),self.assertRaises(observation.NativeClosePublicationError):
                observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                    guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='storage-census')
            self.assertIsNone(ctx.fd)
            tx=(directory/'tx.bin').read_bytes()
            value=observation.rederive(directory,self.image,ending='detach',hud=False,first_boot=True,profile='storage-census')
            self.assertEqual(value['proof']['storage_census']['status'],'PASS_METADATA_ONLY')
            self.assertEqual((directory/'tx.bin').read_bytes(),tx)

    def test_oversized_device_number_after_detach_keeps_proved_health(self):
        with self.running() as ctx:
            raw=fixture().replace(b'\n8:0\n',b'\n'+b'9'*5000+b':0\n',1)
            (ctx.folder/'census.bin').write_bytes(raw);directory=ctx.folder/'oversized-rdev'
            value=observation.observe(directory,self.image,base.HostFixture(ctx),ending='detach',hud=False,
                guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='storage-census')
            self.assertTrue(value['proof']['native_health_proved'])
            self.assertTrue(value['proof']['detach_ack_observed'])
            self.assertFalse(value['proof']['control_acceptance_observed'])
            self.assertEqual(value['proof']['storage_census']['status'],'NO_PROOF')
            self.assertIsNone(ctx.fd)
            self.assertEqual(value,observation.rederive(directory,self.image,ending='detach',hud=False,
                first_boot=True,profile='storage-census'))

    def test_storage_profile_cannot_request_hud_or_control(self):
        with self.running() as ctx:
            for ending,hud in (('download',False),('detach',True)):
                with self.assertRaises(ValueError):
                    observation.observe(ctx.folder/ending,self.image,base.HostFixture(ctx),ending=ending,hud=hud,
                        guard=lambda:None,before_terminal=lambda:None,first_boot=True,profile='storage-census')


if __name__=='__main__':unittest.main()
