"""Actual host/ARM64 text decoding and independently authenticated phase facts."""
from pathlib import Path
import subprocess
import tempfile
import unittest

import test_s22plus_autoboot_watchdog_v1 as base
import s22plus_debian_autoboot_phase_v1 as spec

ROOT=base.ROOT
STATS=('entries: 1\noverrun: 0\ncommit overrun: 0\nbytes: 128\n'
       'oldest event ts: 10.000000\nnow ts: 12.500000\ndropped events: 0\nread events: 1\n')


class PhaseParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='s22-phase-parser-')
        cls.folder=Path(cls.temporary.name)
        (cls.folder/'s22plus_autoboot_phase_seal_v1.h').write_bytes(spec.probe_header())
        for machine,compiler,extra in (('host','gcc',[]),('arm64','aarch64-linux-gnu-gcc',['-static'])):
            command=[compiler,'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',*extra,
                '-I',str(cls.folder),'-I',str(ROOT/'workspace/public/src/native-init'),
                str(ROOT/'tests/s22plus_autoboot_phase_parse_harness.c'),'-o',str(cls.folder/machine)]
            result=subprocess.run(command,capture_output=True,timeout=60)
            if result.returncode:raise RuntimeError(result.stderr.decode())

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def parse(self,mode,text,*args):
        results=[]
        for machine in ('host','arm64'):
            command=(['qemu-aarch64'] if machine=='arm64' else [])+[str(self.folder/machine),mode,*args]
            done=subprocess.run(command,input=text.encode(),capture_output=True,timeout=5)
            self.assertEqual(done.returncode,0,done.stderr.decode())
            results.append(tuple(map(int,done.stdout.split())))
        self.assertEqual(*results)
        return results[0]

    def test_signed_register_idle_pid_and_exact_callsite(self):
        text='          <idle>-0       [007] d.h1  10.000001: ping_return: (qcom_wdt_kthread+0x26c/0x320 [qcom_wdt_core]) cpu=7 rc=-22\n'
        self.assertEqual(self.parse('trace',text),(0,10000001,4,0,7,7,-22))
        for old,new in (('[007]','[008]'),('cpu=7','cpu=-1'),('rc=-22','rc=2147483648'),
            ('+0x26c/','+0x268/'),('[qcom_wdt_core]','[foreign]'),('10.000001','10.00000'),
            ('qcom_wdt_kthread+0x26c/0x320 [qcom_wdt_core]','0xffff12345678'),
            (' rc=-22',''),('\n',''),('cpu=7','cpu=7 extra=0')):
            with self.subTest(new=new):self.assertNotEqual(self.parse('trace',text.replace(old,new))[0],0)

    def test_all_probe_shapes_and_missing_fields(self):
        for identifier,name,symbol,offset,fields in spec.PROBES:
            body=f'            worker-52 [001] ....  12.000000: {name}: ({symbol}+0x{offset:x}/0x320 [qcom_wdt_core])'
            if 'cpu=' in fields:body+=' cpu=1'
            if 'rc=' in fields:body+=' rc=0'
            self.assertEqual(self.parse('trace',body+'\n')[:3],(0,12000000,identifier))
            self.assertNotEqual(self.parse('trace',body+' unused=0\n')[0],0)

    def profile(self,changes=None):
        changes=changes or {}
        return ''.join(f'{name} {changes.get(i,(3,0))[0]} {changes.get(i,(3,0))[1]}\n'
                       for i,name,*_ in spec.PROBES)

    def test_profile_excess_is_valid_and_per_event_deficit_is_not(self):
        self.assertEqual(self.parse('profile',self.profile(),'2'),(0,4095,36,0))
        self.assertNotEqual(self.parse('profile',self.profile({1:(1,0),2:(100,0)}),'2')[0],0)
        self.assertEqual(self.parse('profile',self.profile({2:(3,1)}),'2'),(0,4095,36,1))
        normal=self.profile()
        for text in (normal.rstrip(),normal+normal.splitlines()[0]+'\n',
            '\n'.join(normal.splitlines()[:-1])+'\n',normal.replace('timer_enter','s22phase/timer_enter'),
            normal.replace('3 0','-1 0',1),normal.replace('3 0','4294967296 0',1)):
            self.assertNotEqual(self.parse('profile',text,'2')[0],0)

    def test_every_stats_row_is_required_once(self):
        self.assertEqual(self.parse('stats',STATS),(0,0,0,0))
        self.assertEqual(self.parse('stats',STATS.replace('overrun: 0','overrun: 2',1)),(0,2,0,0))
        for line in STATS.splitlines(keepends=True):
            self.assertNotEqual(self.parse('stats',STATS.replace(line,''))[0],0)
            self.assertNotEqual(self.parse('stats',STATS+line)[0],0)
        for text in (STATS.rstrip(),STATS.replace('bytes: 128','bytes: -1'),STATS+'unknown: 0\n'):
            self.assertNotEqual(self.parse('stats',text)[0],0)

    def test_datagrams_are_one_complete_fixed_packet(self):
        for text in ('1 D 0 0\n','2 B 1 0\n','3 E 1 23\n','34 X 0 0\n'):
            self.assertEqual(self.parse('packet',text)[0],0)
        for text in ('','1 ','0 D 0 0\n','35 X 0 0\n','2 B 0 0\n','3 E 1 -1\n',
                     '1 D 0 0','1 D 0 0\n2 B 1 0\n'):
            self.assertNotEqual(self.parse('packet',text)[0],0)


