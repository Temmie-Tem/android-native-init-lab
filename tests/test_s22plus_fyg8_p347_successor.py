"""P347 actual receipt projection and strengthened semantic rejection, H0."""
from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'workspace/public/src/scripts/revalidation'),
               str(ROOT/'workspace/public/src/scripts/analysis')]
import device_action_f1_live_v2 as live
import device_action_f1_v2 as core
import s22plus_fyg8_p347_research_shell_runtime as runtime
import s22plus_fyg8_p347_research_shell_observer as observer
import s22plus_fyg8_p347_artifact_identity as artifact
import s22plus_fyg8_p347_process_v2_candidate_static as static
import s22plus_fyg8_p345_research_shell_runtime as old_runtime
from test_s22plus_fyg8_p345_live_receipt import _ReceiptFixture, KEY, KEY_SHA256


class P347SuccessorTests(unittest.TestCase):
    def test_actual_receipt_reopen_projection_and_semantic_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = _ReceiptFixture(Path(directory)/'run', variant='p347')
            self.assertGreater(len(fixture.payload), 120000)
            variant = live._host_first_variant(fixture.prepared.bundle)
            with mock.patch.object(live, '_p328_read_auth_key', return_value=(KEY, KEY_SHA256)), \
                 mock.patch.object(live, '_reopen_candidate_guard_release',
                                   return_value={'status': 'released', 'released': True}):
                durable = live._reopen_candidate_observation(fixture.prepared)
                self.assertTrue(variant.proof_ok(durable))
                state = {'candidate_classification':'odin_transfer_completed',
                         'candidate_completed':True, 'download_endpoint_absent':True,
                         'rollback_classification':'odin_transfer_completed',
                         'rollback_completed':True, 'final_verified':True}
                proof = live._candidate_arrival_proof_projection(fixture.prepared, state)
                self.assertTrue(proof['proof'])
                self.assertEqual(json.loads(json.dumps(proof)), proof)
                for flag in ('candidate_completed', 'rollback_completed', 'final_verified'):
                    bad = dict(state); bad[flag] = False
                    self.assertFalse(live._candidate_arrival_proof_projection(fixture.prepared,bad)['proof'])
            for change in ('short-timeout', 'missing-output'):
                bad = copy.deepcopy(fixture.proof)
                if change == 'short-timeout':
                    bad['sessions'][2]['commands'][1]['duration_ms'] = 101
                else:
                    bad['sessions'][4]['commands'][1]['output'] = observer.identity(b'x\n'*32768)
                with self.assertRaises(observer.QualificationError):
                    observer.validate_qualification(bad)

    def test_consumed_inputs_and_source_drift_rejected(self):
        self.assertNotEqual(runtime.P347_RUN_ID, old_runtime.P345_RUN_ID)
        self.assertNotEqual(runtime.child_source(), old_runtime.child_source())
        acceptance = live.typed_evidence.p347_stock_adapter.acceptance_fixture()
        closure = static.source_receipts()
        for role in ('p347_child_loader_template', 'p347_readonly_child', 'p347_readonly_child_c',
                     'p347_template_research_shell_runtime', 'p347_template_research_shell_observer'):
            self.assertIn(role, closure)
        sources = core.execution_critical_source_receipts(acceptance,
            candidate_arrival_proof_role=live.typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE)
        core.verify_candidate_source_binding(acceptance, {'source_closure':closure}, sources)
        bad = copy.deepcopy(sources)
        bad['p347_template_research_shell_observer']['sha256'] = '0'*64
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_source_binding(acceptance, {'source_closure':closure}, bad)
        for old in (artifact.P345_CONSUMED_AP_IDENTITY, artifact.P346_CONSUMED_AP_IDENTITY):
            with self.assertRaises(artifact.ArtifactIdentityError):
                artifact.validate_rollback_ap(Path('/unused'),old)


if __name__ == '__main__': unittest.main()
