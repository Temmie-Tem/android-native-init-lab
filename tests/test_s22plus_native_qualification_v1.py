"""Immutable qualification reuse and final-boundary Download clocks; no devices."""
from pathlib import Path
import os
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import device_action_read_dependencies_v1 as dependencies
import device_action_raw_capture_v1 as raw
import s22plus_boot_only_f1_transport as transport
import s22plus_native_records_v3 as records
import s22plus_native_qualification_v1 as qualification
import s22plus_native_adapter_v3 as adapter
import s22plus_native_session_v3 as owner
import s22plus_native_target_io_v3 as target
import s22plus_debian_handoff_profile_v1 as handoff


class QualificationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        patch=mock.patch.object(handoff,'ROOT',self.root);patch.start();self.addCleanup(patch.stop)
        self.template=self.root/'template';self.template.write_bytes(b'fixed template')
        self.archive=self.root/'archive';self.archive.write_bytes(b'archive data')
        self.archive_pin=records.pin(self.archive)
        self.stream=raw.publish_captured_bytes(self.root,'fixture',stdout=b'proof',stderr=b'')
        self.nested=self.root/'nested.json'
        records.publish(self.nested,dict(value='checked'))
        self.image=dict(runtime_sources={'template':{k:v for k,v in records.pin(self.template).items() if k!='path'}})
        self.calls=0

    def validate(self,image):
        self.calls+=1
        nested=records.read(self.nested)
        handle=raw.load_handle(self.stream.receipt_path)
        stdout=raw.read_stdout(handle,maximum=1024);stderr=raw.read_stderr(handle,maximum=1024)
        with transport.pin_regular_file(self.archive,label='fixture archive',
                expected_size=self.archive_pin['size'],expected_sha256=self.archive_pin['sha256']): pass
        return dict(nested=nested,stdout=stdout.hex(),stderr=stderr.hex())

    def test_reuses_all_verified_inputs_and_returns_independent_value(self):
        ticket=qualification.Qualification();value=ticket.binding(self.image,self.validate)
        value['nested']['value']='caller mutation'
        self.assertEqual(ticket.binding(self.image,self.validate)['nested']['value'],'checked')
        self.assertEqual(self.calls,1)
        self.assertTrue({self.template,self.archive,self.nested,self.stream.receipt_path}<=set(ticket.dependencies.files))
        self.assertTrue(any(path.stat().st_size==0 for path in ticket.dependencies.files))

    def test_each_nested_raw_archive_and_source_change_invalidates_without_revalidation(self):
        ticket=qualification.Qualification();ticket.binding(self.image,self.validate)
        paths=list(ticket.dependencies.files)
        for path in paths:
            with self.subTest(path=path.name):
                fresh=qualification.Qualification();fresh.binding(self.image,self.validate)
                original=path.read_bytes();path.chmod(0o600);path.write_bytes(original+b'X')
                count=self.calls
                with self.assertRaises(ValueError):fresh.binding(self.image,self.validate)
                path.write_bytes(original);path.chmod(0o400)
                with self.assertRaisesRegex(ValueError,'ticket is invalid'):fresh.binding(self.image,self.validate)
                self.assertEqual(self.calls,count)

    def test_same_size_restored_mtime_replace_link_and_mode_changes_reject(self):
        for change in ('bytes','replace','link','mode','symlink'):
            with self.subTest(change=change):
                path=self.root/('change-'+change);path.write_bytes(b'aaaa')
                with dependencies.ReadSet() as observed:records.read_bytes(path)
                before=path.stat()
                if change=='bytes':path.write_bytes(b'bbbb');os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
                elif change=='replace':path.unlink();path.write_bytes(b'aaaa')
                elif change=='link':os.link(path,path.with_suffix('.link'))
                elif change=='mode':path.chmod(0o400)
                else:
                    destination=path.with_suffix('.data');path.rename(destination);path.symlink_to(destination)
                with self.assertRaises(ValueError):observed.check()

    def test_change_during_qualification_never_installs_ticket(self):
        ticket=qualification.Qualification()
        def mutate(image):
            value=self.validate(image);self.nested.chmod(0o600);self.nested.write_bytes(b'{}');return value
        with self.assertRaises(ValueError):ticket.binding(self.image,mutate)
        self.assertIsNone(ticket.dependencies)
        with self.assertRaisesRegex(ValueError,'ticket is invalid'):ticket.binding(self.image,self.validate)

    def test_new_image_or_failed_validator_cannot_reuse_ticket(self):
        ticket=qualification.Qualification();ticket.binding(self.image,self.validate)
        with self.assertRaisesRegex(ValueError,'image changed'):ticket.binding(dict(self.image,other=1),self.validate)
        failed=qualification.Qualification()
        with self.assertRaisesRegex(ValueError,'bad qualification'):
            failed.binding(self.image,mock.Mock(side_effect=ValueError('bad qualification')))
        self.assertIsNone(failed.dependencies)

    def test_nested_collection_and_warm_pure_caches_are_observed(self):
        import s22plus_debian_autoboot_phase_v1 as phases
        ticket=qualification.Qualification()
        with mock.patch.object(handoff.payloads,'cache_clear') as first, \
                mock.patch.object(phases.original_scripts,'cache_clear') as second, dependencies.ReadSet() as outer:
            ticket.binding(self.image,self.validate)
        first.assert_called_once();second.assert_called_once()
        self.assertEqual(outer.files,ticket.dependencies.files)


class DownloadDeadlineTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.folder=Path(temporary.name);self.now=1_000_000_000;self.launched=[];self.events=[]
        self.step=owner.Step('android-download','download','A')
        self.session=object.__new__(owner.Session)
        self.session.request={'operation':'debian-autoboot'}
        self.session.grant=dict(schema=owner.SCHEMA,host_boot=owner.host_boot(),
            opened_ns=1,deadline_ns=1000_000_000_000)
        self.session.check=lambda **kw:self.advance('check',19)
        self.session.unused=lambda:False
        self.session.rows=lambda:[]
        self.session.consume=lambda:self.advance('consume',19)
        self.session.journal=SimpleNamespace(append=self.append)
        self.publication_delay=0
        self.instance=object.__new__(adapter.Adapter)
        self.instance.folder=lambda *args,**kwargs:self.folder
        self.instance.android=lambda *args:SimpleNamespace(download=self.download)

    def advance(self,event,seconds):self.events.append(event);self.now+=seconds*1_000_000_000
    def append(self,event,**detail):
        self.intent=detail;self.advance('intent',self.publication_delay)
    def snapshot(self,*args):
        self.events.append('snapshot');return dict(generation='current',observed=self.now)
    def download(self,*,before_dispatch):
        before_dispatch();self.launched.append(self.now);return {}
    def execute(self):
        with mock.patch.object(adapter,'clock',side_effect=lambda:self.now), \
                mock.patch.object(owner,'clock',side_effect=lambda:self.now), \
                mock.patch.object(target,'usb_snapshot',side_effect=self.snapshot), \
                mock.patch.object(target,'wait_departure',side_effect=lambda before,folder,**kw:dict(before=before,deadline=kw['deadline_ns'])):
            return self.instance.android_download(self.step,{},guard=lambda:None,
                before_dispatch=lambda detail:self.session.intent(self.step,detail=detail))

    def test_delayed_guards_precede_fresh_snapshot_and_single_full_window(self):
        self.execute()
        self.assertEqual(self.events,['check','consume','snapshot','intent'])
        self.assertEqual(self.intent['detail']['departure_deadline_ns']-self.launched[0],30_000_000_000)
        self.assertEqual(records.read(self.folder/'departure-before.json')['observed'],self.launched[0])
        self.assertEqual(records.read(self.folder/'result.json')['departure']['deadline'],self.intent['detail']['departure_deadline_ns'])

    def test_slow_durable_publication_blocks_command_without_deadline_renewal(self):
        self.publication_delay=31
        with self.assertRaisesRegex(ValueError,'expired before Android command'):self.execute()
        self.assertEqual(self.launched,[])
        self.assertEqual(self.now-self.intent['detail']['departure_deadline_ns'],1_000_000_000)

    def test_finite_grant_expiry_during_publication_blocks_command(self):
        self.session.grant['deadline_ns']=40_000_000_000
        self.publication_delay=2
        with self.assertRaisesRegex(ValueError,'original native task grant expired'):self.execute()
        self.assertEqual(self.launched,[])

    def test_slow_snapshot_publication_cannot_start_a_fresh_window(self):
        original=adapter.publish
        def delayed(path,value):
            receipt=original(path,value)
            if path.name=='departure-before.json':self.advance('snapshot-publication',31)
            return receipt
        with mock.patch.object(adapter,'publish',side_effect=delayed):
            with self.assertRaisesRegex(ValueError,'expired before Android command'):self.execute()
        self.assertEqual(self.launched,[])
        self.assertEqual(self.now-self.intent['detail']['departure_deadline_ns'],1_000_000_000)

    def test_actual_raw_producer_prepares_streams_before_intent_and_spawn(self):
        # Real fixed Android.command + raw producer, using harmless host Python
        # as the executable and no USB/ADB. Only argv selection is a fixture.
        executable=Path(sys.executable).resolve()
        client=target.Android(records.pin(executable,maximum=32*1024*1024),{}, {},self.folder,guard=lambda:None)
        code='print("producer fixture")'
        original=raw.RawCaptureWriter
        def prepare(*args,**kwargs):
            writer=original(*args,**kwargs);self.advance('streams',40);return writer
        def dispatch():
            self.advance('intent',0)
            self.assertTrue((self.folder/'fixture.stdout.bin').exists())
            self.assertTrue((self.folder/'fixture.stderr.bin').exists())
        with mock.patch.object(raw,'RawCaptureWriter',side_effect=prepare):
            handle=client.command(['-c',code],'fixture',timeout=2,before_launch=dispatch)
        raw.require_success(handle)
        self.assertEqual(self.events,['streams','intent'])
        self.assertEqual(raw.read_stdout(handle,maximum=100),b'producer fixture\n')

    def test_rejected_spawn_callback_preserves_raw_failure_without_launch(self):
        def reject():raise ValueError('expired original grant')
        with mock.patch.object(raw.subprocess,'Popen') as spawn:
            handle=raw.acquire_command(['/fixture/unexecuted'],self.folder,'rejected',timeout=1,
                stdout_maximum=10,stderr_maximum=10,before_spawn=reject)
            spawn.assert_not_called()
        self.assertEqual(handle.producer_error_type,'ValueError')
        self.assertIsNone(handle.returncode)
        self.assertEqual(raw.read_stdout(handle,maximum=10),b'')
        self.assertEqual(raw.load_handle(handle.receipt_path),handle)

    def test_slow_poll_guard_cannot_sample_after_original_deadline(self):
        before=dict(snapshot=dict(path='/fixture/usb'),identity={})
        with mock.patch.object(target,'clock',side_effect=lambda:self.now), \
                mock.patch.object(target.usbfs,'snapshot_node') as sample:
            with self.assertRaisesRegex(ValueError,'guard exceeded original deadline'):
                target.wait_departure(before,self.folder,deadline_ns=self.now+30_000_000_000,
                    guard=lambda:self.advance('guard',31))
            sample.assert_not_called()


if __name__=='__main__':unittest.main()
