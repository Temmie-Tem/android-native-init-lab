"""Remaining-effect model and actual raw failure grammar for setup completion."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'workspace/public/src/scripts/revalidation'))
import device_action_raw_capture_v1 as raw
import s22plus_native_gpt_setup_completion_v1 as completion
import s22plus_native_records_v3 as records
import s22plus_native_session_v3 as owner
import test_s22plus_native_gpt_session_v1 as model


class CompletionTests(unittest.TestCase):
    setUp=model.GptOwnerTests.setUp
    operation=model.GptOwnerTests.operation
    through_reset=model.GptOwnerTests.through_reset

    def ready(self):
        session,device=self.operation();self.through_reset(session)
        device.health_failure=True
        self.assertEqual(session.resume(attended=True,operator_statement='Initial setup reported')['state'],
            'AWAITING_GPT_RECOVERY')
        device.health_failure=False
        prefix=[q.read_bytes() for q in sorted(session.journal.directory.glob('*.json'))]
        self.assertEqual(len(prefix),20)
        directory=self.root/'completion-review';directory.mkdir()
        incident=records.publish(directory/'incident.json',{'fixture':'independent bound incident'})
        review=records.publish(directory/'review.json',{'fixture':'independent source review'})
        # Real retained bindings are exercised by prepare/independent H0 on the
        # exact run. This model isolates the remaining dispatch/owner behavior.
        patch=mock.patch.object(completion,'verify_binding',return_value={});patch.start();self.addCleanup(patch.stop)
        return session,device,completion.Completion(session,incident,review),prefix

    def execute(self,run):
        return run.execute(attended=True,operator_statement='Operator requests root after setup')

    def test_success_keeps_stop_and_performs_only_the_first_remaining_reboot(self):
        session,device,run,prefix=self.ready();old=list(device.actions)
        result=self.execute(run)
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual(device.actions[len(old):],['health:android-initial','android-reboot','health:android-final'])
        self.assertEqual((device.apply_count,device.restore_count,device.reset_count,device.reboot_count),(1,0,1,1))
        self.assertEqual([q.read_bytes() for q in sorted(session.journal.directory.glob('*.json'))[:20]],prefix)
        self.assertIsNone(self.f1)

    def test_missing_review_dispatches_nothing(self):
        session,device,run,prefix=self.ready();before=list(device.actions)
        with mock.patch.object(completion,'verify_binding',side_effect=ValueError('review mismatch')), \
                self.assertRaises(ValueError):self.execute(run)
        self.assertEqual(device.actions,before);self.assertIsNotNone(self.f1)

    def test_expired_original_grant_dispatches_nothing(self):
        session,device,run,prefix=self.ready();before=list(device.actions)
        with mock.patch.object(owner,'clock',return_value=session.grant['deadline_ns']+1),self.assertRaises(ValueError):
            self.execute(run)
        self.assertEqual(device.actions,before)

    def test_uncertain_reboot_is_never_repeated_or_replaced_by_a_transfer(self):
        session,device,run,prefix=self.ready();device.fail_after='android-reboot'
        with self.assertRaises(OSError):self.execute(run)
        self.assertEqual(device.reboot_count,1);before=list(device.actions)
        with self.assertRaisesRegex(ValueError,'later unresolved'):self.execute(run)
        self.assertEqual(device.actions,before);self.assertIsNotNone(self.f1)

    def test_expiry_during_intent_publication_keeps_intent_without_dispatch(self):
        session,device,run,prefix=self.ready();original=owner.clock
        def clock():
            return session.grant['deadline_ns']+1 if model.gpt.intents(device,'android-reboot') else original()
        with mock.patch.object(owner,'clock',side_effect=clock),self.assertRaises(ValueError):self.execute(run)
        self.assertEqual(device.reboot_count,0)
        self.assertEqual(len(model.gpt.intents(device,'android-reboot')),1)

    def test_terminal_publication_cut_remains_h0_repairable(self):
        session,device,run,prefix=self.ready();original=owner.publish;cut=[False]
        def publish(path,value):
            if Path(path)==session.directory/'terminal.json' and not cut[0]:
                cut[0]=True;raise OSError('terminal publication cut')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=publish),self.assertRaises(OSError):self.execute(run)
        self.assertFalse(any(row['event']=='setup-completion-stopped' for row in session.rows()))
        before=list(device.actions);result=run.repair()
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual(device.actions,before);self.assertEqual(device.reboot_count,1)

    def test_h0_repair_requires_unchanged_supplemental_admission(self):
        session,device,run,prefix=self.ready();original=owner.publish
        def publish(path,value):
            if Path(path)==session.directory/'terminal.json':raise OSError('terminal publication cut')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=publish),self.assertRaises(OSError):self.execute(run)
        path=run.folder/'admission.json';path.chmod(0o600);path.write_bytes(b'{}\n');path.chmod(0o400)
        before=list(device.actions)
        with self.assertRaisesRegex(ValueError,'admission provenance'):run.repair()
        self.assertEqual(device.actions,before);self.assertIsNotNone(self.f1)
        self.assertFalse((session.directory/'terminal.json').exists())

    def test_publication_cut_reuses_the_original_reboot_proof(self):
        session,device,run,prefix=self.ready();original=owner.publish;cut=[False]
        def publish(path,value):
            if Path(path)==session.directory/'android-reboot.json' and not cut[0]:
                cut[0]=True;raise OSError('publication cut after actual reboot')
            return original(path,value)
        with mock.patch.object(owner,'publish',side_effect=publish),self.assertRaises(owner.ResultPublicationError):
            self.execute(run)
        self.assertEqual(device.reboot_count,1)
        result=self.execute(run)
        self.assertEqual(result['reboot']['status'],'PASS_CHANGED_BOOT_GPT_CAPACITY_AND_ROOT')
        self.assertEqual(device.reboot_count,1)
        before=list(device.actions);run.repair();self.assertEqual(device.actions,before)


class MissingSuTests(unittest.TestCase):
    def test_actual_raw_producer_requires_the_exact_completed_missing_su_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            for index,(code,stdout,stderr,accepted) in enumerate(((127,b'',completion.SU_MISSING,True),
                    (0,b'',completion.SU_MISSING,False),(127,b'extra',completion.SU_MISSING,False),
                    (127,b'',b'Permission denied\n',False))):
                body='import sys;sys.stdout.buffer.write('+repr(stdout)+');sys.stderr.buffer.write('+repr(stderr)+');sys.exit('+str(code)+')'
                handle=raw.acquire_command([sys.executable,'-c',body],Path(folder),f'case-{index}',timeout=5,
                    stdout_maximum=16384,stderr_maximum=16384)
                receipt=records.pin(handle.receipt_path)
                if accepted:completion.missing_su(receipt)
                else:
                    with self.assertRaises(ValueError):completion.missing_su(receipt)


if __name__=='__main__':unittest.main()
