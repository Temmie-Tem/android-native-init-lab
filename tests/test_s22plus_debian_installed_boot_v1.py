"""P404 H0 state/proof cuts; no connected operation."""
from pathlib import Path
from contextlib import contextmanager
import importlib.util
import builtins
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_installed_boot_v1 as lane


class Rows:
    def __init__(self):self.items=[]
    def append(self,event,**data):self.items.append(dict(event=event,data=data))
    def rows(self):return self.items


class InstalledBootTests(unittest.TestCase):
    def setUp(self):
        self.rows=Rows()
        self.rows.append('owner-opened',plan={},grant={})

    def effect(self,step):
        self.rows.append('effect-intent',step=step,detail={})
        lane.journal_state(self.rows)
        self.rows.append('effect-result',step=step,receipt={})
        lane.journal_state(self.rows)

    def test_normal_return_needs_debian_health_physical_arrival_and_shutdown(self):
        self.effect('android-download')
        self.effect('candidate-boot')
        with self.assertRaises(ValueError):self.effect('debian-shutdown')
        self.rows.items.pop()
        self.rows.append('observation',step='debian-health',receipt={})
        self.effect('debian-shutdown')
        self.rows.append('native-return-armed',health={},shutdown={})
        with self.assertRaises(ValueError):self.effect('native-return')
        self.rows.items.pop()
        self.rows.append('physical-statement',role='P399',statement='attended Download')
        self.effect('native-return')
        self.rows.append('native-auth-intent',image={})
        self.rows.append('native-detach-intent',image={})
        self.rows.append('observation',step='native-health',receipt={})
        self.rows.append('terminal',receipt={})
        lane.journal_state(self.rows)

    def test_uncertain_intent_never_replays_and_a_needs_attendance(self):
        self.rows.append('effect-intent',step='android-download',detail={})
        lane.journal_state(self.rows)
        self.rows.append('research-stopped',error_type='Cut',message='cut')
        with self.assertRaises(ValueError):
            self.rows.append('effect-intent',step='android-download',detail={})
            lane.journal_state(self.rows)
        self.rows.items.pop()
        with self.assertRaises(ValueError):
            self.rows.append('effect-intent',step='android-restore',detail={})
            lane.journal_state(self.rows)
        self.rows.items.pop()
        self.rows.append('physical-statement',role='A',statement='attended Download')
        self.effect('android-restore')
        self.rows.append('terminal',receipt={})
        lane.journal_state(self.rows)

    def test_pre_intent_a_attendance_can_be_reaffirmed_without_a_replay(self):
        self.rows.append('effect-intent',step='android-download',detail={})
        self.rows.append('research-stopped',error_type='Cut',message='cut')
        self.rows.append('physical-statement',role='A',statement='attending')
        self.rows.append('physical-reaffirmed',role='A',statement='still attending')
        self.rows.append('effect-intent',step='android-restore',detail={})
        lane.journal_state(self.rows)
        with self.assertRaises(ValueError):
            self.rows.append('effect-intent',step='android-restore',detail={})
            lane.journal_state(self.rows)

    def test_no_effect_stop_can_close_without_flash(self):
        self.rows.append('research-stopped',error_type='Cut',message='cut')
        self.rows.append('terminal',receipt={})
        lane.journal_state(self.rows)
        self.assertEqual(len([r for r in self.rows.rows() if r['event']=='effect-intent']),0)

    def test_completed_a_raw_resumes_result_without_transfer(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            capture=base/'android-restore-transfer'/('attempt-'+'a'*32)
            capture.mkdir(parents=True)
            lane.publish(capture/'odin.capture.json',dict(retained=True))
            self.rows.append('physical-statement',role='A',statement='attended')
            self.rows.append('effect-intent',step='android-restore',
                detail=dict(capture_directory=str(capture)))
            owner=object.__new__(lane.Owner)
            owner.directory=base
            owner.journal=self.rows
            owner.transfer_proved=Mock(return_value=True)
            receipt=owner.finish_proved_a_transfer()
            self.assertEqual(receipt,lane.pin(base/'android-restore.json'))
            self.assertIn('android-restore',lane.journal_state(self.rows)[1])
            self.assertEqual(owner.transfer_proved.call_count,2)
            self.assertEqual(owner.finish_proved_a_transfer(),receipt)

    def test_corrupt_completed_a_result_cannot_close(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            capture=base/'android-restore-transfer'/('attempt-'+'b'*32)
            capture.mkdir(parents=True)
            lane.publish(capture/'odin.capture.json',dict(retained=True))
            self.rows.append('physical-statement',role='A',statement='attended')
            self.rows.append('effect-intent',step='android-restore',
                detail=dict(capture_directory=str(capture)))
            bad=lane.publish(base/'android-restore.json',dict(raw=dict(path='wrong'),
                transport=None))
            self.rows.append('effect-result',step='android-restore',receipt=bad)
            owner=object.__new__(lane.Owner)
            owner.directory=base
            owner.journal=self.rows
            owner.transfer_proved=Mock(return_value=True)
            with self.assertRaises(ValueError):owner.finish_proved_a_transfer()

    def test_frozen_recovery_review_ignores_candidate_and_new_review_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            critical=base/'owner.py';critical.write_text('old owner\n')
            candidate=base/'candidate.py';candidate.write_text('first candidate\n')
            review=base/'review.json'
            lane.publish(review,dict(schema=lane.SCHEMA+'-review',verdict='PASS_GO',
                scope='REACHABLE_OWNER_AND_BOUNDARY',findings=[],reviewer='independent',
                sources=[lane.pin(critical),lane.pin(candidate)]))
            original=lane.pin(review)
            candidate.write_text('second candidate\n')
            current=base/'new-review.json'
            lane.publish(current,dict(schema=lane.SCHEMA+'-review',verdict='PASS_GO',
                scope='REACHABLE_OWNER_AND_BOUNDARY',findings=[],reviewer='independent',
                sources=[lane.pin(critical),lane.pin(candidate)]))
            with patch.object(lane,'REVIEW',current), \
                    patch.object(lane,'recovery_sources',return_value=[critical]):
                self.assertEqual(lane.capability(recovery=original),original)
                critical.write_text('changed owner\n')
                with self.assertRaises(ValueError):lane.capability(recovery=original)

    def test_a_recovery_module_loads_without_native_return_modules(self):
        real_import=builtins.__import__
        excluded={'s22plus_native_adapter_v3','s22plus_native_host_v3',
            's22plus_native_observation_v3'}
        def import_without_native(name,*args,**kwargs):
            if name in excluded:raise ImportError('native-only module unavailable')
            return real_import(name,*args,**kwargs)
        spec=importlib.util.spec_from_file_location('p404_recovery_import_fixture',
            Path(lane.__file__))
        module=importlib.util.module_from_spec(spec)
        with patch('builtins.__import__',side_effect=import_without_native):
            spec.loader.exec_module(module)
        self.assertTrue(callable(module.Owner.recover_android))

    def test_native_close_continuation_holds_target_lease(self):
        held=[]
        @contextmanager
        def lease(_):
            held.append(True)
            try:yield
            finally:held.pop()
        owner=object.__new__(lane.Owner)
        owner.recovery=True
        owner._close_native_held=Mock(side_effect=lambda:len(held))
        with patch.object(lane.registry,'target_session_lease',lease):
            self.assertEqual(owner.close_native(),1)
        self.assertEqual(held,[])

    def test_candidate_raw_completion_reconstructs_only_its_bound_result(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            attempt=base/'candidate-boot-transfer'/('attempt-'+'c'*32)
            attempt.mkdir(parents=True)
            artifact=dict(path=str(base/'AP.tar.md5'),size=123,sha256='a'*64)
            odin=dict(path=str(base/'odin4'),size=456,sha256='b'*64)
            ticket=dict(device='/dev/bus/usb/001/002')
            command=lane.transport.build_odin_boot_only_command(
                Path(odin['path']),Path(artifact['path']),ticket['device'])
            invocation=lane.publish(attempt/'invocation.json',dict(
                command=command,odin=odin,ap=artifact,ticket=ticket))
            writer=lane.raw.RawCaptureWriter(attempt,'odin',stdout_maximum=65536,
                stderr_maximum=16384,argv0_name='odin4')
            writer.write_stdout(b'Setup Connection\nUpload Binaries\nboot.img.lz4\n'
                b'100%\nClose Connection\n')
            writer.finalize(returncode=0)
            self.rows.append('effect-intent',step='android-download',detail={})
            self.rows.append('effect-result',step='android-download',receipt={})
            self.rows.append('effect-intent',step='candidate-boot',detail=dict(
                ap=artifact,ticket=ticket,capture_directory=str(attempt),invocation=invocation))
            owner=object.__new__(lane.Owner)
            owner.directory=base
            owner.journal=self.rows
            owner.plan=dict(candidate=dict(ap=artifact),N=dict(ap={}),A=dict(ap={}),odin=odin)
            self.assertTrue(owner.transfer_proved('candidate-boot'))
            receipt=owner.finish_proved_transfer('candidate-boot')
            self.assertEqual(receipt,lane.pin(base/'candidate-boot.json'))
            self.assertTrue(lane.read(base/'candidate-boot.json')['resumed_from_original_raw'])
            self.assertEqual(owner.finish_proved_transfer('candidate-boot'),receipt)
            self.rows.items[3]['data']['detail']['ticket']=dict(device='/dev/bus/usb/001/003')
            with self.assertRaises(ValueError):owner.transfer_proved('candidate-boot')

    def test_shutdown_raw_and_departure_complete_without_resending_ssh(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            io=base/'debian-shutdown-io';io.mkdir()
            endpoint=dict(interface='usb-test')
            health=lane.publish(base/'debian-health.json',dict(endpoint=endpoint))
            for step in ('android-download','candidate-boot'):
                self.rows.append('effect-intent',step=step,detail={})
                self.rows.append('effect-result',step=step,receipt={})
            self.rows.append('observation',step='debian-health',receipt=health)
            self.rows.append('effect-intent',step='debian-shutdown',detail=dict(health=health))
            writer=lane.raw.RawCaptureWriter(io,'command',stdout_maximum=65536,
                stderr_maximum=16384,argv0_name='ssh')
            writer.write_stdout(b'DEBIAN_SHUTDOWN_REQUEST_ACCEPTED\n')
            writer.finalize(returncode=0)
            lane.publish(io/'departure.json',dict(endpoint=endpoint,
                observed_boottime_ns=10,method='NCM_ENDPOINT_ABSENT'))
            owner=object.__new__(lane.Owner)
            owner.directory=base
            owner.journal=self.rows
            owner.plan=dict(link=dict(ssh_address='192.0.2.2'))
            owner.ssh=Mock(side_effect=AssertionError('shutdown replay'))
            receipt=owner.finish_proved_shutdown()
            self.assertEqual(receipt,lane.pin(base/'debian-shutdown.json'))
            self.assertIn('debian-shutdown',lane.journal_state(self.rows)[1])
            self.assertEqual(owner.finish_proved_shutdown(),receipt)
            owner.ssh.assert_not_called()

    def test_native_detach_raw_can_publish_missing_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            for step in ('android-download','candidate-boot'):
                self.rows.append('effect-intent',step=step,detail={})
                self.rows.append('effect-result',step=step,receipt={})
            self.rows.append('observation',step='debian-health',receipt={})
            self.rows.append('effect-intent',step='debian-shutdown',detail={})
            self.rows.append('effect-result',step='debian-shutdown',receipt={})
            self.rows.append('native-return-armed',health={},shutdown={})
            self.rows.append('physical-statement',role='P399',statement='attending')
            self.rows.append('effect-intent',step='native-return',detail={})
            self.rows.append('effect-result',step='native-return',receipt={})
            self.rows.append('native-auth-intent',image={})
            self.rows.append('native-detach-intent',image={})
            owner=object.__new__(lane.Owner)
            owner.directory=base
            owner.journal=self.rows
            owner.plan=dict(N=dict(run_id_hex='a'*32))
            proof=dict(proof=dict(filesystem=dict(
                status='PASS_READONLY_WITNESS_CLEAN_UNMOUNT')))
            import s22plus_native_observation_v3 as native
            with patch.object(native,'rederive',return_value=proof) as rederive:
                receipt=owner.finish_proved_native_health(dict(boot_id_sha256='b'*64))
                self.assertEqual(receipt,lane.pin(base/'native-health.json'))
                self.assertEqual(owner.finish_proved_native_health(
                    dict(boot_id_sha256='b'*64)),receipt)
            self.assertEqual(rederive.call_count,2)
            self.assertIn('native-health',lane.journal_state(self.rows)[2])

    def test_zero_effect_owner_cut_closes_even_after_preintent_read(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            plan=lane.publish(base/'plan.json',dict(directory=str(base)))
            lane.publish(base/'grant.json',dict(attended=True))
            (base/'fresh-start').mkdir()
            lane.publish(base/'fresh-start/result.json',dict(healthy=True))
            (base/'android-download-io').mkdir()
            owner=object.__new__(lane.Owner)
            owner.directory=base
            owner.plan_receipt=plan
            owner.plan=dict(directory=str(base))
            owner.grant=dict(attended=True)
            owner.journal=self.rows
            owner.recovery=True
            self.rows.items.clear()  # Host cut after global owner, before journal open.
            @contextmanager
            def lease(_):yield
            with patch.object(lane.registry,'target_session_lease',lease), \
                 patch.object(lane.registry,'require_f1_owner'), \
                 patch.object(lane.registry,'retire_f1_owner') as retire, \
                 patch.object(lane,'validate_plan'), \
                 patch.object(lane,'validate_grant'), \
                 patch.object(lane.old,'android_projection',return_value=dict(healthy=True)):
                terminal=owner.close_no_effect()
                self.assertEqual(lane.read(lane.verify(terminal))['device_effects'],0)
                self.assertEqual([row['event'] for row in self.rows.rows()],
                    ['owner-opened','research-stopped','terminal'])
                self.assertEqual(owner.close_no_effect(),terminal)
                self.assertEqual(retire.call_count,2)

    def test_debian_health_rederives_from_raw_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            writer=lane.raw.RawCaptureWriter(Path(folder),'health',stdout_maximum=65536,
                stderr_maximum=16384)
            run='a'*32
            candidate=dict(namespace='p405',version='v0.4.0-rc.5',run_id='c'*32)
            body=(f'S22PLUS_FYG8_DEBIAN_V1 {run}\n'
                f"BOOTSTRAP_CANDIDATE {candidate['namespace']} {candidate['version']} {candidate['run_id']}\n"
                'pid1_exe=/usr/sbin/init\npid1_root=/\n'
                'BOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\n'
                'boot_id=11111111-1111-4111-8111-111111111111\n'
                'boot_count=3\nDEBIAN_HEALTH_PASS\n').encode()
            writer.write_stdout(body)
            handle=writer.finalize(returncode=0)
            plan=dict(root_run_id=run,candidate=candidate)
            value=lane.installed_health_projection(handle,plan)
            self.assertEqual(value['boot_count'],3)
            self.assertEqual(value['status'],'PASS_INSTALLED_DEBIAN_PID1')
            with self.assertRaises(ValueError):
                lane.installed_health_projection(handle,dict(plan,root_run_id='b'*32))
            with self.assertRaises(ValueError):
                lane.installed_health_projection(handle,dict(plan,candidate=dict(candidate,run_id='d'*32)))


if __name__=='__main__':unittest.main()
