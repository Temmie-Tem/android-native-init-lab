"""Inactive watchdog observer: actual C producer, bounded reads, strict decoder."""
import hashlib
import hmac
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_debian_autoboot_transition_v1 as trace

KEY=bytes([7])+bytes(31)
RUN=bytes([8])+bytes(15)
BOOT=b'01234567-89ab-cdef-0123-456789abcdef'
SOURCE=hashlib.sha256(b'synthetic watchdog H0 executable').hexdigest()
EXPECTED={actor:SOURCE for actor in trace.WATCHDOG_ACTORS}


def stat_text(pid=230,**changes):
    fields={9:0x00200000,14:10,15:2,20:1,22:123,39:7,40:99,41:1}
    fields.update({int(k):v for k,v in changes.items()})
    return f'{pid} (gh-watchdog) S '+ ' '.join(str(fields.get(i,0)) for i in range(4,53))+'\n'


def authenticated(body,boot=BOOT):
    tag=hmac.digest(KEY,trace.DOMAIN+RUN+hashlib.sha256(boot).digest()+body,'sha256')
    return b'S22AT1 run='+RUN.hex().encode()+b' boot='+boot+b' mac='+tag.hex().encode()+b' data='+body.hex().encode()+b'\n'


def record(*,actor=6,seq=1,kind=4,stage=79,convention=3,error=0,value=12,ms=6000,
           task=230,start=123,properties=ord('S')|(7<<8)|(1<<16)|(99<<24),sample=6000<<3,pid=21):
    raw=bytearray(128);raw[:8]=b'S22AT01\0'
    struct.pack_into('<6I',raw,8,actor,seq,kind,stage,convention,error)
    struct.pack_into('<qQIIIIQIIII',raw,32,value,ms,pid,1,0,0,0,task,start,properties,sample)
    raw[88:120]=bytes.fromhex(SOURCE)
    return authenticated(raw)


def project(data,**kwargs):
    return trace.retained(data,key=KEY,run=RUN,expected=kwargs.pop('expected',EXPECTED),**kwargs)