class PhaseFacts(unittest.TestCase):
    def line(self,**changes):
        args=dict(stage=86,value=10000001,ms=10001,task=0,start=4|(7<<8),
                  properties=7,sample=2**32-22)
        args.update(changes)
        return base.record(**args)

    def project(self,*lines,phase=True,phase_window_ms=15000):
        return base.project(b''.join(lines),phase=phase,phase_window_ms=phase_window_ms)

    def test_virtual_window_requires_explicit_trusted_selection(self):
        late=self.line(value=20000001,ms=20001)
        self.assertEqual(self.project(late)['rejected'],{'semantics':1})
        virtual=self.project(late,phase_window_ms=spec.VM_TIMING['absolute_window_ms'])
        self.assertFalse(virtual['rejected'])
        self.assertEqual(virtual['records'][0]['phase']['kernel_boottime_us'],20000001)
        self.assertEqual(self.project(late)['rejected'],{'semantics':1})
        with self.assertRaises(ValueError):
            self.project(late,phase_window_ms=300000)

    def test_selection_and_positive_scope(self):
        self.assertEqual(self.project(self.line(),phase=False)['rejected'],{'unselected_phase':1})
        result=self.project(self.line())
        self.assertFalse(result['rejected'])
        self.assertTrue(result['phase']['consistent'])
        observed=result['records'][0]['phase']
        self.assertEqual((observed['pid'],observed['target_cpu'],observed['returned_register']),(0,7,-22))
        self.assertIsNone(result['highest_authenticated_stage'])
        self.assertFalse(result['phase']['watchdog_pet_proved'])
        self.assertFalse(result['phase']['cleanup_confirmed'])
        self.assertFalse(result['phase']['window_complete'])
        self.assertEqual(self.project(base.record())['rejected'],{'unselected_proc_watchdog':1})

    def test_cap_cutoff_and_scalar_shapes(self):
        for changes in (dict(value=14999999,ms=15000),dict(start=4|(8<<8)),
            dict(properties=8),dict(start=5,sample=1,properties=2**32-1),
            dict(stage=87,value=0,ms=15000,task=1,start=0,properties=ord('D'),sample=0)):
            self.assertFalse(self.project(self.line(**changes))['records'])

    def test_metadata_failure_keeps_positive_observation(self):
        positive=self.line()
        profile=self.line(stage=88,seq=2,value=100,error=71,task=2047,start=26,properties=1,sample=0)
        ring=self.line(stage=89,seq=3,value=2,task=255,start=0,properties=0,sample=1)
        result=self.project(positive,profile,ring)
        self.assertEqual(len(result['records']),3)
        self.assertFalse(result['phase']['metadata_complete'])
        self.assertFalse(result['phase']['no_detected_loss'])
        self.assertTrue(result['phase']['consistent'])

    def test_checked_summaries_and_cleanup_are_separate(self):
        profile=self.line(stage=88,seq=2,value=100,task=4095,start=26,properties=1,sample=0)
        ring=self.line(stage=89,seq=3,value=0,task=255,start=0,properties=0,sample=0)
        result=self.project(self.line(),profile,ring)
        self.assertTrue(result['phase']['metadata_complete'])
        self.assertTrue(result['phase']['no_detected_loss'])
        self.assertFalse(result['phase']['cleanup_confirmed'])
        self.assertFalse(result['phase']['window_complete'])
        duplicate=self.line(stage=88,seq=4,value=100,task=4095,start=26,properties=1,sample=0)
        self.assertIn('phase_duplicate_metadata',self.project(self.line(),profile,ring,duplicate)['phase']['conflicts'])

    def test_optional_phase_records_do_not_replace_functional_completion(self):
        installed=base.record(actor=4,stage=58,kind=2,convention=2,value=0,task=0,start=0,properties=0,sample=0,pid=11)
        complete=base.record(stage=70,seq=4,value=0,task=0,start=0,properties=0,sample=0,ms=12000)
        result=self.project(installed,self.line(),complete)
        self.assertTrue(result['installed_debian_pid1'])
        self.assertTrue(result['rcs_completed'])
        self.assertEqual(result['highest_authenticated_stage'],'RCS_COMPLETE')

    def test_kernel_and_script_retention_gaps_preserve_surviving_facts(self):
        profile=self.line(stage=88,seq=35,value=100,task=4095,start=26,properties=26,sample=0)
        ring=self.line(stage=89,seq=36,value=0,task=255,start=0,properties=0,sample=34<<8)
        begin=self.line(stage=87,seq=2,value=0,task=1,start=0,properties=ord('D'),sample=0)
        end=self.line(stage=87,seq=34,value=0,task=34,start=0,properties=ord('X'),sample=0)
        for packets in ((),(begin,end)):
            result=self.project(self.line(),*packets,profile,ring)
            self.assertTrue(result['phase']['retained_kernel_count_gap'])
            self.assertTrue(result['phase']['retained_script_count_gap'])
            self.assertFalse(result['phase']['no_detected_loss'])
            self.assertTrue(result['phase']['consistent'])
            self.assertEqual(result['records'][0]['phase']['event_id'],4)


if __name__=='__main__':unittest.main()
