"""Fixed renderer exit and actual PID1/observer/return lifecycle with platform fixtures."""
from pathlib import Path
import copy,sys,types,unittest
from unittest import mock
import test_s22plus_fyg8_p361_renderer as renderer_fixture
import s22plus_fyg8_p368_display_renderer as renderer

support=types.ModuleType('_p368_joined_fixture')
support.__file__=str(Path('tests/test_s22plus_fyg8_p367_lifecycle.py').resolve())
sys.modules[support.__name__]=support
raw=Path(support.__file__).read_text().replace('p367','p368').replace('P367','P368')
exec(compile(raw,support.__file__+'#p368','exec'),support.__dict__)
live=support.live

class RendererExit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(renderer_fixture,'renderer',renderer):
            renderer_fixture.RendererTests.setUpClass.__func__(cls)
    run_case=renderer_fixture.RendererTests.run_case
    def test_real_renderer_exits_seven_after_third_submission(self):
        for name in ('success','inherited-zero-fb'):
            result=self.run_case(name)
            self.assertEqual(result.returncode,7,result.stderr)
            self.assertEqual(result.stderr.count(b'DISPLAY_SWAP_SUBMITTED'),3)
            self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),4)
            self.assertNotIn(b'H0_STATIC_HELD',result.stdout)
    def test_prior_commit_failure_does_not_become_injected_exit(self):
        result=self.run_case('second-error')
        self.assertEqual(result.returncode,1,result.stderr)
        self.assertEqual(result.stderr.count(b'H0_ATOMIC_COUNT='),2)
        self.assertNotIn(b'DISPLAY_SWAP_SUBMITTED',result.stderr)

class ChildExitLifecycle(support.P368JoinedLifecycle):
    test_actual_joined_success_and_diagnostic_failure_with_foreign_download=None
    test_native_payload_is_p366_identity_only=None
    test_client_restart_before_eof_resumes_without_transfer_replay=None
    test_after_eof_cut_preserves_fixed_outputs_and_fails_closed=None
    def test_exact_fault_and_wrong_fault_have_distinct_terminal_results(self):
        for case in ('child-exit','normal','writer'):
            with self.subTest(case=case):
                p=self.prepared();backend=support.JoinedBackend(p,self.peer,case,foreign=True)
                with self.patches():
                    result=live.execute_prepared(p,p.approval_token,backend)
                    live.validate_live_result(result,p)
                self.assertEqual(result['current_state'],'CLOSED')
                self.assertFalse(result['recovery_required'])
                self.assertEqual(result['verdict'],'PASS_F1_V2_P368_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK' if case=='child-exit' else 'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                self.assertEqual([c for c in backend.calls if c.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
    def test_retained_qualification_rejects_wrong_exit_signal_and_swap_count(self):
        p=self.prepared();backend=support.JoinedBackend(p,self.peer,'child-exit')
        with self.patches():live.execute_prepared(p,p.approval_token,backend)
        observer=support.parent.support.observer
        proof=backend.fixture.proof
        observer.validate_qualification(proof)
        for key,value in (('display_submitted_swaps',2),('display_submitted_swaps',10),('display_child_exited_before_ready',False)):
            altered=copy.deepcopy(proof);altered['sessions'][0]['semantic'][key]=value
            with self.assertRaises(ValueError):observer.validate_qualification(altered)
        for child in ({'event':observer.control.CHILD_EXIT,'code':0},{'event':observer.control.CHILD_SIGNAL,'code':7},None):
            altered=copy.deepcopy(proof);altered['sessions'][0]['native_progress']['child_status']=child
            with self.assertRaises(ValueError):observer.validate_qualification(altered)

if __name__=='__main__':unittest.main()