class WatchdogProducer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='s22-watchdog-h0-')
        cls.folder=Path(cls.temp.name);cls.commands=[]
        for name,compiler,extra in (('host','gcc',[]),('arm64','aarch64-linux-gnu-gcc',['-static'])):
            if not shutil.which(compiler):raise RuntimeError(f'required H0 compiler missing: {compiler}')
            command=[compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',*extra,
                '-I',str(ROOT/'workspace/public/src/native-init'),
                '-I',str(ROOT/'workspace/public/src/debian/s22plus_initramfs_h0'),
                str(ROOT/'tests/s22plus_autoboot_watchdog_harness.c'),'-o',str(cls.folder/name)]
            result=subprocess.run(command,capture_output=True,timeout=60)
            if result.returncode:raise RuntimeError(result.stderr.decode())
            cls.commands.append(command)
        if not shutil.which('qemu-aarch64'):raise RuntimeError('required H0 ARM64 runner missing')

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def run_case(self,case='normal',*,actor=6,stat=None,comm='gh-watchdog\n',wchan='qcom_wdt_kthread',second=False,symlink=False):
        outputs=[]
        for machine in ('host','arm64'):
            with self.subTest(machine=machine,case=case),tempfile.TemporaryDirectory(dir=self.folder) as name:
                proc=Path(name)
                for pid in ([230,231] if second else [230]):
                    task=proc/str(pid);task.mkdir();(task/'comm').write_text(comm)
                    (task/'stat').write_text(stat if stat is not None else stat_text(pid))
                    (task/'wchan').write_text(wchan)
                if symlink:
                    (proc/'230/stat').unlink();(proc/'230/stat').symlink_to('/nonexistent-h0-fixture')
                cmd=(['qemu-aarch64'] if machine=='arm64' else [])+[str(self.folder/machine),str(proc),case,str(actor)]
                value=subprocess.run(cmd,capture_output=True,timeout=10,cwd=proc)
                self.assertEqual(value.returncode,0,value.stderr.decode())
                self.assertIn(b'H0_OK',value.stderr)
                proof=project(value.stdout)
                self.assertFalse(proof['rejected'],value.stdout)
                self.assertFalse(proof['conflicts'])
                self.assertFalse(proof['watchdog_conflicts'])
                for field in ('installed_debian_pid1','watchdog_pet_proved','watchdog_phase_proved',
                        'watchdog_cause_proved','watchdog_samples_atomic','absence_proves_nonexecution',
                        'rcs_completed','ssh_access_proved','clean_shutdown_proved','replay_authorized'):
                    self.assertIs(proof[field],False)
                self.assertIsNone(proof['highest_authenticated_stage'])
                outputs.append(proof)
        self.assertEqual(len(outputs),2)
        self.assertEqual(outputs[0],outputs[1])
        return outputs[0]

    def test_five_bounded_pairs_from_both_existing_owners(self):
        for actor in (6,8):
            proof=self.run_case(actor=actor)
            self.assertEqual(len(proof['records']),10)
            for row in proof['records']:
                self.assertNotIn('child_pid',row)
                self.assertEqual(row['watchdog']['task'],dict(pid=230,starttime_ticks=123))
            task=proof['records'][0]['watchdog']
            self.assertEqual((task['cpu_time_ticks'],task['last_cpu'],task['scheduling_policy'],task['rt_priority']),(12,7,1,99))

    def test_missing_ambiguous_wrong_filesystem_and_symlink_are_errors(self):
        for kwargs,error in ((dict(comm='unrelated\n'),2),(dict(second=True),17),
                            (dict(case='wrong-fs'),71),(dict(symlink=True),40)):
            with self.subTest(kwargs=kwargs):
                proof=self.run_case(**kwargs)
                self.assertEqual(len(proof['records']),1)
                self.assertEqual(proof['records'][0]['watchdog']['read_error'],error)

    def test_actual_read_errors_stop_without_retry_and_preserve_errno(self):
        for case,error in (('eintr',4),('eio',5),('slow-read',110),('very-slow-read',110),
                           ('short-read',75),('close-error',5),('too-many-entries',75)):
            with self.subTest(case=case):
                proof=self.run_case(case)
                self.assertEqual(len(proof['records']),1)
                self.assertEqual(proof['records'][0]['watchdog']['read_error'],error)

    def test_wchan_failure_keeps_task_fact_and_disables_further_reads(self):
        proof=self.run_case('wchan-error')
        self.assertEqual(len(proof['records']),2)
        self.assertEqual(proof['records'][0]['watchdog']['read_error'],0)
        self.assertEqual(proof['records'][1]['watchdog']['read_error'],13)

    def test_cached_pid_reuse_and_reuse_during_read_never_relabel_task(self):
        for case,count in (('reuse-after',3),('reuse-during',1)):
            proof=self.run_case(case)
            self.assertEqual(len(proof['records']),count)
            self.assertEqual(proof['records'][-1]['watchdog']['read_error'],116)

    def test_malformed_and_oversized_proc_stat_are_not_facts(self):
        for text in (stat_text(**{'9':0}),stat_text(**{'20':2}),stat_text(**{'39':32}),
                stat_text(**{'14':-1}),stat_text(**{'14':2**64}),stat_text(**{'40':100}),
                stat_text().replace('(gh-watchdog)','(impostor)'),stat_text().replace(' S ',' Q '),
                stat_text().rstrip()+' 0\n',stat_text()+'x'*2048):
            proof=self.run_case(stat=text)
            self.assertEqual(len(proof['records']),1)
            self.assertGreater(proof['records'][0]['watchdog']['read_error'],0)

    def test_wait_symbol_classes_do_not_emit_raw_symbols_or_addresses(self):
        for text,label in (('0','zero_running_unavailable_or_hidden'),('csd_lock_wait','csd_lock_wait'),
                           ('ffffabcd12340000','other'),('new_private_symbol','other')):
            proof=self.run_case(wchan=text)
            self.assertEqual(proof['records'][1]['watchdog']['wait_symbol_class'],label)
            if label=='other':self.assertNotIn(text,str(proof))

    def test_late_call_and_observer_budgets_do_not_restart(self):
        proof=self.run_case('late')
        self.assertEqual(len(proof['records']),8)
        self.assertEqual(proof['records'][0]['watchdog']['slot'],1)
        proof=self.run_case('late-owner',actor=8)
        self.assertEqual(len(proof['records']),6)
        self.assertEqual(proof['records'][0]['watchdog']['slot'],2)
        for case in ('disabled','budget-exhausted','spend-exhausted','log-loss','after-window'):
            self.assertFalse(self.run_case(case)['records'])
        self.assertFalse(self.run_case(actor=7)['records'])

    def test_logging_delay_preserves_acquisition_time(self):
        proof=self.run_case('log-delay')
        row=proof['records'][1]
        self.assertEqual(row['watchdog']['acquired_boottime_ms'],6000)
        self.assertEqual(row['boottime_ms'],6200)


