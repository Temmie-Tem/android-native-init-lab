"""Actual common owner, raw reopen and rollback for all shared step variants."""
import importlib
import copy,json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
from tests import s22plus_display_step_h0_support as support


def fixture(prefix):
    native=types.ModuleType('test_s22plus_fyg8_'+prefix+'_handoff')
    native.runtime=importlib.import_module('s22plus_fyg8_'+prefix+'_research_shell_runtime')
    native.observer=importlib.import_module('s22plus_fyg8_'+prefix+'_research_shell_observer')
    native.KEY=b'k'*32;native.source=lambda:support.native_source(prefix)
    sys.modules[native.__name__]=native
    base=types.ModuleType('_'+prefix+'_step_lifecycle');base.__file__=str(Path('tests/test_s22plus_fyg8_p370_lifecycle.py').resolve());sys.modules[base.__name__]=base
    raw=Path(base.__file__).read_text().replace('p370',prefix).replace('P370',prefix.upper()).replace('live.planned_handoff','live.'+prefix+'_planned_handoff')
    raw=raw.replace("self.peer.start('resume-bad-ack' if self.case=='resume-bad-ack' else 'wait-good')","self.peer.start(self.case)")
    exec(compile(raw,base.__file__+'#'+prefix,'exec'),base.__dict__)
    return base


BASE=fixture('p372')
class DisplayStepLifecycle(BASE.JoinedLifecycle):
    # Use fixture infrastructure, not predecessor-specific assertions.
    for _name in dir(BASE.JoinedLifecycle):
        if _name.startswith('test_'):locals()[_name]=None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.renderer=support.build_renderer(cls.peer.root/'renderer','p372')

    def test_requested_frame_result_raw_reopen_and_terminal_recovery(self):
        p=self.prepared();backend=BASE.Backend(p,self.peer,'wait-good')
        with self.patches(),mock.patch.dict(os.environ,DISPLAY_STEP_RENDERER=str(self.renderer)):
            result=BASE.live.execute_prepared(p,p.approval_token,backend)
            BASE.live.validate_live_result(result,p)
            self.assertEqual(result['verdict'],'PASS_F1_V2_P372_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK')
            self.assertEqual(result['live_state']['command_count'],7)
            self.assertEqual(result['live_state']['p372_native_return_control_qualification']['status_samples'][-1]['completed_steps'],1)
            again=BASE.live.recover_prepared(p,backend)
            self.assertEqual(again,result)
        self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])


def extra_lifecycle(prefix):
    base=fixture(prefix)
    class FixedVariant(base.JoinedLifecycle):
        for name in dir(base.JoinedLifecycle):
            if name.startswith('test_'):locals()[name]=None
        @classmethod
        def setUpClass(cls):
            super().setUpClass();cls.renderer=support.build_renderer(cls.peer.root/'renderer',prefix)
        def test_actual_fixed_variant_raw_and_rollback(self):
            p=self.prepared();backend=base.Backend(p,self.peer,'wait-good')
            with self.patches(),mock.patch.dict(os.environ,DISPLAY_STEP_RENDERER=str(self.renderer)):
                result=base.live.execute_prepared(p,p.approval_token,backend)
                base.live.validate_live_result(result,p)
                self.assertEqual(result['verdict'],'PASS_F1_V2_'+prefix.upper()+'_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK')
                self.assertEqual(result['live_state']['command_count'],8 if prefix=='p373' else 7)
                sample=result['live_state'][prefix+'_native_return_control_qualification']['status_samples'][-1]
                self.assertEqual(sample['completed_steps'],2 if prefix=='p373' else 0)
                self.assertEqual(sample['exit_code'],0 if prefix=='p373' else 7)
            self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
        def test_pending_work_raw_failure_receipt_and_tamper(self):
            if prefix!='p373':return
            p=self.prepared();backend=base.Backend(p,self.peer,'step-stall')
            with self.patches(),mock.patch.dict(os.environ,DISPLAY_STEP_RENDERER=str(self.renderer)):
                result=base.live.execute_prepared(p,p.approval_token,backend)
                base.live.validate_live_result(result,p)
                self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
                self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
                self.assertEqual(self.peer.last_marks.count('download 0'),1)
                path=p.run_dir/'candidate-observer.json';original=path.read_bytes();value=json.loads(original)
                self.assertIsNone(value['proof']['status_samples'][1]['request'])
                self.assertTrue(value['proof']['status_samples'][1]['pending'])
                base.live._p345_validate_receipt(p,path,backend.fixture.spec)
                changed=copy.deepcopy(value)
                for key in ('proof',prefix+'_native_return_control_qualification'):
                    changed[key]['status_samples'][1]['completed_steps']=2
                    changed[key]['status_samples'][1]['pending']=False
                path.chmod(0o600);path.write_text(json.dumps(changed));path.chmod(0o400)
                with self.assertRaisesRegex(base.live.F1LiveError,'raw STATUS samples differ'):
                    base.live._p345_validate_receipt(p,path,backend.fixture.spec)
                path.chmod(0o600);path.write_bytes(original);path.chmod(0o400)
                base.live._p345_validate_receipt(p,path,backend.fixture.spec)
            self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])
    return FixedVariant

P373Lifecycle=extra_lifecycle('p373')
P374Lifecycle=extra_lifecycle('p374')


if __name__=='__main__':unittest.main()
