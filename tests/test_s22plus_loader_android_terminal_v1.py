"""The existing connector dispatches only exact loader controls and A recovery."""
from pathlib import Path
import unittest
from unittest import mock

import test_s22plus_mainline_terminal_v1 as common
import test_s22plus_approved_terminal_persistent_v1 as persistent
import s22plus_loader_android_profile_v1 as profile
import s22plus_mainline_task_v1 as task
import s22plus_native_records_v3 as records


class LoaderTerminalTests(common.TerminalTests):
    selected_profile=profile

    def test_comparison_schema_cannot_borrow_ram_profile_authority(self):
        bound=self.controller.bundle(str(self.base))
        self.assertEqual(bound['operation'],profile.OPERATION)
        self.assertEqual(bound['namespace'],profile.NAMESPACE)
        value=records.read(self.directory/'task.json');value['N']['profile']='mainline-ram-v1'
        common.save(self.directory/'task.json',value)
        with self.assertRaises(ValueError):self.controller.bundle(str(self.base))


class LoaderContinuationTests(common.MainlineContinuationTests):
    selected_profile=profile
    test_normal_physical_return_uses_original_observation_and_grant=None
    test_interrupted_mainline_without_stopped_row_only_selects_original_a_recovery=None

    def test_no_normal_continuation_and_settled_original_owner_is_reconciled_once(self):
        with self.assertRaises(ValueError):self.controller.continue_task(str(self.base),'continue_approved_task')
        result=self.controller.continue_task(str(self.base),'recover_approved_task')
        self.assertTrue(result['dispatched']);self.settle()
        self.assertTrue((self.operation/'fixture-recover').exists())
        self.raw.assert_not_called()
        stops=[r for r in self.journal.rows() if r['event']=='stopped']
        self.assertEqual(len(stops),1);self.assertEqual(stops[0]['data']['error_type'],'SettledLauncherInterruption')
        self.assertFalse(self.controller.continue_task(str(self.base),'recover_approved_task')['dispatched'])
        self.assertEqual([r for r in self.journal.rows() if r['event']=='stopped'],stops)

    def test_unsettled_launcher_or_uncertain_a_cannot_reconcile_a_stop(self):
        result=self.base/persistent.backend.DISPATCH/'result.json';saved=result.read_bytes();result.unlink()
        with self.assertRaises((ValueError,OSError)):self.controller.continue_task(str(self.base),'recover_approved_task')
        self.assertFalse(any(r['event']=='stopped' for r in self.journal.rows()))
        result.write_bytes(saved)
        self.journal.append('effect-intent',step='install-android',action='transfer',role='A')
        self.raw.return_value={'completed':False}
        with self.assertRaises(ValueError):self.controller.continue_task(str(self.base),'recover_approved_task')
        self.assertFalse(any(r['event']=='stopped' for r in self.journal.rows()))


class BackendClosureTests(unittest.TestCase):
    setUp=persistent.PersistentTests.setUp
    tearDown=persistent.PersistentTests.tearDown
    review=persistent.PersistentTests.review
    wait_result=persistent.PersistentTests.wait_result

    def test_recovery_backend_does_not_require_build_files_but_keeps_live_modules(self):
        build=self.root/'workspace/public/src/mainline/s22plus_loader_android_h0/guard.c'
        self.assertFalse(build.exists())
        persistent.transport.selected_review(self.root)
        persistent.backend.verify_bridge(self.root)
        build.parent.mkdir(parents=True);build.write_text('unreviewed candidate development edit')
        persistent.transport.selected_review(self.root)
        persistent.backend.verify_bridge(self.root)
        live=self.root/'workspace/public/src/scripts/revalidation/s22plus_loader_android_access_v1.py'
        live.write_text(live.read_text()+'\n# changed live observer\n')
        with self.assertRaises(ValueError):persistent.transport.selected_review(self.root)


if __name__=='__main__':unittest.main()