class WatchdogDecoder(unittest.TestCase):
    def test_explicit_eight_actor_selection_is_required(self):
        value=project(record(),expected={a:SOURCE for a in trace.RCS_ACTORS})
        self.assertEqual(value['rejected'],{'unselected_watchdog':1})
        selected={name:dict(sha256=SOURCE) for name in ('writer','entry','witness','hook')}
        self.assertEqual(set(trace.sources(selected)),set(trace.ACTORS))
        selected['transition_observer']=dict(schema='s22plus-autoboot-watchdog-v1')
        self.assertEqual(trace.sources(selected),EXPECTED)

    def test_payload_shape_and_timing_cannot_be_promoted(self):
        bad=(dict(properties=0),dict(sample=(6000<<3)|5),dict(ms=5999),dict(sample=8500<<3),
             dict(sample=(9250<<3)|1,ms=9250),dict(value=-1),dict(task=2),dict(error=5),
             dict(stage=80,value=7,properties=0),dict(kind=1),dict(actor=7))
        for changes in bad:
            with self.subTest(changes=changes):
                self.assertFalse(project(record(**changes))['records'])

    def test_duplicate_slot_and_changed_task_are_diagnostic_conflicts(self):
        for second,conflict in ((record(seq=2),'repeated_watchdog_slot'),
                (record(seq=2,sample=(9000<<3)|1,ms=9000,start=124),'watchdog_task_identity'),
                (record(seq=2,sample=(9000<<3)|1,ms=9000,value=1),'watchdog_cpu_time_reversal')):
            proof=project(record()+second)
            self.assertIn(conflict,proof['watchdog_conflicts'])
            self.assertFalse(proof['watchdog_observations_consistent'])

    def test_optional_partial_pairs_and_errors_do_not_erase_functional_facts(self):
        installed=record(actor=4,stage=58,kind=2,convention=2,value=0,task=0,start=0,properties=0,sample=0,pid=11)
        complete=record(stage=70,seq=3,value=0,task=0,start=0,properties=0,sample=0,ms=12000)
        for diagnostic in (record(),record(stage=80,value=0,properties=0),
                record(error=5,value=0,task=0,start=0,properties=0),record()+record(seq=2)):
            proof=project(installed+diagnostic+complete)
            self.assertTrue(proof['installed_debian_pid1'])
            self.assertTrue(proof['rcs_completed'])
            self.assertEqual(proof['highest_authenticated_stage'],'RCS_COMPLETE')
            self.assertFalse(proof['watchdog_pet_proved'])

    def test_source_boot_authentication_and_sequence_contradictions_still_fail_closed(self):
        line=record();match=trace.LINE.fullmatch(line.rstrip());body=bytearray.fromhex(match[4].decode())
        body[88:120]=bytes(32)
        self.assertEqual(project(authenticated(body))['rejected'],{'producer':1})
        self.assertFalse(project(line.replace(b'mac=',b'mac=0',1))['records'])
        proof=project(line+line)
        self.assertIn('duplicate_sequence',proof['conflicts'])
        self.assertFalse(proof['watchdog_observations_consistent'])
        body=bytearray.fromhex(match[4].decode());struct.pack_into('<I',body,12,2)
        proof=project(line+authenticated(body,boot=b'11111111-2222-3333-4444-555555555555'))
        self.assertIn('kernel_boot',proof['conflicts'])


if __name__=='__main__':unittest.main()
