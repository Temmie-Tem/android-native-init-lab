from dataclasses import replace
from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest import mock
from s22plus_native_departure_h0_support import Fixture, Clock, departure, return_host


class NativeDepartureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.fx=Fixture(self.root);self.run=self.root/'run'
        self.intent,self.ir=self.fx.intent(self.run);self.clock=Clock(self.intent)
    def observe(self):
        return departure.observe_departure(self.run,self.intent,self.ir,
            monotonic_ns=self.clock.monotonic_ns,sleep=self.clock.sleep)
    def test_exact_absence_after_stable_polls_and_reopen(self):
        calls=[]
        def snapshots(*args):
            calls.append(1)
            if len(calls)<3:return self.fx.snapshot
            return self.fx.absent()
        with mock.patch.object(departure,'_snapshot',side_effect=snapshots):
            self.assertTrue(self.observe())
        value,receipt=departure.read_observation(self.run,self.intent,self.ir)
        self.assertEqual(value['status'],'absent');self.assertFalse(value['download_proved'])
        before={p.name:p.read_bytes() for p in self.run.glob('*.json')}
        with mock.patch.object(departure,'_snapshot',side_effect=AssertionError('sealed absence must not resample')):
            self.assertTrue(self.observe())
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.run.glob('*.json')})
        self.assertEqual(len(calls),3)
    def test_same_deadline_timeout_and_late_absence(self):
        self.clock.now=self.intent['created_monotonic_ns']+30_000_000_000-1
        def late(*args):
            self.clock.now+=2
            return self.fx.absent()
        with mock.patch.object(departure,'_snapshot',side_effect=late):self.assertFalse(self.observe())
        value,_=departure.read_observation(self.run,self.intent,self.ir)
        self.assertEqual(value['status'],'timeout')
    def test_expired_budget_does_not_probe(self):
        self.clock.now=self.intent['created_monotonic_ns']+30_000_000_000
        with mock.patch.object(departure,'_snapshot',side_effect=AssertionError('expired probe')):
            self.assertFalse(self.observe())
    def test_replacement_nonenoent_and_foreign_departure_fail_closed(self):
        cases=[replace(self.fx.snapshot,birth_time_ns=98765),PermissionError(13,'fixture'),
            departure.usbfs.UsbfsIdentityError('fixture'),
            departure.usbfs.UsbfsEndpointDeparture('/dev/bus/usb/003/078')]
        for i,case in enumerate(cases):
            with self.subTest(case=type(case).__name__):
                run=self.root/('error'+str(i));intent,ir=self.fx.intent(run);clock=Clock(intent)
                def snapshot(*args):
                    if isinstance(case,Exception):raise case
                    return case
                with mock.patch.object(departure,'_snapshot',side_effect=snapshot):
                    with self.assertRaises(departure.DepartureError):
                        departure.observe_departure(run,intent,ir,monotonic_ns=clock.monotonic_ns,sleep=clock.sleep)
                value,_=departure.read_observation(run,intent,ir);self.assertEqual(value['status'],'error')
                with mock.patch.object(departure,'_snapshot',side_effect=AssertionError('no retry')):
                    with self.assertRaises(departure.DepartureError):departure.observe_departure(run,intent,ir)
    def test_stale_intent_nonce_source_and_host_boot_reject(self):
        for field in ('binding','request','endpoint_identity_sha256','host_boot_sha256'):
            intent=copy.deepcopy(self.intent)
            if field=='binding':intent[field]['binding_sha256']='b'*64
            elif field=='request':intent[field]['nonce_sha256']='3'*64
            else:intent[field]='f'*64
            with self.subTest(field=field),self.assertRaises(departure.DepartureError):
                departure.read_binding(self.run,intent)
        with mock.patch.object(departure,'_host_boot',return_value='f'*64):
            with self.assertRaises(departure.DepartureError):self.observe()
    def test_changed_mapping_before_control_is_rejected_with_raw_preserved(self):
        run=self.root/'mapping';run.mkdir()
        def snapshot(*args):
            (self.fx.usb_path/'devnum').write_text('78\n')
            return self.fx.snapshot
        with mock.patch.object(departure,'_snapshot',side_effect=snapshot):
            with self.assertRaises(departure.DepartureError):departure.capture_binding(run,
                endpoint=self.fx.endpoint,binding=self.intent['binding'],request=self.intent['request'])
        self.assertTrue((run/departure.RAW_BINDING_NAME).exists())
        self.assertFalse((run/departure.BINDING_NAME).exists())
        self.assertFalse((run/return_host.INTENT_NAME).exists())
    def test_raw_publication_cut_does_not_reobserve(self):
        original=departure._publish
        def cut(path,value):
            if path.name==departure.OBSERVATION_NAME:raise OSError('publication cut')
            return original(path,value)
        with mock.patch.object(departure,'_snapshot',side_effect=self.fx.absent),mock.patch.object(departure,'_publish',side_effect=cut):
            with self.assertRaises(OSError):self.observe()
        self.assertTrue((self.run/departure.RAW_OBSERVATION_NAME).exists())
        with mock.patch.object(departure,'_snapshot',side_effect=AssertionError('no retry')):
            with self.assertRaises(departure.DepartureError):self.observe()
    def test_malformed_coordinate_is_sealed_before_parser_rejects(self):
        run=self.root/'bad-coordinate';run.mkdir()
        (self.fx.usb_path/'busnum').write_bytes(b'not-a-coordinate\n')
        with self.assertRaises(departure.DepartureError):
            departure.capture_binding(run,endpoint=self.fx.endpoint,
                binding=self.intent['binding'],request=self.intent['request'])
        path=run/departure.CAPTURE_NAME/'before-busnum.capture.json'
        handle=departure.usbfs.raw_capture.load_handle(path)
        self.assertEqual(departure.usbfs.raw_capture.read_stdout(handle,maximum=17),b'not-a-coordinate\n')
        self.assertFalse((run/departure.BINDING_NAME).exists())

    def test_malformed_retained_mapping_raises_normalized_local_error(self):
        raw,_=departure._read(self.run/departure.RAW_BINDING_NAME)
        cases=[('sysfs_path',None),('sysfs_path',42),('busnum',True),('devnum','77')]
        for field,value in cases:
            bad=copy.deepcopy(raw);bad['before'][field]=value;bad['after'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(departure.DepartureError):
                departure._validate_raw_binding(bad,'e'*64,self.run)
        for value in (None,42,[]):
            with self.subTest(endpoint=value),self.assertRaises(departure.DepartureError):
                departure._validate_raw_binding(raw,value,self.run)

    def test_arrival_window_requires_joined_departure_witness(self):
        value=dict(schema='s22plus_fyg8_p366_return_window_v1',binding=self.intent['binding'],
            control_intent=self.ir,outcome='exact-download-within-control-window',
            observed_within_software_deadline=True,closed_monotonic_ns=self.clock.now,
            host_boot_sha256=self.intent['host_boot_sha256'],physical_prompt_required=False,
            physical_intervention='UNOBSERVED',software_causal_attribution='UNPROVED',
            rollback_topology_record={'path':'/fixture','size':1,'sha256':'a'*64})
        with self.assertRaises(return_host.ReturnControlError):return_host.validate_window(value,
            binding=self.intent['binding'],intent=self.intent,intent_receipt=self.ir)
        with mock.patch.object(departure,'_snapshot',side_effect=self.fx.absent):self.assertTrue(self.observe())
        return_host.validate_window(value,binding=self.intent['binding'],intent=self.intent,intent_receipt=self.ir)

if __name__=='__main__':unittest.main()
