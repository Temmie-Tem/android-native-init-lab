"""Actual descriptor owner, paired STATUS raw receipts and rollback lifecycle."""
from pathlib import Path
import copy,json,sys,types,unittest
from unittest import mock
base=types.ModuleType('_p371_lifecycle_fixture');base.__file__=str(Path('tests/test_s22plus_fyg8_p370_lifecycle.py').resolve());sys.modules[base.__name__]=base
raw=Path(base.__file__).read_text().replace('p370','p371').replace('P370','P371').replace('live.planned_handoff','live.p371_planned_handoff')
raw=raw.replace("self.peer.start('resume-bad-ack' if self.case=='resume-bad-ack' else 'wait-good')","self.peer.start(self.case if self.case in ('resume-bad-ack','status-write-failure') else 'wait-good')")
exec(compile(raw,base.__file__+'#p371','exec'),base.__dict__)
live=base.live

class StatusLifecycle(base.JoinedLifecycle):
    def test_actual_status_samples(self):
        p=self.prepared();backend=base.Backend(p,self.peer,'wait-good')
        with self.patches():
            result=live.execute_prepared(p,p.approval_token,backend)
            live.validate_live_result(result,p)
            proof=result['live_state']['p371_native_return_control_qualification']
            self.assertEqual(len(proof['status_samples']),2)
            self.assertGreaterEqual(proof['status_samples'][1]['elapsed_since_first_ms'],2000)
            self.assertEqual(result['live_state']['command_count'],6)
            self.assertEqual(result['verdict'],'PASS_F1_V2_P371_NATIVE_RETURN_CONTROL_AND_ROLLED_BACK')

    def test_early_sample_negative_receipt_replays_status_facts(self):
        p=self.prepared();backend=base.Backend(p,self.peer,'wait-good')
        with self.patches(),mock.patch.object(base.observer.control,'STATUS_INTERVAL_SEC',0):
            result=live.execute_prepared(p,p.approval_token,backend)
            live.validate_live_result(result,p)
            self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
            self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
            self.assertEqual(self.peer.last_marks.count('download 0'),1)
            path=p.run_dir/'candidate-observer.json';raw=path.read_bytes();value=json.loads(raw)
            self.assertFalse(value['accepted']);self.assertEqual(len(value['proof']['status_samples']),2)
            self.assertLess(value['proof']['status_samples'][1]['elapsed_since_first_ms'],2000)
            live._p345_validate_receipt(p,path,backend.fixture.spec)
            changed=copy.deepcopy(value)
            for key in ('proof','p371_native_return_control_qualification'):
                changed[key]['status_samples'][1]['elapsed_since_first_ms']=2000
            path.chmod(0o600);path.write_text(json.dumps(changed));path.chmod(0o400)
            with self.assertRaisesRegex(live.F1LiveError,'raw STATUS samples differ'):
                live._p345_validate_receipt(p,path,backend.fixture.spec)
            path.chmod(0o600);path.write_bytes(raw);path.chmod(0o400)
            live._p345_validate_receipt(p,path,backend.fixture.spec)

    def test_partial_status_response_keeps_rollback_available(self):
        p=self.prepared();backend=base.Backend(p,self.peer,'status-write-failure')
        with self.patches():
            result=live.execute_prepared(p,p.approval_token,backend)
            live.validate_live_result(result,p)
        self.assertEqual(result['current_state'],'CLOSED');self.assertFalse(result['recovery_required'])
        self.assertEqual(result['verdict'],'NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK')
        self.assertEqual(self.peer.last_marks.count('status 1'),1)
        self.assertNotIn('download 0',self.peer.last_marks)
        self.assertEqual([x for x in backend.calls if x.startswith('transfer-')],['transfer-candidate','transfer-rollback'])

if __name__=='__main__':unittest.main()
