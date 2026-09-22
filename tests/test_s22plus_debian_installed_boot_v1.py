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

    def test_debian_health_rederives_from_raw_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            writer=lane.raw.RawCaptureWriter(Path(folder),'health',stdout_maximum=65536,
                stderr_maximum=16384)
            run='a'*32
            body=(f'S22PLUS_FYG8_DEBIAN_V1 {run}\n'
                'pid1_exe=/usr/sbin/init\npid1_root=/\n'
                'BOOTSTRAP_HANDOFF pid=1 children=0 backend=s22plus-fyg8\n'
                'boot_id=11111111-1111-4111-8111-111111111111\n'
                'boot_count=3\nDEBIAN_HEALTH_PASS\n').encode()
            writer.write_stdout(body)
            handle=writer.finalize(returncode=0)
            value=lane.installed_health_projection(handle,dict(root_run_id=run))
            self.assertEqual(value['boot_count'],3)
            self.assertEqual(value['status'],'PASS_INSTALLED_DEBIAN_PID1')
            with self.assertRaises(ValueError):
                lane.installed_health_projection(handle,dict(root_run_id='b'*32))


if __name__=='__main__':unittest.main()
