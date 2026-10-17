"""Partial rcS observations preserve syscall, fork and completion boundaries."""
import hashlib
import hmac
import struct
import unittest

import test_s22plus_autoboot_transition_v1 as base
trace=base.trace


class RcsFacts(unittest.TestCase):
    key=base.TransitionTests.key
    run_id=base.TransitionTests.run_id
    boot=base.TransitionTests.boot
    sources={**base.TransitionTests.sources,6:base.TransitionTests.sources[4],7:base.TransitionTests.sources[4]}

    def line(self,*,child=0,status=0,done=0,**kwargs):
        line=base.TransitionTests.line(self,**kwargs)
        match=trace.LINE.fullmatch(b'S22AT1'+line.split(b'S22AT1',1)[1].rstrip(b'\n'))
        self.assertIsNotNone(match)
        run,boot,_,encoded=match.groups();body=bytearray.fromhex(encoded.decode())
        struct.pack_into('<III',body,72,child,status,done)
        tag=hmac.digest(self.key,trace.DOMAIN+self.run_id+hashlib.sha256(boot).digest()+body,'sha256')
        return b'S22AT1 run='+run+b' boot='+boot+b' mac='+tag.hex().encode()+b' data='+body.hex().encode()+b'\n'

    def project(self,*lines):
        return trace.retained(b''.join(lines),key=self.key,run=self.run_id,expected=self.sources)

    def fork(self,**kwargs):
        return self.line(actor=6,stage=64,convention=1,result=22,pid=21,ppid=1,**kwargs)

    def child(self,**kwargs):
        values=dict(actor=7,stage=71,kind=4,convention=3,result=0,pid=22,ppid=21)
        values.update(kwargs);return self.line(**values)

    def test_actual_fork_and_child_identity_join(self):
        value=self.project(self.fork(),self.child())
        self.assertTrue(value['progress_claim_valid'])
        self.assertTrue(value['rcs_child_fork_proved'])
        self.assertFalse(value['rcs_child_exec_proved'])

    def test_child_cannot_cross_parent_or_fork_identity(self):
        for values in (dict(pid=23),dict(ppid=20)):
            with self.subTest(values=values):
                value=self.project(self.fork(),self.child(**values))
                self.assertFalse(value['progress_claim_valid'])
                self.assertFalse(value['rcs_child_fork_proved'])

    def test_pre_exec_and_failed_exec_never_prove_exec_success(self):
        for kind,result,error in ((1,0,0),(2,-1,2)):
            value=self.project(self.child(stage=74,kind=kind,convention=1,result=result,error=error))
            self.assertFalse(value['rcs_child_exec_proved'])
            self.assertFalse(value['rcs_completed'])

    def test_parent_fork_zero_and_exec_success_return_are_impossible(self):
        for row in (self.line(actor=6,stage=64,convention=1,result=0,pid=21),
                    self.child(stage=74,kind=2,convention=1,result=0)):
            self.assertFalse(self.project(row)['records'])

    def test_reaped_child_failure_is_not_rcs_completion(self):
        reaped=self.line(actor=6,stage=69,kind=4,convention=3,pid=21,ppid=1,
            seq=2,child=22,status=125<<8,done=1)
        value=self.project(self.fork(),self.child(),reaped)
        self.assertTrue(value['progress_claim_valid'])
        self.assertEqual(value['records'][-1]['wait_status'],125<<8)
        self.assertFalse(value['rcs_completed'])

    def test_wait_must_refer_to_the_same_forked_child(self):
        for row in (self.line(actor=6,stage=66,convention=1,pid=21,result=23,seq=2),
                    self.line(actor=6,stage=69,kind=4,convention=3,pid=21,seq=2,child=23,done=1)):
            value=self.project(self.fork(),row)
            self.assertIn('rcs_wait_join',value['conflicts'])

    def test_checked_completion_is_independent_of_missing_child_records(self):
        value=self.project(self.line(actor=6,stage=70,kind=4,convention=3,pid=21))
        self.assertTrue(value['rcs_completed'])
        self.assertTrue(value['rcs_child_exec_proved'])
        self.assertFalse(value['rcs_child_fork_proved'])
        self.assertEqual(value['highest_authenticated_stage'],'RCS_COMPLETE')

    def test_missing_record_return_does_not_locate_a_stall(self):
        value=self.project(self.line(actor=6,stage=65,kind=1,convention=2,pid=21),
            self.line(actor=6,stage=75,kind=2,convention=1,result=128,pid=21,seq=2))
        self.assertFalse(value['rcs_fork_record_completed'])
        self.assertFalse(value['pending_call_proves_stall'])
        self.assertEqual(value['begin_without_return'][0]['stage'],'RCS_FORK_RECORD')

    def test_unknown_child_executable_or_unselected_actor_is_rejected(self):
        value=self.project(self.child(source='00'*32))
        self.assertEqual(value['rejected'],{'producer':1})
        value=trace.retained(self.child(),key=self.key,run=self.run_id,expected=base.TransitionTests.sources)
        self.assertFalse(value['records'])
        self.assertNotIn('rcs_completed',value)

    def parent(self,stage,**kwargs):
        values=dict(actor=6,stage=stage,pid=21,ppid=1)
        values['convention']=trace.stages()[stage][2]
        if values['convention']==3:values['kind']=4
        values.update(kwargs);return self.line(**values)

    def assert_conflict(self,*rows):
        proof=self.project(*rows)
        self.assertFalse(proof['rejected'])
        self.assertFalse(proof['progress_claim_valid'])
        self.assertFalse(proof['rcs_completed'])
        self.assertFalse(proof['rcs_child_exec_proved'])
        self.assertFalse(proof['rcs_fork_record_completed'])

    def test_failed_child_or_reap_cannot_coexist_with_completion(self):
        for failed in (self.child(stage=72,kind=2,convention=1,result=-1,error=22),
                self.child(stage=73,kind=2,convention=1,result=0),
                self.child(stage=73,kind=2,convention=1,result=-1,error=22),
                self.child(stage=74,kind=2,convention=1,result=-1,error=2),
                self.parent(69,child=22,status=126<<8,done=1)):
            self.assert_conflict(failed,self.parent(70,seq=2))

    def test_failed_child_cannot_have_successful_reap_or_later_exec(self):
        for stage in (72,73,74):
            failed=self.child(stage=stage,kind=2,convention=1,result=-1,error=22)
            self.assert_conflict(failed,self.parent(69,child=22,done=1))
            if stage!=74:
                self.assert_conflict(failed,self.child(stage=74,seq=2,kind=1,convention=1))

    def test_failed_fork_or_admission_cannot_advance(self):
        for stage in (61,62,63,64):
            failed=self.parent(stage,result=-1 if stage==64 else 5,error=5)
            for later in (self.child(),self.parent(65,kind=1,seq=2),self.parent(70,seq=2)):
                self.assert_conflict(failed,later)

    def test_child_wait_and_reap_join_without_fork_record(self):
        for later in (self.parent(66,result=23),self.parent(69,child=23,done=1)):
            self.assert_conflict(self.child(),later)
        self.assert_conflict(self.parent(66,result=22),self.parent(69,seq=2,child=23,done=1))

    def test_record_failures_cannot_complete_record_or_enter_wait(self):
        for stage,result,error in ((75,127,0),(75,-1,5),(76,-1,9),(77,5,5),(78,-1,5),(65,5,5)):
            failed=self.parent(stage,result=result,error=error)
            for later in (self.parent(65,seq=2),self.parent(66,seq=2),
                          self.parent(69,seq=2,child=22,done=1),self.parent(70,seq=2)):
                self.assert_conflict(failed,later)

    def test_failed_record_still_allows_owned_close_and_stop(self):
        for stage,result,error in ((75,127,0),(76,-1,9),(77,5,5)):
            value=self.project(self.parent(stage,result=result,error=error),
                self.parent(78,seq=2),self.parent(78,seq=3,kind=3,convention=3,error=5))
            self.assertTrue(value['progress_claim_valid'])
            self.assertFalse(value['rcs_fork_record_completed'])

    def test_fatal_wait_sleep_or_heartbeat_cannot_complete(self):
        for stage in (66,67,68):
            self.assert_conflict(self.parent(stage,result=5 if stage==68 else -1,error=5),
                self.parent(70,seq=2))
        for stage in (67,68):
            self.assert_conflict(self.parent(66,result=22),self.parent(stage,seq=2))

    def test_interrupted_wait_sleep_and_stale_errno_success_can_complete(self):
        for stage in (66,67):
            value=self.project(self.parent(stage,result=-1,error=4),self.parent(70,seq=2))
            self.assertTrue(value['rcs_completed'])
        value=self.project(self.parent(76,error=9),self.parent(65,seq=2),self.parent(70,seq=3))
        self.assertTrue(value['rcs_completed'])

    def test_co_present_stage_reversal_is_rejected(self):
        for first,last in ((70,66),(66,65),(75,65),(78,77),(62,61)):
            self.assert_conflict(self.parent(first,result=128 if first==75 else 0),
                self.parent(last,seq=2,kind=1))
        self.assert_conflict(self.child(stage=74,kind=1,convention=1),
            self.child(stage=72,kind=1,convention=1,seq=2))

    def test_heartbeat_may_precede_first_sleep_and_child_may_precede_fork_return(self):
        for order in ((67,68),(68,67)):
            value=self.project(self.parent(66),self.parent(order[0],seq=2),
                self.parent(order[1],seq=3),self.parent(70,seq=4))
            self.assertTrue(value['rcs_completed'])
        value=self.project(self.child(ms=50),self.fork(ms=100))
        self.assertTrue(value['progress_claim_valid'])

    def test_stop_cannot_resume_but_post_completion_stop_is_valid(self):
        self.assert_conflict(self.parent(64,kind=3,convention=3,error=5),self.parent(70,seq=2))
        value=self.project(self.parent(70),self.parent(70,seq=2,kind=3,convention=3,error=5))
        self.assertTrue(value['rcs_completed'])

    def test_shared_boot_clock_enforces_only_causal_parent_child_bounds(self):
        self.assert_conflict(self.parent(64,kind=1,ms=101),self.child(ms=100))
        for end in (self.parent(69,child=22,done=1,ms=100),self.parent(70,ms=100)):
            self.assert_conflict(self.child(ms=101),end)
            self.assertTrue(self.project(self.child(ms=100),end)['progress_claim_valid'])
        self.assertTrue(self.project(self.parent(64,kind=1,ms=100),self.child(ms=100))['progress_claim_valid'])
        self.assertTrue(self.project(self.child(ms=101))['progress_claim_valid'])


if __name__=='__main__':unittest.main()
