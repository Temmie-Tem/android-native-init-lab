import hashlib
import hmac
from pathlib import Path
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_autoboot_transition_v1 as trace


class TransitionTests(unittest.TestCase):
    key=b'k'*32
    run_id=b'r'*16
    boot=b'11111111-2222-3333-4444-555555555555'
    sources={actor:hashlib.sha256(str(actor).encode()).hexdigest() for actor in trace.ACTORS}

    def line(self,*,actor=4,seq=1,kind=2,stage=58,convention=2,result=0,error=0,ms=100,
            pid=11,ppid=1,source=None,boot=None):
        raw=bytearray(128);raw[:8]=b'S22AT01\0'
        struct.pack_into('<6I',raw,8,actor,seq,kind,stage,convention,error)
        struct.pack_into('<qQIIIIQIIII',raw,32,result,ms,pid,ppid,0,0,0,0,0,0,0)
        raw[88:120]=bytes.fromhex(source or self.sources[actor])
        boot=boot or self.boot
        tag=hmac.digest(self.key,trace.DOMAIN+self.run_id+hashlib.sha256(boot).digest()+raw,'sha256')
        return b'[  0.100] S22AT1 run='+self.run_id.hex().encode()+b' boot='+boot+b' mac='+tag.hex().encode()+b' data='+raw.hex().encode()+b'\n'

    def project(self,data,**kwargs):
        return trace.retained(data,key=self.key,run=self.run_id,expected=self.sources,**kwargs)

    def test_isolated_return_proves_checked_init_without_inventing_begin(self):
        result=self.project(self.line())
        self.assertTrue(result['installed_debian_pid1'])
        self.assertEqual(len(result['return_without_begin']),1)
        self.assertFalse(result['logging_complete'])

    def test_pre_exec_does_not_prove_installed_init(self):
        result=self.project(self.line(actor=3,stage=55,kind=1,convention=1,pid=1,ppid=0))
        self.assertFalse(result['installed_debian_pid1'])
        self.assertEqual(len(result['begin_without_return']),1)
        self.assertFalse(result['pending_call_proves_stall'])

    def test_duplicate_and_conflicting_sequences_block_progress_claim(self):
        for second in (self.line(),self.line(result=71,error=71)):
            with self.subTest(second=second):
                result=self.project(self.line()+second)
                self.assertFalse(result['progress_claim_valid'])
                self.assertFalse(result['installed_debian_pid1'])

    def test_foreign_actual_executable_is_not_physical_proof(self):
        result=self.project(self.line(source='00'*32))
        self.assertFalse(result['records'])
        self.assertEqual(result['rejected'],{'producer':1})

    def test_wrong_run_and_mac_are_not_records(self):
        wrong_run=self.line().replace(self.run_id.hex().encode(),b'00'*16)
        wrong_mac=self.line().replace(b'mac=',b'mac=00',1)
        self.assertFalse(self.project(wrong_run+wrong_mac)['records'])

    def test_checked_failure_is_not_installed_init_proof(self):
        result=self.project(self.line(result=71,error=71))
        self.assertFalse(result['installed_debian_pid1'])
        self.assertEqual(result['records'][0]['error'],71)

    def test_syscall_success_can_preserve_stale_errno(self):
        result=self.project(self.line(actor=1,stage=1,convention=1,pid=13,ppid=12,error=9))
        self.assertEqual(result['records'][0]['result'],0)
        self.assertEqual(result['records'][0]['errno_snapshot'],9)
        self.assertIsNone(result['records'][0]['error'])

    def test_actor_pid_and_stage_cannot_be_substituted(self):
        self.assertFalse(self.project(self.line(actor=2,stage=58,pid=1,ppid=0))['records'])
        self.assertFalse(self.project(self.line(pid=1))['records'])

    def test_mixed_kernel_boots_block_progress_claim(self):
        result=self.project(self.line()+self.line(seq=2,boot=b'22222222-2222-3333-4444-555555555555'))
        self.assertFalse(result['installed_debian_pid1'])
        self.assertIn('kernel_boot',result['conflicts'])

    def test_time_reversal_blocks_progress_claim(self):
        result=self.project(self.line(ms=100)+self.line(seq=2,ms=99))
        self.assertIn('actor_order',result['conflicts'])

    def test_truncation_and_empty_capture_never_prove_nonexecution(self):
        for data in (b'',self.line()[:-12]):
            result=self.project(data)
            self.assertFalse(result['records'])
            self.assertFalse(result['absence_proves_nonexecution'])

    def test_cross_mount_return_can_survive_missing_begin(self):
        result=self.project(self.line(actor=2,stage=45,convention=1,pid=1,ppid=0))
        self.assertEqual(result['return_without_begin'][0]['stage'],'MOVE_DEV')

    def test_installed_hook_can_be_invoked_through_sysvinit_shell(self):
        result=self.project(self.line(pid=65,ppid=64))
        self.assertTrue(result['installed_debian_pid1'])

    def test_distinct_sequence_cannot_repeat_or_contradict_same_return(self):
        for second in (self.line(seq=2),self.line(seq=2,result=71,error=71),
                       self.line(seq=2,kind=1)):
            result=self.project(self.line()+second)
            self.assertFalse(result['progress_claim_valid'])
            self.assertFalse(result['installed_debian_pid1'])

    def test_selected_syscalls_never_have_positive_return(self):
        self.assertFalse(self.project(self.line(actor=2,stage=45,convention=1,pid=1,ppid=0,result=3))['records'])
        self.assertFalse(self.project(self.line(actor=2,stage=50,convention=1,pid=1,ppid=0,result=0))['records'])


if __name__=='__main__':unittest.main()
